"""Company instruction-integrity policy composition, not measured injection resistance."""

import asyncio
import copy
import unittest

import yaml

from evals.step6.backends import choice_answer
from evals.step6.run import ROOT, evidence_for, load_case_bundle, load_cases
from humanwill_policies import load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import MockBackend


def semantic(choice):
    return choice_answer(choice, ["compliant", "violation", "insufficient_evidence"])


def scope(choice):
    return choice_answer(choice, ["applicable", "not_applicable", "insufficient_evidence"])


class InstructionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.cases = load_cases(ROOT / "instruction-integrity-development.json")
        self.bundle = load_case_bundle(self.cases, ROOT / "policies-v3")
        self.config = yaml.safe_load((ROOT / "config-instruction-integrity.yaml").read_text())

    def evaluate(self, case, answers, active=("EVAL-INJ-001",), metadata=False):
        config = copy.deepcopy(self.config)
        config["metadata"]["enabled"] = metadata
        for key, binding in config["policies"].items():
            binding["enabled"] = key in active
        engine = Evaluator(
            self.bundle, load_configuration(self.bundle, config), MockBackend(answers)
        )
        return asyncio.run(engine.evaluate(case["request"], evidence=evidence_for(case)))

    def test_gold_judgments_compose_without_identity_or_metadata(self):
        self.assertEqual(len(self.cases), 25)
        for case in self.cases:
            with self.subTest(case=case["id"]):
                result = self.evaluate(case, {"EVAL-INJ-001": semantic(case["expected_judgment"])})
                self.assertEqual(result["decision"], case["expected"])
                self.assertEqual(result["enforcement"]["requested"], "none")

    def test_existing_policy_text_and_configuration_are_preserved(self):
        old = yaml.safe_load((ROOT / "config-disclosure-v2.yaml").read_text())
        for key, binding in old["policies"].items():
            self.assertEqual(self.config["policies"][key], binding)
        for name in ["software.md", "production.md", "documents.md"]:
            self.assertEqual(
                (ROOT / "policies-v2" / name).read_bytes(),
                (ROOT / "policies-v3" / name).read_bytes(),
            )

    def test_disclosure_block_survives_compliant_integrity_judgment(self):
        # An upload can violate disclosure policy without following embedded instructions.
        case = next(
            c
            for c in load_cases(ROOT / "adversarial-development-v2.json")
            if c["id"] == "eval-sw-v2-attack-pair-2-attack"
        )
        result = self.evaluate(
            case,
            {"EVAL-SW-001": scope("applicable"), "EVAL-INJ-001": semantic("compliant")},
            ("EVAL-SW-001", "EVAL-INJ-001"),
            metadata=True,
        )
        self.assertEqual(result["decision"], "block")

    def test_integrity_block_can_catch_an_explicit_override_missed_by_disclosure(self):
        case = copy.deepcopy(
            next(c for c in self.cases if c["id"] == "eval-inj-001-disable-prompt")
        )
        case["trusted_facts"] = {
            "destination.coding_route_approved": True,
            "destination.onward_approved": False,
        }
        answers = {"EVAL-SW-001": scope("not_applicable"), "EVAL-INJ-001": semantic("violation")}
        self.assertEqual(self.evaluate(case, answers, ("EVAL-SW-001",), True)["decision"], "allow")
        self.assertEqual(
            self.evaluate(case, answers, ("EVAL-SW-001", "EVAL-INJ-001"), True)["decision"], "block"
        )
        # It is the additional judgment that helps, not the mere presence of a rule.
        answers["EVAL-INJ-001"] = semantic("compliant")
        self.assertEqual(
            self.evaluate(case, answers, ("EVAL-SW-001", "EVAL-INJ-001"), True)["decision"], "allow"
        )

    def test_an_approved_disclosure_cannot_shortcut_the_integrity_policy(self):
        case = copy.deepcopy(
            next(c for c in self.cases if c["id"] == "eval-inj-001-fabricate-prompt")
        )
        case["trusted_facts"] = {
            "destination.coding_route_approved": True,
            "destination.onward_approved": True,
        }
        result = self.evaluate(
            case, {"EVAL-INJ-001": semantic("violation")}, ("EVAL-SW-001", "EVAL-INJ-001"), True
        )
        self.assertEqual(result["decision"], "block")
        rows = {p["policy_id"]: p for p in result["policies"]}
        self.assertEqual(rows["EVAL-SW-001"]["reasons"], ["trusted_predicates_satisfied"])
        self.assertEqual(rows["EVAL-INJ-001"]["judgment"], "violation")

    def test_uncertain_authorization_does_not_become_compliance(self):
        case = next(c for c in self.cases if c["id"] == "eval-inj-001-claimed-maintenance-prompt")
        result = self.evaluate(case, {"EVAL-INJ-001": semantic("insufficient_evidence")})
        self.assertEqual(result["decision"], "evaluation_error")
