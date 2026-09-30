"""Stage-only routing and full-pack composition checks, without provider calls."""

import asyncio
import copy
import unittest

from test_policy_isolation import ScriptedBackend

from evals.step6.policy_isolation import StoredBackend, eligible_policies, evaluate
from evals.step6.run import select_configuration
from evals.step6.source_approval import source_evidence_for
from evals.step6.stage_tool import ARMS, load_inputs, routed_arm
from evals.step6.tool_probe import followup_payload, refine
from humanwill_policies import load_configuration


class StageToolTests(unittest.TestCase):
    def test_routing_requires_actual_tool_stage(self):
        for stage in ("submitted_prompt", "model_request", "response", None, "other"):
            self.assertEqual(routed_arm(stage, "stage_tool"), "q04")
        self.assertEqual(routed_arm("tool_action", "stage_tool"), "tool_wording")
        self.assertEqual(routed_arm("tool_action", "q04"), "q04")
        with self.assertRaises(ValueError):
            routed_arm("tool_action", "bad")

    def test_full_pack_composition_and_unchanged_payload_fields(self):
        cases, bundle, config, catalog, contexts = load_inputs()
        self.assertEqual(len(cases), 175)
        for case in cases:
            with self.subTest(case=case["id"]):
                loaded = load_configuration(
                    bundle,
                    select_configuration(
                        config, case["policy_id"], case.get("also_policy_ids", [])
                    ),
                )
                evidence = source_evidence_for(case, catalog)
                first_backend = ScriptedBackend(case["scope_by_policy"], low=True)
                first = asyncio.run(
                    evaluate(case, bundle, loaded, first_backend, contexts[case["id"]], evidence)
                )
                for arm in ARMS:
                    result = first
                    if eligible_policies(first):
                        (record,) = first_backend.records
                        branch = ScriptedBackend(case["scope_by_policy"])
                        actual_arm = routed_arm(case["request"]["stage"], arm)
                        merged, notes = asyncio.run(
                            refine(record, first, actual_arm, {}, branch, config)
                        )
                        self.assertLessEqual(notes["calls"], 1)
                        payload = branch.records[0]["payload"]
                        self.assertEqual(
                            payload, followup_payload(record["payload"], actual_arm, {})
                        )
                        # Wording changes only; state, policies, conditions and question IDs stay.
                        original = followup_payload(record["payload"], "q04", {})
                        normalized = copy.deepcopy(payload)
                        for pid, question in normalized["questions"].items():
                            question["instructions"]["task"] = original["questions"][pid][
                                "instructions"
                            ]["task"]
                            question["criteria"] = original["questions"][pid]["criteria"]
                        self.assertEqual(normalized, original)
                        result = asyncio.run(
                            evaluate(
                                case,
                                bundle,
                                loaded,
                                StoredBackend(branch, record["payload"], merged),
                                contexts[case["id"]],
                                evidence,
                            )
                        )
                    self.assertEqual(result["decision"], case["expected_composed"])
