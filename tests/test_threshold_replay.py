"""Replay integrity and metrics, without local measurement artifacts or model calls."""

import asyncio
import copy
import unittest
from unittest.mock import patch

from evals.step6.threshold_replay import (
    BASELINE,
    CANDIDATE,
    RecordedBackend,
    configuration_v4,
    counts,
    decision_view,
    report,
    validate_rows,
)
from humanwill_policies.serialization import digest


class ThresholdReplayTests(unittest.TestCase):
    def test_only_thresholds_and_version_change(self):
        original = {
            "format": "humanwill.config/3",
            "metadata": {"enabled": True},
            "policies": {
                "RULE": {
                    "enabled": True,
                    "mode": "monitor",
                    "scope": "unchanged",
                    "monitor_min_confidence": 0.8,
                }
            },
        }
        baseline = configuration_v4(original, BASELINE)
        candidate = configuration_v4(original, CANDIDATE)
        baseline["outcome_thresholds"]["not_applicable"] = 0.7
        self.assertEqual(candidate, baseline)
        self.assertEqual(original["policies"]["RULE"]["monitor_min_confidence"], 0.8)
        self.assertEqual(candidate["policies"]["RULE"]["scope"], "unchanged")

    def test_recorded_answers_are_consumed_exactly_and_never_generated(self):
        answer = {
            "choice": "not_applicable",
            "confidence": 0.75,
            "probabilities": {"applicable": 0, "not_applicable": 1, "insufficient_evidence": 0},
        }
        backend = RecordedBackend({"policies": [{"policy_id": "RULE", "evidence": answer}]})
        with self.assertRaises(ValueError):
            backend.validate_consumed()
        with patch(
            "humanwill_policies.providers.JevBackend.evaluate",
            side_effect=AssertionError("No provider calls permitted"),
        ):
            response = asyncio.run(
                backend.evaluate({"questions": {"RULE": {}}}, timeout=1, max_bytes=10000)
            )
        self.assertEqual(response["answers"]["RULE"], {"type": "choice", **answer})
        backend.validate_consumed()
        asyncio.run(backend.evaluate({"questions": {"RULE": {}}}, timeout=1, max_bytes=10000))
        with self.assertRaises(ValueError):
            backend.validate_consumed()

    def test_baseline_comparison_does_not_hide_masked_policy_errors(self):
        before = {"decision": "block", "policies": [{"status": "error"}], "duration_ms": 100}
        after = {"decision": "block", "policies": [{"status": "not_applicable"}], "duration_ms": 1}
        self.assertNotEqual(decision_view(before), decision_view(after))
        after["policies"] = before["policies"]
        self.assertEqual(decision_view(before), decision_view(after))

    def test_missing_duplicate_reordered_or_relabelled_rows_are_rejected(self):
        cases = [
            {
                "id": key,
                "request": {"text": key},
                "expected_by_policy": {"R": "allow"},
                "scope_by_policy": {"R": "not_applicable"},
                "expected_composed": "allow",
            }
            for key in ("one", "two")
        ]
        contexts = {c["id"]: {"context": {"scope": c["id"]}} for c in cases}
        rows = [
            {
                **c,
                "result": {"request_sha256": digest(c["request"])},
                "context_sha256": digest(contexts[c["id"]]["context"]),
            }
            for c in cases
        ]
        validate_rows(cases, rows, contexts)
        variants = [rows[:1], rows[::-1], rows + rows[:1]]
        for key, value in [("expected_composed", "block"), ("context_sha256", "wrong")]:
            changed = copy.deepcopy(rows)
            changed[0][key] = value
            variants.append(changed)
        for changed in variants:
            with self.assertRaises(ValueError):
                validate_rows(cases, changed, contexts)
        with self.assertRaises(ValueError):
            report(cases, [], {})

    def test_false_blocks_misses_and_unknown_allows_are_separate(self):
        result = counts(
            [
                ("allow", "evaluation_error"),
                ("allow", "block"),
                ("block", "evaluation_error"),
                ("block", "allow"),
                ("evaluation_error", "allow"),
                ("evaluation_error", "evaluation_error"),
            ]
        )
        self.assertEqual(result["false_blocks_if_fail_closed"], 2)
        self.assertEqual(result["explicit_false_violations"], 1)
        self.assertEqual(result["missed_violations_if_fail_closed"], 1)
        self.assertEqual(result["specified_errors"], 2)
        self.assertEqual(result["unknown_incorrectly_allowed"], 1)
        self.assertEqual(result["unknown_correctly_indeterminate"], 1)
