"""Verify the active 100-case review includes source policy and preserves its history."""

import asyncio
import hashlib
import json
import unittest
from pathlib import Path

import yaml

from evals.step6.backends import choice_answer
from evals.step6.run import load_case_bundle, load_cases, select_configuration
from evals.step6.source_approval import load_catalog, source_evidence_for
from humanwill_policies import load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import MockBackend

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evals/step6"
DATASET = BASE / "release/holdout-sources-v2.json"


class RevisedHoldoutTests(unittest.TestCase):
    def test_all_original_events_preserved_but_source_checks_added(self):
        old = json.loads((BASE / "release/holdout-v1.json").read_text())["cases"]
        new = load_cases(DATASET, allowed_splits={"review_candidate"})
        self.assertEqual(len(new), 100)
        for before, after in zip(old, new, strict=True):
            self.assertEqual(before["request"], after["request"])
            self.assertEqual(before["expected"], after["expected_by_policy"][before["policy_id"]])
            self.assertIn("EVAL-SRC-001", after["expected_by_policy"])
            self.assertEqual(after["review_expected"], after["expected_composed"])
        changed = {
            c["id"]: c["review_expected"] for c in new if c["review_expected"] != c["expected"]
        }
        self.assertEqual(
            changed,
            {
                "holdout-v1-sw-download-dependency": "block",
                "holdout-v1-sw-git-fetch": "evaluation_error",
            },
        )
        manual = next(c for c in new if c["id"] == "holdout-v1-sw-download-manual")
        self.assertEqual(manual["expected_by_policy"]["EVAL-SRC-001"], "allow")
        self.assertEqual(manual["scope_by_policy"]["EVAL-SRC-001"], "not_applicable")

    def test_review_snapshot_is_exact_and_pending(self):
        snapshot = json.loads((BASE / "release/holdout-sources-v2-snapshot.json").read_text())
        self.assertEqual(snapshot["status"], "pending_owner_labels")
        for path, expected in snapshot["sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)

    def test_all_hundred_combined_results_with_scripted_semantics(self):
        cases = load_cases(DATASET, allowed_splits={"review_candidate"})
        bundle = load_case_bundle(cases, BASE / "policies-sources-v1")
        config = yaml.safe_load((BASE / "config-sources-v1.yaml").read_text())
        catalog = load_catalog()
        for case in cases:
            with self.subTest(case=case["id"]):
                answers = {
                    key: choice_answer(
                        value or "insufficient_evidence",
                        ["applicable", "not_applicable", "insufficient_evidence"],
                    )
                    for key, value in case["scope_by_policy"].items()
                }
                selected = select_configuration(config, case["policy_id"], ["EVAL-SRC-001"])
                evaluator = Evaluator(
                    bundle, load_configuration(bundle, selected), MockBackend(answers)
                )
                result = asyncio.run(
                    evaluator.evaluate(case["request"], evidence=source_evidence_for(case, catalog))
                )
                self.assertEqual(result["decision"], case["expected_composed"])
                for row in result["policies"]:
                    if row["policy_id"] not in case["expected_by_policy"]:
                        continue
                    observed = (
                        "block"
                        if row["judgment"] == "violation"
                        else "evaluation_error"
                        if row["status"] == "error"
                        else "allow"
                    )
                    self.assertEqual(observed, case["expected_by_policy"][row["policy_id"]])
