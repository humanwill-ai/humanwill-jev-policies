"""Paired question-batch isolation and new fixture composition checks (no API)."""

import asyncio
import copy
import unittest

from offline_reviewed_fixture import comparison_inputs as validate_experiment
from test_policy_isolation import GATES, ScriptedBackend

from evals.step6.q04_comparison import (
    ARMS,
    StoredBackend,
    eligible_policies,
    evaluate,
    followup_payloads,
    refine,
)
from evals.step6.reviewed_live import observed_policy
from evals.step6.run import select_configuration
from evals.step6.short_questions import transform
from evals.step6.source_approval import source_evidence_for
from humanwill_policies import load_configuration


class Q04ComparisonTests(unittest.TestCase):
    def test_all_cases_composition_and_paired_payloads(self):
        _, cases, bundle, config, catalog, contexts = validate_experiment()
        self.assertEqual(len(cases), 199)
        fresh = [c for c in cases if c["id"].startswith("fresh-q04-")]
        self.assertEqual(len(fresh), 24)
        self.assertEqual(
            [
                sum(c["expected_composed"] == d for c in fresh)
                for d in ("allow", "block", "evaluation_error")
            ],
            [12, 8, 4],
        )
        for case in cases:
            with self.subTest(case=case["id"]):
                loaded = load_configuration(
                    bundle,
                    select_configuration(
                        config, case["policy_id"], case.get("also_policy_ids", [])
                    ),
                )
                evidence = source_evidence_for(case, catalog)
                gold = ScriptedBackend(case["scope_by_policy"])
                result = asyncio.run(
                    evaluate(case, bundle, loaded, gold, contexts[case["id"]], evidence)
                )
                self.assertEqual(result["decision"], case["expected_composed"])
                for policy in result["policies"]:
                    if policy["policy_id"] not in case["expected_by_policy"]:
                        continue
                    self.assertEqual(
                        observed_policy(policy), case["expected_by_policy"][policy["policy_id"]]
                    )
                primary = ScriptedBackend(case["scope_by_policy"], low=True)
                first = asyncio.run(
                    evaluate(case, bundle, loaded, primary, contexts[case["id"]], evidence)
                )
                if not eligible_policies(first):
                    continue
                record = primary.records[0]
                for arm in ARMS:
                    secondary = ScriptedBackend(case["scope_by_policy"])
                    merged, notes = asyncio.run(refine(record, first, arm, secondary, GATES, 15000))
                    stored = StoredBackend(secondary, record["payload"], merged)
                    composed = asyncio.run(
                        evaluate(case, bundle, loaded, stored, contexts[case["id"]], evidence)
                    )
                    self.assertEqual(
                        composed["decision"],
                        "evaluation_error"
                        if notes["unattempted_policy_ids"]
                        and not any(
                            case["expected_by_policy"][pid] == "block" for pid in notes["accepted"]
                        )
                        else case["expected_composed"],
                    )
                    self.assertLessEqual(notes["calls"], 2)
                    for exchange in secondary.records:
                        actual = exchange["payload"]
                        wanted = transform(copy.deepcopy(record["payload"]), "q04")
                        if arm == "isolate_q04":
                            self.assertEqual(len(actual["questions"]), 1)
                            wanted["questions"] = {
                                p: wanted["questions"][p] for p in actual["questions"]
                            }
                        self.assertEqual(actual, wanted)
                if len(record["payload"]["questions"]) == 1:
                    ids = eligible_policies(first)
                    self.assertEqual(
                        followup_payloads(record["payload"], ids, ARMS[0]),
                        followup_payloads(record["payload"], ids, ARMS[1]),
                    )

    def test_invalid_arm_and_policy_rejected(self):
        for arm, ids in [("other", ["p"]), ("batch_q04", ["missing"])]:
            with self.assertRaises(ValueError):
                followup_payloads({"questions": {"p": {}}}, ids, arm)
