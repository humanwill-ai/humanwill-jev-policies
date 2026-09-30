"""Research-only classification uses runtime data, keeps policies and trusted checks."""

import asyncio
import copy
import json
import unittest

from test_policy_isolation import ScriptedBackend

from evals.step6.policy_isolation import StoredBackend, eligible_policies, evaluate
from evals.step6.run import select_configuration
from evals.step6.short_questions import transform
from evals.step6.source_approval import source_evidence_for
from evals.step6.tool_probe import (
    ARMS,
    BASE,
    classifier_payload,
    followup_payload,
    load_inputs,
    qualified,
    refine,
)
from evals.step6.tool_probe import (
    validate_experiment as validate_live,
)
from humanwill_policies import load_configuration
from humanwill_policies.providers import validate_response


def validate_experiment():
    return load_inputs(json.loads((BASE / "protocol.json").read_text()))


def classification(intent="proposed_execution", operation="local_transform", confidence=0.9):
    questions = classifier_payload({"model": "test", "state": {}})["questions"]
    return {
        "answers": {
            key: {
                "choice": choice,
                "confidence": confidence,
                "probabilities": {
                    label: float(label == choice) for label in questions[key]["criteria"]
                },
            }
            for key, choice in [("tool_use", intent), ("operation", operation)]
        },
        "duration_ms": 0,
    }


class ToolProbeTests(unittest.TestCase):
    def test_all_selected_cases_preserve_payload_and_gold_composition(self):
        _, cases, bundle, config, catalog, contexts = validate_experiment()
        self.assertEqual(len(cases), 16)
        for case in cases:
            with self.subTest(case=case["id"]):
                loaded = load_configuration(
                    bundle,
                    select_configuration(
                        config, case["policy_id"], case.get("also_policy_ids", [])
                    ),
                )
                evidence = source_evidence_for(case, catalog)
                primary = ScriptedBackend(case["scope_by_policy"], low=True)
                first = asyncio.run(
                    evaluate(case, bundle, loaded, primary, contexts[case["id"]], evidence)
                )
                record = primary.records[0]
                classifier = classifier_payload(record["payload"])
                self.assertEqual(classifier["state"], record["payload"]["state"])
                self.assertEqual(set(classifier["questions"]), {"tool_use", "operation"})
                self.assertNotIn("expected", str(classifier))
                for arm in ARMS:
                    backend = ScriptedBackend(case["scope_by_policy"])
                    merged, notes = asyncio.run(
                        refine(record, first, arm, classification(), backend, config)
                    )
                    validate_response(
                        merged, record["payload"]["questions"], backend.accepted_models
                    )
                    out = asyncio.run(
                        evaluate(
                            case,
                            bundle,
                            loaded,
                            StoredBackend(backend, record["payload"], merged),
                            contexts[case["id"]],
                            evidence,
                        )
                    )
                    self.assertEqual(out["decision"], case["expected_composed"])
                    self.assertLessEqual(notes["calls"], 1)
                    if not backend.records:
                        continue
                    actual = copy.deepcopy(backend.records[0]["payload"])
                    actual["state"].pop("model_operation_hypothesis", None)
                    self.assertEqual(actual["state"], record["payload"]["state"])
                    self.assertEqual(set(actual["questions"]), set(record["payload"]["questions"]))
                    for pid, q in actual["questions"].items():
                        self.assertEqual(
                            q["instructions"]["policy"],
                            record["payload"]["questions"][pid]["instructions"]["policy"],
                        )
                        self.assertEqual(
                            q["instructions"]["trusted_conditions"],
                            record["payload"]["questions"][pid]["instructions"][
                                "trusted_conditions"
                            ],
                        )
                    if arm == "q04":
                        self.assertEqual(actual, transform(record["payload"], "q04"))

    def test_unknown_or_weak_classification_cannot_assert_tool_use(self):
        _, cases, bundle, config, catalog, contexts = validate_experiment()
        case = cases[0]
        loaded = load_configuration(
            bundle, select_configuration(config, case["policy_id"], case["also_policy_ids"])
        )
        backend = ScriptedBackend(case["scope_by_policy"])
        asyncio.run(
            evaluate(
                case,
                bundle,
                loaded,
                backend,
                contexts[case["id"]],
                source_evidence_for(case, catalog),
            )
        )
        payload = backend.records[0]["payload"]
        for c in [
            classification("unknown"),
            classification("no_execution"),
            classification(confidence=0.69),
            {"answers": {}},
        ]:
            self.assertEqual(
                followup_payload(payload, "classified_tool", c), transform(payload, "q04")
            )
        unknown = followup_payload(payload, "classified_tool", classification(operation="unknown"))
        self.assertNotIn("model_operation_hypothesis", unknown["state"])
        self.assertFalse(qualified({"confidence": 1, "probabilities": {"a": 0.5, "b": 0.5}}))
        with self.assertRaises(ValueError):
            followup_payload(payload, "invalid", classification())

    def test_classification_time_is_inside_total_budget(self):
        _, cases, bundle, config, catalog, contexts = validate_experiment()
        case = cases[0]
        loaded = load_configuration(
            bundle, select_configuration(config, case["policy_id"], case["also_policy_ids"])
        )
        primary = ScriptedBackend(case["scope_by_policy"], low=True)
        first = asyncio.run(
            evaluate(
                case,
                bundle,
                loaded,
                primary,
                contexts[case["id"]],
                source_evidence_for(case, catalog),
            )
        )
        self.assertTrue(eligible_policies(first))
        c = classification()
        c["duration_ms"] = 15001
        secondary = ScriptedBackend(case["scope_by_policy"])
        merged, notes = asyncio.run(
            refine(primary.records[0], first, "classified_tool", c, secondary, config)
        )
        self.assertEqual(notes["error"], "evaluation_timeout")
        self.assertEqual(notes["calls"], 0)
        self.assertEqual(merged, primary.records[0]["raw_response"])

    def test_historical_paid_guard_rejects_post_measurement_source_cleanup(self):
        with self.assertRaisesRegex(ValueError, "Frozen"):
            validate_live()
