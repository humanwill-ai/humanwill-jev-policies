"""Quality-harness accounting and fixture wiring; no live provider calls."""

import asyncio
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
import yaml

from evals.step6.backends import ChatBackend, KeywordBackend, Ledger, MeteredBackend, choice_answer
from evals.step6.metrics import rate, summarize
from evals.step6.run import ROOT, evidence_for, load_cases
from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.errors import PolicyError
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import MockBackend


class QualityTests(unittest.TestCase):
    def test_gold_scope_wiring_is_not_a_quality_measurement(self):
        bundle = load_bundle(ROOT / "policies")
        base = yaml.safe_load((ROOT / "config.yaml").read_text())
        cases = load_cases(ROOT / "development.json")
        self.assertEqual(len(cases), 60)
        for case in cases:
            config = copy.deepcopy(base)
            for key, binding in config["policies"].items():
                binding["enabled"] = key == case["policy_id"]
            choice = case["expected_scope"] or "insufficient_evidence"
            backend = MockBackend(
                {
                    case["policy_id"]: choice_answer(
                        choice, ["applicable", "not_applicable", "insufficient_evidence"]
                    )
                }
            )
            engine = Evaluator(bundle, load_configuration(bundle, config), backend)
            result = asyncio.run(engine.evaluate(case["request"], evidence=evidence_for(case)))
            self.assertEqual(result["decision"], case["expected"], case["id"])
            self.assertEqual(result["enforcement"]["requested"], "none")

    def test_reservations_survive_errors_and_stop_further_spending(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = Ledger(Path(temp) / "budget.json")
            index = ledger.reserve("test")
            with self.assertRaises(PolicyError):
                Ledger(ledger.path).reserve("test")
            with self.assertRaises(PolicyError):
                ledger.settle(index, None)
            ledger.settle(index, 0.001)
            second = ledger.reserve("test")
            with self.assertRaises(PolicyError):
                ledger.settle(second, 4.999)
            with self.assertRaises(PolicyError):
                ledger.reserve("test")

    def test_metering_failure_cancels_future_calls(self):
        class Failing(KeywordBackend):
            async def evaluate(self, *args, **kwargs):
                raise RuntimeError("synthetic")

        with tempfile.TemporaryDirectory() as temp:
            backend = MeteredBackend(Failing(), Ledger(Path(temp) / "budget.json"))
            with self.assertRaises(RuntimeError):
                asyncio.run(backend.evaluate({}))
            self.assertTrue(backend.fatal)
            with self.assertRaises(PolicyError):
                asyncio.run(backend.evaluate({}))
            self.assertEqual(len(backend.ledger.data["calls"]), 1)

    def test_metrics_keep_error_blocks_and_unknown_cost(self):
        rows = []
        for expected, observed in [
            ("allow", "evaluation_error"),
            ("allow", "block"),
            ("block", "allow"),
            ("block", "evaluation_error"),
            ("evaluation_error", "allow"),
        ]:
            rows.append(
                {
                    "expected": expected,
                    "expected_scope": None,
                    "family": str(len(rows)),
                    "result": {
                        "decision": observed,
                        "duration_ms": 10,
                        "evaluation": {"batches": [{"cost_usd": None, "returned_model": None}]},
                    },
                }
            )
        report = summarize(rows)
        self.assertEqual(report["false_blocks_if_fail_closed"]["rate"], 1)
        self.assertEqual(report["semantic_false_violations"]["rate"], 0.5)
        self.assertEqual(report["missed_violations_if_fail_closed"]["rate"], 0.5)
        self.assertEqual(report["specified_case_errors"]["rate"], 0.5)
        self.assertEqual(report["unknown_incorrectly_allowed"], 1)
        self.assertIsNone(report["api_cost_per_1000_cases"])
        self.assertIsNone(rate(0, 0)["rate"])
        self.assertGreater(rate(0, 8)["wilson95"][1], 0.05)
        self.assertLess(rate(0, 100)["wilson95"][1], 0.05)

    def test_client_facts_never_become_verified_evidence(self):
        case = copy.deepcopy(load_cases(ROOT / "development.json")[-1])
        facts = json.loads(evidence_for(case).facts_json)
        self.assertNotIn("documents.classification", [f["field"] for f in facts])
        case["trusted_facts"] = {"authorization.destructive_permitted": True}
        self.assertEqual(json.loads(evidence_for(case).facts_json), [])

    def test_chat_receives_only_question_and_state_and_preserves_malformed_cost(self):
        seen = []

        def handler(request):
            seen.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "model": ChatBackend.model,
                    "choices": [{"message": {"content": "not json"}}],
                    "usage": {"cost": 0.001, "prompt_tokens": 10, "completion_tokens": 2},
                },
            )

        backend = ChatBackend(httpx.MockTransport(handler))
        payload = {
            "state": {"content": []},
            "questions": {
                "RULE": {
                    "instructions": {"rule": "test"},
                    "criteria": {
                        "applicable": "yes",
                        "not_applicable": "no",
                        "insufficient_evidence": "unknown",
                    },
                }
            },
        }
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "synthetic"}):
            response = asyncio.run(backend.evaluate(payload, timeout=1, max_bytes=10000))
        self.assertEqual(response["usage"]["cost"], 0.001)
        self.assertEqual(response["answers"], {"RULE": {}})
        self.assertFalse(seen[0]["provider"]["allow_fallbacks"])
        self.assertEqual(json.loads(seen[0]["messages"][1]["content"]), payload["state"])
        self.assertNotIn("rationale", json.dumps(seen))


