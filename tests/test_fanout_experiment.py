"""Offline guards for an isolated experiment; no runtime profile is added."""

import copy
import unittest

from evals.step6.backends import choice_answer
from evals.step6.fanout import FanoutBackend, expand
from humanwill_policies.errors import PolicyError
from humanwill_policies.questions import scoped_variant

LABELS = ["applicable", "not_applicable", "insufficient_evidence"]


class Wire:
    transport = "mock"
    model = "mock"
    accepted_models = ("mock",)

    def __init__(self, choices):
        self.choices = choices
        self.calls = 0

    async def evaluate(self, payload, **kwargs):
        self.calls += 1
        answers = {}
        for key in payload["questions"]:
            variant = key.split("__")[0]
            choice, confidence = self.choices[variant]
            answers[key] = choice_answer(choice, LABELS)
            answers[key]["confidence"] = confidence
        return {
            "model": "mock",
            "usage": {"input_tokens": 1, "output_tokens": 1, "cost": 0.001},
            "answers": answers,
        }


def payload(stage="tool_action"):
    q = {
        "type": "choice",
        "instructions": {
            "policy": {"text": "Original policy"},
            "trusted_conditions": {"required_fields": [], "meaning": ""},
        },
        "criteria": {k: k for k in LABELS},
    }
    return {
        "model": "mock",
        "state": {"stage": stage, "content": []},
        "questions": {"P": scoped_variant(q, "q05")},
    }


class FanoutTests(unittest.IsolatedAsyncioTestCase):
    async def run_case(self, answers, stage="tool_action"):
        wire = Wire(answers)
        wrapper = FanoutBackend(
            wire, {"applicable": 0.8, "not_applicable": 0.7, "insufficient_evidence": 0.8}
        )
        original = payload(stage)
        primary = await wrapper.evaluate(original)
        second = copy.deepcopy(original)
        second["questions"]["P"] = scoped_variant(
            second["questions"]["P"], "tool_action" if stage == "tool_action" else "q04"
        )
        secondary = await wrapper.evaluate(second)
        self.assertEqual(wire.calls, 1)
        self.assertEqual(primary["usage"]["cost"], 0.001)
        self.assertEqual(secondary["usage"]["cost"], 0)
        return primary["answers"]["P"], secondary["answers"]["P"], wrapper

    async def test_agreeing_q04_can_rescue_tool_uncertainty(self):
        first, second, wrapper = await self.run_case(
            {
                "q05": ("not_applicable", 0.5),
                "q04": ("not_applicable", 0.9),
                "tool_action": ("not_applicable", 0.5),
            }
        )
        self.assertEqual(first["confidence"], 0.5)
        self.assertEqual(second["confidence"], 0.9)
        self.assertEqual(wrapper.notes["P"], "q04")

    async def test_qualified_conflict_vetoes_rescue(self):
        first, second, wrapper = await self.run_case(
            {
                "q05": ("not_applicable", 0.5),
                "q04": ("applicable", 0.9),
                "tool_action": ("not_applicable", 0.9),
            }
        )
        self.assertEqual(first, second)
        self.assertEqual(wrapper.notes["P"], "qualified_disagreement")

    async def test_qualified_unknown_vetoes_rescue(self):
        first, second, _ = await self.run_case(
            {
                "q05": ("not_applicable", 0.5),
                "q04": ("insufficient_evidence", 0.9),
                "tool_action": ("not_applicable", 0.9),
            }
        )
        self.assertEqual(first, second)

    async def test_non_tool_has_no_tool_question(self):
        expanded, _ = expand(payload("response"))
        self.assertEqual(set(expanded["questions"]), {"q05__P", "q04__P"})
        await self.run_case(
            {"q05": ("not_applicable", 0.5), "q04": ("not_applicable", 0.9)}, "response"
        )

    async def test_oversized_payload_rejected(self):
        request = payload()
        request["state"]["large"] = "x" * 24000
        with self.assertRaises(PolicyError):
            expand(request)


class FullFixtureTests(unittest.IsolatedAsyncioTestCase):
    async def test_gold_composition_both_arms(self):
        from evals.step6.fanout import load_inputs
        from evals.step6.preview_full_pack import evaluate

        class Gold:
            transport = "mock"
            model = "mock"
            accepted_models = ("mock",)

            def __init__(self, case):
                self.case = case
                self.payloads = []

            async def evaluate(self, payload, **kwargs):
                self.payloads.append(copy.deepcopy(payload))
                return {
                    "model": "mock",
                    "usage": {"input_tokens": 0, "output_tokens": 0, "cost": 0},
                    "answers": {
                        qid: choice_answer(
                            self.case["scope_by_policy"][qid.split("__")[-1]], LABELS
                        )
                        for qid in payload["questions"]
                    },
                }

        cases, bundle, config, contexts, catalog = load_inputs()
        for case in cases:
            with self.subTest(case=case["id"]):
                gold = Gold(case)
                first = await evaluate(case, bundle, config, gold, contexts, catalog)
                wire = Gold(case)
                second = await evaluate(
                    case,
                    bundle,
                    config,
                    FanoutBackend(wire, config["outcome_thresholds"]),
                    contexts,
                    catalog,
                )
                self.assertEqual(first["decision"], case["expected_composed"])
                self.assertEqual(second["decision"], case["expected_composed"])
                self.assertLessEqual(len(wire.payloads), 1)
                if wire.payloads:
                    expanded, _ = expand(gold.payloads[0])
                    self.assertEqual(wire.payloads[0], expanded)
