"""Frozen experiment contracts; scripted answers are not model-quality evidence."""

import asyncio
import copy
import unittest

from test_conversation_live import CaptureBackend
from test_conversation_structure import answers

from evals.step6.conversation_structure import flatten
from evals.step6.conversation_structure import transform as structural_transform
from evals.step6.conversation_views import ARMS, assess, load_inputs, transform
from humanwill_policies.errors import PolicyError


class PolicyViewsTests(unittest.TestCase):
    def test_all_30_cases_all_arms_preserve_policies_and_gold_composition(self):
        cases, bundle, config = load_inputs()
        self.assertEqual(len(cases), 30)
        for case in cases:
            calls = {}
            for arm in ARMS:
                backend = CaptureBackend(answers(case))
                result = asyncio.run(assess(case, bundle, config, backend, arm))
                self.assertEqual(result["decision"], case["expected_composed"])
                self.assertEqual(len(backend.calls), 1)
                calls[arm] = backend.calls[0]
            flat = calls["flat"]
            self.assertEqual(calls["structured"], structural_transform(flat, "structured"))
            candidate = calls["policy_views"]
            self.assertEqual(candidate["state"]["content"], flat["state"]["content"])
            restored = copy.deepcopy(candidate)
            if "conversation" in restored["state"]:
                self.assertEqual(
                    flatten(restored["state"].pop("conversation")), flat["state"]["content"]
                )
                for question in restored["questions"].values():
                    question["instructions"].pop("assessment_subject")
            self.assertEqual(restored, flat)

    def test_roleless_candidate_is_identical_flat_not_reparsed(self):
        cases, bundle, config = load_inputs()
        for case in cases:
            if not case["id"].startswith("flat-"):
                continue
            backend = CaptureBackend(answers(case))
            for arm in ["flat", "policy_views"]:
                asyncio.run(assess(case, bundle, config, backend, arm))
            self.assertEqual(backend.calls[0], backend.calls[1])
            self.assertNotIn("conversation", backend.calls[1]["state"])

    def test_subject_is_operator_configuration_not_strategy_or_id_heuristic(self):
        payload = {
            "state": {
                "stage": "model_request",
                "content": [{"kind": "text", "role": "user", "text": "hello"}],
            },
            "questions": {"ARBITRARY": {"instructions": {}}, "ANOTHER": {"instructions": {}}},
        }
        subjects = {"ARBITRARY": "whole_payload", "ANOTHER": "current_operation"}
        output = transform(payload, "policy_views", subjects)
        self.assertEqual(
            output["questions"]["ARBITRARY"]["instructions"]["assessment_subject"]["view"],
            "state.content",
        )
        self.assertEqual(
            output["questions"]["ANOTHER"]["instructions"]["assessment_subject"]["view"],
            "state.conversation",
        )
        for invalid in [
            {},
            {"ARBITRARY": "current_operation"},
            {"ARBITRARY": "skip", "ANOTHER": "whole_payload"},
        ]:
            with self.assertRaises(ValueError):
                transform(payload, "policy_views", invalid)

    def test_labels_notes_and_claims_cannot_change_subject_configuration(self):
        cases, bundle, config = load_inputs()
        case = cases[0]
        changed = copy.deepcopy(case)
        changed.update(
            expected_choices={},
            expected_by_policy={},
            expected_composed="block",
            reason="approved",
            category="whole_payload",
        )
        backend = CaptureBackend(answers(case))
        for item in [case, changed]:
            asyncio.run(assess(item, bundle, config, backend, "policy_views"))
        self.assertEqual(backend.calls[0], backend.calls[1])

    def test_history_secret_stays_in_both_views_and_secret_question_uses_full_payload(self):
        cases, bundle, config = load_inputs()
        case = next(c for c in cases if c["id"] == "secret-retained-history")
        backend = CaptureBackend(answers(case))
        asyncio.run(assess(case, bundle, config, backend, "policy_views"))
        payload = backend.calls[0]
        self.assertEqual(flatten(payload["state"]["conversation"]), case["request"]["content"])
        self.assertEqual(
            payload["questions"]["CONV-SECRET-001"]["instructions"]["assessment_subject"]["kind"],
            "whole_payload",
        )
        self.assertEqual(payload["state"]["content"], case["request"]["content"])

    def test_low_confidence_still_uses_bounded_followup_and_unchanged_gates(self):
        cases, bundle, config = load_inputs()
        case = next(c for c in cases if c["id"] == "local-review-control")
        low = answers(case)
        low["EVAL-SW-001"]["confidence"] = 0.4
        backend = CaptureBackend(low)
        result = asyncio.run(assess(case, bundle, config, backend, "policy_views"))
        self.assertEqual(result["decision"], "evaluation_error")
        self.assertEqual(len(backend.calls), 2)
        self.assertEqual(backend.calls[0]["state"], backend.calls[1]["state"])
        for pid in backend.calls[1]["questions"]:
            self.assertEqual(
                backend.calls[0]["questions"][pid]["instructions"]["assessment_subject"],
                backend.calls[1]["questions"][pid]["instructions"]["assessment_subject"],
            )

    def test_invalid_arm_stage_and_doubled_size_limit(self):
        payload = {
            "state": {
                "stage": "model_request",
                "content": [{"kind": "text", "role": "user", "text": "x" * 12500}],
            },
            "questions": {},
        }
        with self.assertRaises(PolicyError):
            transform(payload, "policy_views")
        with self.assertRaises(ValueError):
            transform(payload, "skip_history")
        payload["state"]["stage"] = "response"
        with self.assertRaises(ValueError):
            transform(payload, "policy_views")


if __name__ == "__main__":
    unittest.main()
