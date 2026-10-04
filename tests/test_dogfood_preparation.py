"""Publication-preparation research checks; no live calls."""

import asyncio
import copy
import json
import unittest

from evals.dogfood.evaluate import BASE
from evals.dogfood.preparation import assess_arm, profiles
from evals.step6.backends import choice_answer
from humanwill_policies.providers import MockBackend


class Capture(MockBackend):
    async def evaluate(self, payload, **kwargs):
        self.payload = copy.deepcopy(payload)
        return await super().evaluate(payload, **kwargs)


class PreparationTests(unittest.TestCase):
    def cases(self):
        return json.loads((BASE / "preparation-v1/cases.json").read_text())["cases"]

    def test_approval_changes_decision_but_never_becomes_model_input(self):
        b, c, *_ = profiles()[0]["v4"]
        payloads = []
        for case in self.cases()[:3]:
            backend = Capture(
                {
                    pid: choice_answer(
                        choice, ["applicable", "not_applicable", "insufficient_evidence"]
                    )
                    for pid, choice in case["expected_scope_v4"].items()
                }
            )
            result = asyncio.run(assess_arm(case, b, c, backend, "workflow", "v4"))
            self.assertEqual(result["decision"], case["review"]["expected_decision"])
            payloads.append(backend.payload)
        self.assertEqual(payloads[0], payloads[1])
        self.assertEqual(payloads[1], payloads[2])

    def test_policy_change_leaves_context_and_other_instructions_identical(self):
        case = self.cases()[0]
        payloads = []
        for arm in ("v3", "v4"):
            b, c, *_ = profiles()[0][arm]
            backend = Capture(
                {
                    pid: choice_answer(
                        choice, ["applicable", "not_applicable", "insufficient_evidence"]
                    )
                    for pid, choice in case["expected_scope_v4"].items()
                }
            )
            asyncio.run(assess_arm(case, b, c, backend, "workflow", arm))
            payload = backend.payload
            policy = payload["questions"]["EVAL-SW-001"]["instructions"]["policy"]
            self.assertEqual(policy.pop("version"), arm[1:])
            policy.pop("text")
            payloads.append(payload)
        self.assertEqual(payloads[0], payloads[1])


if __name__ == "__main__":
    unittest.main()
