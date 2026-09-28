"""Global confidence gates change acceptance, never authorization or error handling."""

import copy
import math

import test_evaluation
from test_evaluation import ScriptedBackend, answer
from test_foundation import Workspace, write_collection, write_policy

from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.config import preview
from humanwill_policies.contracts import validate_contract
from humanwill_policies.errors import PolicyError


def v4(config, thresholds=None):
    config = copy.deepcopy(config)
    config["format"] = "humanwill.config/4"
    for binding in config["policies"].values():
        binding.pop("monitor_min_confidence", None)
        binding.get("evaluation_profile", {}).pop("min_confidence", None)
    if thresholds is not None:
        config["outcome_thresholds"] = thresholds
    return config


class OutcomeThresholdTests(Workspace):
    config = test_evaluation.EvaluationTests.config
    enforcing = test_evaluation.EvaluationTests.enforcing
    metadata_config = test_evaluation.EvaluationTests.metadata_config
    fact = test_evaluation.EvaluationTests.fact
    run_evaluation = test_evaluation.EvaluationTests.run_evaluation

    thresholds = {"applicable": 0.8, "not_applicable": 0.7, "insufficient_evidence": 0.6}

    def test_every_outcome_below_at_and_above_threshold(self):
        for scoped in (False, True):
            config = v4(
                self.metadata_config("scoped_predicates") if scoped else self.enforcing(),
                self.thresholds,
            )
            choices = (
                {"applicable": "block", "not_applicable": "allow"}
                if scoped
                else {"violation": "block", "compliant": "allow"}
            )
            choices["insufficient_evidence"] = "evaluation_error"
            for choice, accepted in choices.items():
                key = {"violation": "applicable", "compliant": "not_applicable"}.get(choice, choice)
                threshold = self.thresholds[key]
                for confidence in (threshold - 0.01, threshold, threshold + 0.01):
                    with self.subTest(scoped=scoped, choice=choice, confidence=confidence):
                        result = self.run_evaluation(
                            ScriptedBackend({"RULE": answer(choice, confidence, scoped)}),
                            config,
                            facts=[self.fact([])] if scoped else None,
                        )
                        low = confidence < threshold
                        self.assertEqual(
                            result["decision"], "evaluation_error" if low else accepted
                        )
                        row = result["policies"][0]
                        self.assertEqual(row["evidence"]["choice"], choice)
                        if low or choice == "insufficient_evidence":
                            self.assertEqual(
                                row["reasons"],
                                ["low_confidence" if low else "model_indeterminate"],
                            )

    def test_applicable_does_not_bypass_trusted_permissions(self):
        config = v4(self.metadata_config("scoped_predicates"), self.thresholds)
        for facts, expected in [(None, "evaluation_error"), ([self.fact()], "allow")]:
            result = self.run_evaluation(
                ScriptedBackend({"RULE": answer("applicable", 0.8, True)}), config, facts=facts
            )
            self.assertEqual(result["decision"], expected)

    def test_uncertainty_and_enforcement_are_separate(self):
        for mode, on_error, requested in [
            ("monitor", "block", "none"),
            ("enforce", "block", "block"),
            ("enforce", "allow", "allow"),
        ]:
            for choice, confidence in [("insufficient_evidence", 0.9), ("compliant", 0.69)]:
                config = v4(self.enforcing(on_error=on_error), self.thresholds)
                config["policies"]["RULE"]["mode"] = mode
                result = self.run_evaluation(
                    ScriptedBackend({"RULE": answer(choice, confidence)}), config
                )
                self.assertEqual(result["decision"], "evaluation_error")
                self.assertEqual(result["enforcement"]["requested"], requested)

    def test_tied_probabilities_remain_uncertain_even_at_zero_threshold(self):
        value = answer("not_applicable", 1, True)
        value["probabilities"] = {
            "applicable": 0.5,
            "not_applicable": 0.5,
            "insufficient_evidence": 0,
        }
        result = self.run_evaluation(
            ScriptedBackend({"RULE": value}),
            v4(self.metadata_config("scoped_predicates"), dict.fromkeys(self.thresholds, 0)),
            facts=[self.fact([])],
        )
        self.assertEqual(result["decision"], "evaluation_error")

    def test_global_thresholds_apply_to_all_policies(self):
        write_policy(self.root, "other.md", "OTHER")
        write_collection(self.root, ["rule.md", "other.md"])
        config = v4(self.enforcing(), self.thresholds)
        config["policies"]["OTHER"] = copy.deepcopy(config["policies"]["RULE"])
        backend = ScriptedBackend({key: answer("compliant", 0.75) for key in config["policies"]})
        result = self.run_evaluation(backend, config)
        self.assertEqual(result["decision"], "allow")
        self.assertEqual(len(result["policies"]), 2)
        self.assertNotIn("outcome_thresholds", str(backend.calls))

    def test_default_thresholds_hashing_and_preview(self):
        bundle = load_bundle(self.root)
        document = v4(self.config())
        original = copy.deepcopy(document)
        implicit = load_configuration(bundle, document)
        explicit = load_configuration(
            bundle, v4(self.config(), dict.fromkeys(self.thresholds, 0.8))
        )
        self.assertEqual(document, original)
        self.assertEqual(implicit.sha256, explicit.sha256)
        self.assertEqual(
            preview(bundle, implicit)["configuration"]["outcome_thresholds"],
            dict.fromkeys(self.thresholds, 0.8),
        )
        validate_contract("config", implicit.to_dict())
        for key in self.thresholds:
            changed = implicit.to_dict()
            changed["outcome_thresholds"][key] = 0.7
            self.assertNotEqual(implicit.sha256, load_configuration(bundle, changed).sha256)
        for confidence, expected in [(0.79, "evaluation_error"), (0.8, "allow")]:
            self.assertEqual(
                self.run_evaluation(
                    ScriptedBackend({"RULE": answer("compliant", confidence)}), document
                )["decision"],
                expected,
            )

    def test_invalid_or_conflicting_settings_are_rejected(self):
        bundle = load_bundle(self.root)
        variants = []
        for value in (-0.1, 1.1, True, "0.7", None, math.nan, math.inf):
            for key in self.thresholds:
                variants.append(v4(self.config(), {**self.thresholds, key: value}))
        variants.extend(
            [
                v4(self.config(), {}),
                v4(self.config(), {"applicable": 0.8}),
                v4(self.config(), {**self.thresholds, "allow": 0.7}),
            ]
        )
        for key, value in [
            ("monitor_min_confidence", 0.7),
            ("outcome_thresholds", self.thresholds),
        ]:
            config = v4(self.config())
            config["policies"]["RULE"][key] = value
            variants.append(config)
        config = v4(self.enforcing())
        config["policies"]["RULE"]["evaluation_profile"]["min_confidence"] = 0.7
        variants.append(config)
        for config in variants:
            with self.subTest(config=config), self.assertRaises(PolicyError):
                load_configuration(bundle, config)

    def test_old_configuration_behavior_is_preserved(self):
        bundle = load_bundle(self.root)
        for version in (2, 3):
            config = self.enforcing()
            config["format"] = f"humanwill.config/{version}"
            self.assertNotIn("outcome_thresholds", load_configuration(bundle, config).to_dict())
            self.assertEqual(
                self.run_evaluation(ScriptedBackend({"RULE": answer("compliant", 0.85)}), config)[
                    "decision"
                ],
                "evaluation_error",
            )
            config["outcome_thresholds"] = self.thresholds
            self.fails("schema_error", lambda config=config: load_configuration(bundle, config))

    def test_v3_scopes_and_predicate_short_circuit_are_retained(self):
        config = v4(self.metadata_config("scoped_predicates"))
        binding = config["policies"]["RULE"]
        binding["scope_by_stage"] = {"prompt": binding.pop("scope")}
        binding["predicate_short_circuit"] = True
        backend = ScriptedBackend({})
        result = self.run_evaluation(backend, config, facts=[self.fact()])
        self.assertEqual(result["decision"], "allow")
        self.assertFalse(backend.calls)
        backend = ScriptedBackend({"RULE": answer("applicable", 0.8, True)})
        self.assertEqual(
            self.run_evaluation(backend, config, facts=[self.fact([])])["decision"], "block"
        )
        self.assertEqual(backend.calls[0]["questions"]["RULE"]["instructions"]["stage"], "prompt")

    def test_historical_measurement_gates_reject_changed_evaluator(self):
        from evals.step6.gates import audit_candidate
        from evals.step6.release_holdout import validate_protocol as holdout_protocol
        from evals.step6.reviewed_live import validate_protocol as reviewed_protocol

        # No test-only source fixture here: changing core code invalidates old live protocols.
        for validate in [audit_candidate, lambda: holdout_protocol(False), reviewed_protocol]:
            with self.subTest(validate=validate), self.assertRaisesRegex(ValueError, "changed"):
                validate()
