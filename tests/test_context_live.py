"""Keep model choices, adapter rejections, masked policy errors and regressions distinct."""

import copy
import unittest

from evals.step6.context_live import compare, model_scope_metrics


def row():
    return {
        "id": "case-one",
        "expected_composed": "block",
        "expected_by_policy": {"first": "block", "second": "evaluation_error"},
        "scope_by_policy": {"first": "applicable", "second": "insufficient_evidence"},
        "result": {
            "decision": "block",
            "policies": [
                {
                    "policy_id": "first",
                    "status": "evaluated",
                    "judgment": "violation",
                    "reasons": [],
                    "evidence": {"choice": "applicable", "confidence": 0.9},
                },
                {
                    "policy_id": "second",
                    "status": "not_applicable",
                    "judgment": "not_evaluated",
                    "reasons": [],
                    "evidence": {"choice": "not_applicable", "confidence": 0.9},
                },
            ],
        },
    }


class ContextLiveTests(unittest.TestCase):
    def test_scope_is_not_confused_with_adapter_rejection(self):
        current = row()
        p = current["result"]["policies"][0]
        p.update(status="error", judgment="insufficient_evidence", reasons=["low_confidence"])
        p["evidence"]["confidence"] = 0.6
        metrics = model_scope_metrics([current])
        self.assertEqual(metrics["answers"], 2)
        self.assertEqual(metrics["correct_choices"], 1)
        self.assertEqual(metrics["wrong_choices"], 1)
        self.assertEqual(metrics["correct_choices_rejected_low_confidence"], 1)
        self.assertEqual(metrics["wrong_choices_rejected_low_confidence"], 0)
        self.assertEqual(metrics["mismatches"][0]["adapter_outcome"], "allow")

    def test_comparison_exposes_masked_changes_and_rejects_relabeling(self):
        before = row()
        after = copy.deepcopy(before)
        p = after["result"]["policies"][1]
        p.update(status="error", judgment="insufficient_evidence", reasons=["model_indeterminate"])
        p["evidence"]["choice"] = "insufficient_evidence"
        result = compare([before], [after])
        self.assertTrue(result["complete"])
        self.assertEqual(result["fixed_events"], 0)
        self.assertEqual(result["fixed_policy_outcomes"], 1)
        self.assertEqual(compare([after], [before])["regressed_policy_outcomes"], 1)
        self.assertFalse(compare([before], [])["complete"])
        after["expected_composed"] = "allow"
        with self.assertRaises(ValueError):
            compare([before], [after])
        with self.assertRaises(ValueError):
            compare([before], [before, before])
