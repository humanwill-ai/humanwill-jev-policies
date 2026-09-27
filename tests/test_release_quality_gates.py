"""Prospective review boundaries and release-metric audit; no live model calls."""

import asyncio
import copy
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from evals.step6.backends import choice_answer
from evals.step6.gates import (
    CANDIDATE,
    CONFIG,
    POLICIES,
    SNAPSHOT,
    assess_rows,
    assess_runs,
    audit_candidate,
)
from evals.step6.run import evidence_for, load_case_bundle, load_cases, select_configuration
from humanwill_policies import load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import MockBackend


class ReleaseQualityGateTests(unittest.TestCase):
    def test_candidate_snapshot_validates_without_claiming_review(self):
        result = audit_candidate()
        self.assertEqual(result["cases"], 36)
        self.assertIn("pending", result["human_review"])
        self.assertIn("not_assessable", result["release_gate"])
        self.assertEqual(result["api_calls"], 0)

    def test_current_runner_rejects_prospective_candidates(self):
        with self.assertRaisesRegex(ValueError, "unreviewed holdout"):
            load_cases(CANDIDATE)

    def test_draft_gold_scope_composition_only_not_model_accuracy(self):
        cases = load_cases(CANDIDATE, allowed_splits={"review_candidate"})
        bundle = load_case_bundle(cases, POLICIES)
        config = yaml.safe_load(CONFIG.read_text())
        for case in cases:
            with self.subTest(case=case["id"]):
                backend = MockBackend(
                    {
                        case["policy_id"]: choice_answer(
                            case["expected_scope"] or "insufficient_evidence",
                            ["applicable", "not_applicable", "insufficient_evidence"],
                        )
                    }
                )
                evaluator = Evaluator(
                    bundle,
                    load_configuration(bundle, select_configuration(config, case["policy_id"])),
                    backend,
                )
                result = asyncio.run(
                    evaluator.evaluate(case["request"], evidence=evidence_for(case))
                )
                self.assertEqual(result["decision"], case["expected"])
                self.assertEqual(result["enforcement"]["requested"], "none")

    def test_changed_candidate_or_rubric_invalidates_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "candidate.json"
            candidate.write_text(CANDIDATE.read_text().replace("AST visitor", "syntax visitor"))
            with self.assertRaisesRegex(ValueError, "snapshot changed"):
                audit_candidate(candidate=candidate)
            config = Path(directory) / "config.yaml"
            config.write_text(CONFIG.read_text().replace("0.8", "0.7"))
            with self.assertRaisesRegex(ValueError, "snapshot changed"):
                audit_candidate(config_path=config)

    def test_editing_attestation_does_not_establish_human_review(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "snapshot.json"
            data = json.loads(SNAPSHOT.read_text())
            data["status"] = "human_reviewed"
            data["reviewers"] = ["claimed reviewer"]
            snapshot.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "unreviewed candidate"):
                audit_candidate(snapshot=snapshot)

    def rows(self):
        return [
            {
                "id": "event-" + str(index),
                "policy_id": "POLICY",
                "family": "family-" + str(index),
                "expected": label,
                "expected_scope": None,
                "observed_scope": None,
                "repeat": 0,
                "result": {"decision": label, "duration_ms": 10, "evaluation": {"batches": []}},
            }
            for index, label in enumerate(["allow"] * 100 + ["block"] * 100)
        ]

    def test_even_perfect_large_development_sample_cannot_pass_release(self):
        rows = self.rows()
        result = assess_rows(rows, {"case_count": 200, "split": "holdout", "labels": "reviewed"})
        self.assertEqual(result["release_gate"], "not_assessable")
        targets = result["by_policy"]["POLICY"]["observed_target_comparison"]
        self.assertEqual(targets["false_block_upper95"]["status"], "met_on_observed_sample")
        self.assertIn("not_established", result["prerequisites"]["reviewed_independent_holdout"])

    def test_repeats_cannot_inflate_primary_accuracy(self):
        rows = self.rows()[:4]
        repeated = [copy.deepcopy(r) | {"repeat": 1} for r in rows]
        result = assess_rows(rows + repeated, {"case_count": 4})
        self.assertEqual(result["repeats_excluded_from_accuracy_denominators"], 4)
        targets = result["by_policy"]["POLICY"]["observed_target_comparison"]
        self.assertEqual(targets["false_block_upper95"]["status"], "failed")
        self.assertEqual(targets["missed_violation_upper95"]["status"], "unknown")
        with self.assertRaisesRegex(ValueError, "Duplicate primary"):
            assess_rows(rows + rows, {"case_count": 8})

    def test_errors_are_false_blocks_and_missing_cost_stays_unknown(self):
        rows = self.rows()[:4]
        rows[0]["result"].update(
            decision="evaluation_error",
            evaluation={"batches": [{"cost_usd": None, "returned_model": None}]},
        )
        result = assess_rows(rows, {"case_count": 4})["by_policy"]["POLICY"]
        self.assertEqual(result["metrics"]["false_blocks_if_fail_closed"]["count"], 1)
        self.assertEqual(result["metrics"]["specified_case_errors"]["count"], 1)
        self.assertEqual(
            result["observed_target_comparison"]["api_usd_per_1000"]["status"], "unknown"
        )

    def test_run_pooling_requires_matching_protocol_and_unique_events(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ["one", "two"]]
            manifests = []
            for index, path in enumerate(paths):
                path.mkdir()
                manifest = {
                    "backend": "jev",
                    "config_sha256": "same-config",
                    "bundle_sha256": "same-bundle",
                    "source_sha256": {"run.py": "same-source"},
                    "case_count": 1,
                    "dataset_sha256": "dataset-" + str(index),
                }
                manifests.append(manifest)
                (path / "manifest.json").write_text(json.dumps(manifest))
                (path / "results.jsonl").write_text(json.dumps(self.rows()[index]) + "\n")
            report = assess_runs(paths)
            self.assertTrue(report["run"]["complete_primary_rows"])
            self.assertEqual(report["by_policy"]["POLICY"]["metrics"]["cases"], 2)
            manifests[1]["backend"] = "chat"
            (paths[1] / "manifest.json").write_text(json.dumps(manifests[1]))
            with self.assertRaisesRegex(ValueError, "Cannot pool runs"):
                assess_runs(paths)

    def test_incomplete_sample_is_reported(self):
        report = assess_rows(self.rows()[:4], {"case_count": 200})
        self.assertFalse(report["run"]["complete_primary_rows"])
        self.assertEqual(report["release_gate"], "not_assessable")
