"""Isolated retries preserve real composition and cannot use gold labels for routing."""

import asyncio
import copy
import json
import unittest

from offline_reviewed_fixture import reviewed_inputs as validate_experiment

from evals.step6.backends import choice_answer
from evals.step6.policy_isolation import (
    ARMS,
    StoredBackend,
    eligible_policies,
    evaluate,
    followup_payloads,
    merge_answers,
    refine,
)
from evals.step6.run import select_configuration
from evals.step6.short_questions import transform
from evals.step6.source_approval import source_evidence_for
from humanwill_policies import load_configuration
from humanwill_policies.providers import validate_response

OPTIONS = ["applicable", "not_applicable", "insufficient_evidence"]
GATES = {"applicable": 0.8, "not_applicable": 0.7, "insufficient_evidence": 0.8}


class ScriptedBackend:
    transport, model = "openrouter", "typesafe/jev-1.13"
    accepted_models = ("typesafe/jev-1.13-20260917",)

    def __init__(self, scopes, low=False, malformed=False):
        self.scopes, self.low, self.malformed = scopes, low, malformed
        self.records = []
        self.backend = self
        self.fatal = False

    async def evaluate(self, payload, **kwargs):
        answers = {pid: choice_answer(self.scopes[pid], OPTIONS) for pid in payload["questions"]}
        if self.low:
            for answer in answers.values():
                if answer["choice"] != "insufficient_evidence":
                    answer["confidence"] = 0.1
        if self.malformed:
            answer = next(iter(answers.values()))
            answer["probabilities"][answer["choice"]] = 0.99
        response = {
            "model": self.accepted_models[0],
            "answers": answers,
            "usage": {"input_tokens": 0, "output_tokens": 0, "cost": 0},
        }
        self.records.append({"payload": copy.deepcopy(payload), "raw_response": response})
        return response


def result_for(choice="not_applicable", reason="low_confidence", decision="evaluation_error"):
    return {
        "decision": decision,
        "duration_ms": 0,
        "policies": [
            {
                "policy_id": "p",
                "status": "error",
                "reasons": [reason],
                "evidence": {"choice": choice},
            }
        ],
    }


class PolicyIsolationTests(unittest.TestCase):
    def test_runtime_selector_rejects_settled_missing_and_unknown_results(self):
        self.assertEqual(eligible_policies(result_for()), ["p"])
        self.assertEqual(eligible_policies(result_for("applicable")), ["p"])
        for kwargs in [
            {"choice": "insufficient_evidence"},
            {"reason": "missing_trusted_metadata"},
            {"reason": "malformed_response"},
            {"decision": "block"},
            {"decision": "allow"},
        ]:
            self.assertEqual(eligible_policies(result_for(**kwargs)), [])

    def test_all_175_case_compositions_with_injected_uncertainty(self):
        _, cases, bundle, config, catalog, contexts = validate_experiment()
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
                if not eligible_policies(first):
                    self.assertEqual(first["decision"], case["expected_composed"])
                    continue
                record = first_backend.records[0]
                for arm in ARMS:
                    followup = ScriptedBackend(case["scope_by_policy"])
                    merged, notes = asyncio.run(refine(record, first, arm, followup, GATES, 15000))
                    validate_response(
                        merged, record["payload"]["questions"], followup.accepted_models
                    )
                    stored = StoredBackend(followup, record["payload"], merged)
                    result = asyncio.run(
                        evaluate(case, bundle, loaded, stored, contexts[case["id"]], evidence)
                    )
                    self.assertEqual(result["decision"], case["expected_composed"])
                    self.assertLessEqual(notes["calls"], 2)
                    for exchange in followup.records:
                        actual, original = exchange["payload"], record["payload"]
                        self.assertEqual(actual["state"], original["state"])
                        self.assertEqual(actual["model"], original["model"])
                        if arm == "repeat_q05":
                            self.assertEqual(actual, original)
                        else:
                            self.assertEqual(len(actual["questions"]), 1)
                            expected = (
                                transform(original, "q04") if arm == "isolate_q04" else original
                            )
                            for pid, question in actual["questions"].items():
                                self.assertEqual(question, expected["questions"][pid])
                    # Diagnostic fixture labels never appear in the model state or questions.
                    self.assertNotIn('"expected_composed"', json.dumps(record["payload"]))

    def test_merge_requires_agreement_confidence_and_preserves_other_policies(self):
        primary = {"answers": {p: choice_answer("not_applicable", OPTIONS) for p in ("p", "q")}}
        for pid in primary["answers"]:
            primary["answers"][pid]["confidence"] = 0.1
        for choice, confidence, accepted in [
            ("not_applicable", 0.7, True),
            ("not_applicable", 0.69, False),
            ("applicable", 1.0, False),
            ("insufficient_evidence", 1.0, False),
        ]:
            answer = choice_answer(choice, OPTIONS)
            answer["confidence"] = confidence
            result, ids, _ = merge_answers(primary, {"p": answer}, ["p"], GATES)
            self.assertEqual(ids, ["p"] if accepted else [])
            self.assertEqual(result["answers"]["q"], primary["answers"]["q"])
            if not accepted:
                self.assertEqual(result, primary)

    def test_malformed_retry_and_expired_deadline_do_not_change_primary(self):
        payload = {
            "model": ScriptedBackend.model,
            "state": {},
            "questions": {"p": {"type": "choice", "criteria": dict.fromkeys(OPTIONS, "test")}},
        }
        initial = ScriptedBackend({"p": "not_applicable"}, low=True)
        asyncio.run(initial.evaluate(payload))
        record = initial.records[0]
        followup = ScriptedBackend({"p": "not_applicable"}, malformed=True)
        merged, notes = asyncio.run(
            refine(record, result_for(), "repeat_q05", followup, GATES, 15000)
        )
        self.assertEqual(merged, record["raw_response"])
        self.assertEqual(notes["rejected"], {"p": "malformed_response"})
        expired = result_for()
        expired["duration_ms"] = 15001
        unused = ScriptedBackend({"p": "not_applicable"})
        _, notes = asyncio.run(refine(record, expired, "repeat_q05", unused, GATES, 15000))
        self.assertEqual(notes["calls"], 0)
        self.assertEqual(unused.records, [])

    def test_unknown_policy_cannot_be_requested(self):
        with self.assertRaises(ValueError):
            followup_payloads({"questions": {}}, ["not-in-bundle"], "isolate_q05")