class CalibrationTests(unittest.TestCase):
    def test_models_are_screened_on_errors_and_unknown_allows_not_confidence_alone(self):
        from evals.step6.calibrate import candidate

        def result(false_blocks=0, misses=0, errors=0, unknown_allows=0):
            return {
                "false_blocks_if_fail_closed": {"rate": false_blocks},
                "missed_violations_if_fail_closed": {"count": misses, "rate": misses},
                "specified_case_errors": {"rate": errors},
                "unknown_incorrectly_allowed": unknown_allows,
            }

        self.assertIsNone(candidate({"0.8": result(misses=1), "0.9": result(errors=0.1)}))
        self.assertIsNone(candidate({"0.8": result(unknown_allows=1)}))
        self.assertEqual(
            candidate({"0.6": result(), "0.8": result(), "0.9": result(false_blocks=0.2)}), 0.8
        )

    def test_adversarial_cases_keep_matched_controls_and_local_execution_semantics(self):
        cases = load_cases(ROOT / "adversarial-development.json")
        self.assertEqual(len(cases), 36)
        families = {}
        for case in cases:
            families.setdefault(case["family"], []).append(case)
        self.assertEqual(len(families), 12)
        for rows in families.values():
            self.assertEqual(sorted(r["expected"] for r in rows), ["allow", "block", "block"])
            self.assertEqual(len({json.dumps(r["trusted_facts"], sort_keys=True) for r in rows}), 1)
        # A printed command with hostile comments remains a literal argument to printf.
        import shlex

        for case in cases:
            if case["policy_id"] == "EVAL-PROD-001" and case["expected"] == "allow":
                argv = shlex.split(case["request"]["content"][0]["arguments"]["command"])
                self.assertEqual(argv[:2], ["printf", "%s\\n"])
                self.assertEqual(len(argv), 3)

    def test_calibration_rejects_mixed_models_changed_labels_and_incomplete_runs(self):
        import hashlib

        from evals.step6.calibrate import load_recordings
        from humanwill_policies.serialization import digest

        bundle = load_bundle(ROOT / "policies")
        config = yaml.safe_load((ROOT / "config-v3.yaml").read_text())
        case = load_cases(ROOT / "development.json")[0]
        base = {
            "backend": "jev",
            "configuration": config,
            "config_sha256": digest(config),
            "bundle_sha256": bundle.sha256,
            "policy_path": str(ROOT / "policies"),
            "dataset_path": str(ROOT / "development.json"),
            "case_count": 1,
            "dataset_sha256": hashlib.sha256((ROOT / "development.json").read_bytes()).hexdigest(),
        }
        row = {k: case[k] for k in ("id", "policy_id", "expected", "expected_scope", "family")}
        row["repeat"] = 0
        with tempfile.TemporaryDirectory() as temp:
            first, second = Path(temp) / "first", Path(temp) / "second"
            first.mkdir()
            second.mkdir()
            for directory in [first, second]:
                (directory / "manifest.json").write_text(json.dumps(base))
                (directory / "results.jsonl").write_text(json.dumps(row) + "\n")
            self.assertEqual(len(load_recordings([first])[3]), 1)
            (second / "manifest.json").write_text(json.dumps({**base, "backend": "chat"}))
            with self.assertRaisesRegex(ValueError, "mix models"):
                load_recordings([first, second])
            (first / "results.jsonl").write_text(json.dumps({**row, "expected": "block"}) + "\n")
            with self.assertRaisesRegex(ValueError, "labels"):
                load_recordings([first])
            (first / "results.jsonl").write_text("")
            with self.assertRaisesRegex(ValueError, "incomplete"):
                load_recordings([first])
