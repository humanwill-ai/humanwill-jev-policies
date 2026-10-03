"""No provider calls: provenance, egress gates, capture and partial-context composition."""

import asyncio
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from evals.dogfood.evaluate import (
    assess,
    load_profile,
    review_packet,
    source_fingerprint,
    verify_receipt,
)
from evals.dogfood.pilot import ROOT, capture, fingerprint, messages, prepare, render_review, save
from evals.step6.backends import choice_answer
from humanwill_policies.providers import MockBackend


def native(role, text, timestamp, **extra):
    item = {
        "type": "message",
        "role": role,
        "content": [{"type": "input_text" if role == "user" else "output_text", "text": text}],
        **extra,
    }
    if role == "user":
        item["internal_chat_message_metadata_passthrough"] = {"content_item_kinds": ["user.text"]}
    return {"type": "response_item", "timestamp": timestamp, "payload": item}


def packet_fixture():
    request = {
        "format": "humanwill.request/1",
        "request_id": "pilot-test",
        "stage": "model_request",
        "content": [{"id": "p", "kind": "text", "role": "user", "text": "Review local code."}],
        "coverage": {"complete": False, "inspected": ["p"], "omitted": ["tools and older history"]},
    }
    case = {
        "id": "pilot-test",
        "request": request,
        "request_sha256": fingerprint(request),
        "review": {
            "status": "pending",
            "expected_decision": None,
            "reason": "",
            "facts": {
                "destination.onward_approved": None,
                "authorization.software_sources_approved": None,
            },
        },
    }
    return {"format": "humanwill.dogfood-packet/1", "count": 1, "cases": [case]}


