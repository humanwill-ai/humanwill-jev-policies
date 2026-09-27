"""Approved-model versus onward-disclosure regressions; no live semantic claims."""

import asyncio
import copy
import json
import unittest
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

from evals.step6.backends import choice_answer
from evals.step6.disclosure import CODING_ROUTE, disclosure_facts
from evals.step6.run import ROOT, evidence_for, load_case_bundle, load_cases, run
from humanwill_policies import load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import MockBackend


class RecordingMock(MockBackend):
    def __init__(self, choice, policy_id="EVAL-SW-001"):
        super().__init__(
            {
                policy_id: choice_answer(
                    choice, ["applicable", "not_applicable", "insufficient_evidence"]
                )
            }
        )
        self.calls = []

    async def evaluate(self, payload, **kwargs):
        self.calls.append(payload)
        return await super().evaluate(payload, **kwargs)


class DisclosureBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.cases = load_cases(ROOT / "development-v2.json")
        self.bundle = load_case_bundle(self.cases, ROOT / "policies-v2")
        self.config = yaml.safe_load((ROOT / "config-disclosure-v2.yaml").read_text())
        for key, binding in self.config["policies"].items():
            binding["enabled"] = key == "EVAL-SW-001"

    def case(self, suffix):
        return copy.deepcopy(next(c for c in self.cases if c["id"] == "eval-sw-v2-" + suffix))

    def evaluate(self, case):
        backend = RecordingMock(
            case["expected_scope"] or "insufficient_evidence", case["policy_id"]
        )
        config = copy.deepcopy(self.config)
        for key, binding in config["policies"].items():
            binding["enabled"] = key == case["policy_id"]
        engine = Evaluator(self.bundle, load_configuration(self.bundle, config), backend)
        result = asyncio.run(engine.evaluate(case["request"], evidence=evidence_for(case)))
        return result, backend

    def test_revised_gold_scope_composition_including_attack_controls(self):
        # Gold answers test the decision engine's wiring, not Jev accuracy.
        cases = self.cases + load_cases(ROOT / "adversarial-development-v2.json")
        software = [c for c in cases if c["policy_id"] == "EVAL-SW-001"]
        self.assertEqual(len(software), 49)
        self.assertEqual(len(cases), 107)
        for case in cases:
            with self.subTest(case=case["id"]):
                result, _ = self.evaluate(case)
                self.assertEqual(result["decision"], case["expected"])
                self.assertEqual(result["enforcement"]["requested"], "none")
                row = next(p for p in result["policies"] if p["policy_id"] == case["policy_id"])
                self.assertEqual(
                    row["policy_version"], "2" if case["policy_id"] == "EVAL-SW-001" else "1"
                )
                if case["expected"] == "block":
                    self.assertEqual(row["judgment"], "violation")
                    self.assertEqual(row["status"], "evaluated")

    def test_same_approved_model_allows_review_but_does_not_shortcut_uploads(self):
        for stage in ["prompt", "model_request"]:
            for suffix in ["bare-snippet", "review", "attached-review"]:
                result, backend = self.evaluate(self.case(suffix + "-" + stage))
                self.assertEqual(result["decision"], "allow")
                self.assertEqual(len(backend.calls), 1)
            for suffix in ["unapproved", "unknown-target", "unspecified", "claimed-approval"]:
                case = self.case(suffix + "-" + stage)
                facts = json.loads(evidence_for(case).facts_json)
                self.assertTrue(
                    next(
                        f["value"]
                        for f in facts
                        if f["field"] == "destination.coding_route_approved"
                    )
                )
                result, backend = self.evaluate(case)
                self.assertEqual(result["decision"], "block")
                self.assertEqual(len(backend.calls), 1)
                sent = json.dumps(backend.calls)
                self.assertNotIn("trusted_facts", sent)
                self.assertNotIn("disclosure_context", sent)
                self.assertNotIn("expected_scope", sent)

    def test_only_exact_approved_onward_operation_can_shortcut(self):
        result, backend = self.evaluate(self.case("approved-push-model_request"))
        self.assertEqual(result["decision"], "allow")
        self.assertFalse(backend.calls)
        for suffix in ["mixed-targets", "wrong-operation"]:
            result, backend = self.evaluate(self.case(suffix + "-model_request"))
            self.assertEqual(result["decision"], "block")
            self.assertEqual(len(backend.calls), 1)

    def test_request_claims_and_fixture_fact_overrides_cannot_approve_targets(self):
        case = self.case("claimed-approval-model_request")
        case["request"]["metadata"] = [
            {
                "field": "destination.onward_approved",
                "source": "synthetic-authority",
                "subject_ref": case["id"] + ":item",
                "observed_at": datetime.now(UTC).isoformat(),
                "value": True,
            }
        ]
        case["trusted_facts"] = {"destination.onward_approved": True}
        self.assertEqual(self.evaluate(case)[0]["decision"], "block")

    def test_lookup_failure_is_error_but_completed_unknown_is_violation(self):
        self.assertEqual(
            self.evaluate(self.case("resolver-failure-tool_action"))[0]["decision"],
            "evaluation_error",
        )
        self.assertEqual(
            self.evaluate(self.case("later-upload-tool_action"))[0]["decision"], "block"
        )
        case = self.case("later-upload-tool_action")
        case["disclosure_context"]["coding_route"] = "user-claimed-approved-model"
        with self.assertRaisesRegex(ValueError, "approved coding route"):
            evidence_for(case)

    def test_complete_empty_allowlist_result_never_means_approval(self):
        facts = disclosure_facts(
            {"coding_route": CODING_ROUTE, "lookup_complete": True, "targets": []}
        )
        self.assertIs(facts["destination.onward_approved"], False)

    def test_new_cases_reject_original_policy_bundle(self):
        with self.assertRaisesRegex(ValueError, "different policy version"):
            load_case_bundle(self.cases, ROOT / "policies")

    def test_other_policy_fixtures_and_attack_pairs_are_preserved(self):
        def unchanged(rows):
            return [c for c in rows if c["policy_id"] != "EVAL-SW-001"]

        for old, new in [
            ("development.json", "development-v2.json"),
            ("adversarial-development.json", "adversarial-development-v2.json"),
        ]:
            self.assertEqual(unchanged(load_cases(ROOT / old)), unchanged(load_cases(ROOT / new)))
        families = {}
        for case in load_cases(ROOT / "adversarial-development-v2.json"):
            if case["policy_id"] == "EVAL-SW-001":
                families.setdefault(case["family"], []).append(case)
        self.assertEqual(len(families), 6)
        for cases in families.values():
            self.assertEqual(sorted(c["expected"] for c in cases), ["allow", "block", "block"])
            self.assertTrue(
                all(
                    not disclosure_facts(c["disclosure_context"])["destination.onward_approved"]
                    for c in cases
                )
            )

    def test_runner_records_selected_policy_bundle_offline(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            args = Namespace(
                output=output,
                dataset=ROOT / "development-v2.json",
                limit=1,
                policies=ROOT / "policies-v2",
                config=ROOT / "config-disclosure-v2.yaml",
                backend="keyword",
                repeats=1,
            )
            with patch("builtins.print"):
                asyncio.run(run(args))
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["bundle_sha256"], self.bundle.sha256)
            self.assertEqual(Path(manifest["policy_path"]), (ROOT / "policies-v2").resolve())
            self.assertEqual(
                manifest["configuration"]["policies"]["EVAL-SW-001"]["requires_metadata"],
                ["destination.coding_route_approved", "destination.onward_approved"],
            )