class DogfoodTests(unittest.TestCase):
    def test_transcript_excludes_internal_data_and_later_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = tmp / "transcript.jsonl"
            rows = [
                {"type": "session_meta", "payload": {"cwd": str(ROOT)}},
                native("user", "First prompt", "2026-01-01T00:00:00Z"),
                native("assistant", "Prior answer", "2026-01-01T00:00:01Z", phase="final"),
                native(
                    "assistant", "Internal commentary", "2026-01-01T00:00:02Z", phase="commentary"
                ),
                {
                    "type": "response_item",
                    "payload": {"type": "function_call_output", "output": "SECRET_TOOL_OUTPUT"},
                },
                native("user", "Second prompt", "2026-01-01T00:00:03Z"),
                native("assistant", "FUTURE ANSWER", "2026-01-01T00:00:04Z", phase="final"),
            ]
            injected = native("user", "INJECTED CONTEXT", "2026-01-01T00:00:02Z")
            injected["payload"]["internal_chat_message_metadata_passthrough"][
                "content_item_kinds"
            ] = ["agents_md.instructions"]
            rows.insert(3, injected)
            path.write_text("\n".join(json.dumps(x) for x in rows) + "\n")
            packet = prepare(path, "2026-01-01T00:00:04Z", tmp / "packet", count=2)
            self.assertEqual(
                [p["text"] for p in packet["cases"][-1]["request"]["content"]],
                ["First prompt", "Prior answer", "Second prompt"],
            )
            self.assertFalse(packet["cases"][-1]["request"]["coverage"]["complete"])
            self.assertNotIn("SECRET", json.dumps(packet))
            self.assertNotIn("FUTURE", json.dumps(packet))
            with self.assertRaises(ValueError):
                messages(path, tmp / "other-project")
            with self.assertRaises(ValueError):
                prepare(path, "2027", tmp / "packet", count=2)

    def test_reviews_cannot_rewrite_requests_or_add_facts(self):
        original = packet_fixture()
        reviewed = copy.deepcopy(original)
        r = reviewed["cases"][0]["review"]
        r.update(status="approved", expected_decision="allow")
        self.assertEqual(len(review_packet(original, reviewed)), 1)
        reviewed["cases"][0]["request"]["content"][0]["text"] = "different"
        with self.assertRaises(ValueError):
            review_packet(original, reviewed)
        reviewed = copy.deepcopy(original)
        with self.assertRaises(ValueError):
            review_packet(original, reviewed)

    def test_real_data_requires_exact_egress_receipt(self):
        original = packet_fixture()
        reviewed = copy.deepcopy(original)
        reviewed["cases"][0]["review"].update(status="approved", expected_decision="allow")
        bundle, config = load_profile()
        scope = {"coding_route_approved": True}
        receipt = {
            "packet_sha256": fingerprint(original),
            "review_sha256": fingerprint(reviewed),
            "operator_scope_sha256": fingerprint(scope),
            "bundle_sha256": bundle.sha256,
            "configuration_sha256": config.sha256,
            "source_sha256": source_fingerprint(),
            "allow_external_evaluation": True,
            "owner_authorization": "Synthetic test only",
            "additional_cap_usd": 0.10,
        }
        self.assertEqual(len(verify_receipt(original, reviewed, receipt, scope, bundle, config)), 1)
        for field, value in [
            ("allow_external_evaluation", False),
            ("review_sha256", "wrong"),
            ("additional_cap_usd", 5),
        ]:
            changed = {**receipt, field: value}
            with self.assertRaises(ValueError):
                verify_receipt(original, reviewed, changed, scope, bundle, config)

    def test_provisional_labels_are_never_human_approval(self):
        original = packet_fixture()
        reviewed = copy.deepcopy(original)
        r = reviewed["cases"][0]["review"]
        r.update(status="provisional", expected_decision="allow", reason="Local code review")
        with self.assertRaises(ValueError):
            review_packet(original, reviewed)
        r.update(reviewer="assistant", human_approved=False)
        self.assertEqual(review_packet(original, reviewed)[0]["review"]["status"], "provisional")
        r["human_approved"] = True
        with self.assertRaises(ValueError):
            review_packet(original, reviewed)

    def test_scope_does_not_invent_permission_when_metadata_missing(self):
        bundle, config = load_profile()
        case = packet_fixture()["cases"][0]
        labels = ["applicable", "not_applicable", "insufficient_evidence"]
        for choice, expected in [("not_applicable", "allow"), ("applicable", "evaluation_error")]:
            backend = MockBackend(
                {pid: choice_answer(choice, labels) for pid in config.to_dict()["policies"]}
            )
            result = asyncio.run(assess(case, bundle, config, backend))
            self.assertEqual(result["decision"], expected)
            self.assertEqual(result["enforcement"]["actual"], "not_requested")
            self.assertFalse(result["coverage"]["complete"])

    def test_capture_boundaries_deduplication_and_hard_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = {"project": str(ROOT), "session_id": "session", "max_prompts": 2}
            event = {
                "hook_event_name": "UserPromptSubmit",
                "cwd": str(ROOT),
                "session_id": "session",
                "turn_id": "1",
                "prompt": "text",
            }
            out = Path(tmp) / "capture"
            self.assertEqual(
                capture({**event, "session_id": "other"}, settings, out), "ignored_session"
            )
            self.assertFalse(out.exists())
            self.assertEqual(capture({**event, "cwd": tmp}, settings, out), "ignored_project")
            self.assertEqual(capture(event, settings, out), "captured")
            self.assertEqual(capture(event, settings, out), "duplicate")
            self.assertEqual(capture({**event, "turn_id": "2"}, settings, out), "captured")
            self.assertEqual(capture({**event, "turn_id": "3"}, settings, out), "capture_limit")
            self.assertEqual(len(list(out.glob("dogfood-future-*.json"))), 2)
            for file in out.glob("*.json"):
                self.assertEqual(file.stat().st_mode & 0o777, 0o600)

    def test_capture_command_never_blocks_or_outputs_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            settings = tmp / "settings.json"
            save(settings, {"project": str(ROOT), "session_id": "session", "max_prompts": 100})
            command = [
                sys.executable,
                str(ROOT / "evals/dogfood/pilot.py"),
                "capture",
                "--settings",
                str(settings),
                "--output",
                str(tmp / "queue"),
            ]
            event = {
                "hook_event_name": "UserPromptSubmit",
                "cwd": str(ROOT),
                "session_id": "session",
                "turn_id": "1",
                "prompt": "local review",
            }
            for value in [json.dumps(event), "malformed"]:
                result = subprocess.run(command, input=value, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "")
            self.assertEqual(
                json.loads((tmp / "queue/last-hook-status.json").read_text())["status"],
                "capture_error",
            )

    def test_html_escapes_transcript_script_and_has_no_external_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = packet_fixture()
            p["transcript_prefix_sha256"] = "synthetic"
            p["cases"][0]["request"]["content"][0]["text"] = "</script><script>alert(1)</script>"
            path = Path(tmp) / "review.html"
            render_review(p, path)
            text = path.read_text()
            self.assertNotIn("</script><script>alert(1)</script>", text)
            self.assertIn("textContent", text)
            self.assertNotIn("<script src=", text)


if __name__ == "__main__":
    unittest.main()
