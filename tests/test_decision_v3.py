"""Trusted predicate shortcuts must not bypass other rules, coverage or evidence binding."""

import asyncio
import copy
import json
import unittest
from datetime import timedelta
from unittest.mock import patch

import yaml

from evals.step6.backends import JEV_MODEL, JEV_RETURNED, choice_answer
from evals.step6.run import ROOT, evidence_for, load_cases
from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.errors import PolicyError
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.runtime import EgressPermit, EvidenceContext, utc_now
from humanwill_policies.serialization import digest


class RecordingBackend:
    transport = "openrouter"
    model = JEV_MODEL
    accepted_models = (JEV_RETURNED,)

    def __init__(self, effect=None):
        self.calls = []
        self.effect = effect

    async def evaluate(self, payload, **kwargs):
        self.calls.append(payload)
        if self.effect:
            self.effect()
        return {
            "model": JEV_RETURNED,
            "usage": {"cost": 0},
            "answers": {
                key: choice_answer(
                    "applicable" if "applicable" in q["criteria"] else "violation", q["criteria"]
                )
                for key, q in payload["questions"].items()
            },
        }


class DecisionV3Tests(unittest.TestCase):
    def setUp(self):
        self.bundle = load_bundle(ROOT / "policies")
        self.config = yaml.safe_load((ROOT / "config-v3.yaml").read_text())
        self.case = copy.deepcopy(load_cases(ROOT / "development.json")[2])
        for key, binding in self.config["policies"].items():
            binding["enabled"] = key == "EVAL-SW-001"
        self.backend = RecordingBackend()

    def evaluate(self, evidence=None, permit=True):
        request = self.case["request"]
        engine = Evaluator(self.bundle, load_configuration(self.bundle, self.config), self.backend)
        return asyncio.run(
            engine.evaluate(
                request,
                evidence=evidence or evidence_for(self.case),
                egress=EgressPermit(digest(request), self.bundle.sha256, "openrouter")
                if permit
                else None,
            )
        )

    def test_positive_facts_need_no_model_or_egress_permit(self):
        result = self.evaluate(permit=False)
        self.assertEqual(result["format"], "humanwill.result/3")
        self.assertEqual(result["rubric"], "humanwill.choice/2")
        self.assertEqual(result["decision"], "allow")
        self.assertIsNone(result["evaluation"])
        self.assertFalse(self.backend.calls)
        row = next(p for p in result["policies"] if p["policy_id"] == "EVAL-SW-001")
        self.assertEqual(row["reasons"], ["trusted_predicates_satisfied"])
        self.assertNotIn("choice", row["evidence"])

    def test_no_global_allow_and_stage_specific_question(self):
        self.config["policies"]["EVAL-DOC-001"] = {
            "enabled": True,
            "mode": "monitor",
            "strategy": "semantic",
        }
        result = self.evaluate()
        self.assertEqual(result["decision"], "block")
        self.assertEqual(set(self.backend.calls[0]["questions"]), {"EVAL-DOC-001"})
        self.case["trusted_facts"]["destination.approved"] = False
        self.backend.calls.clear()
        self.evaluate()
        q = self.backend.calls[0]["questions"]["EVAL-SW-001"]["instructions"]
        self.assertEqual(q["stage"], "model_request")
        self.assertEqual(
            q["rule"], self.config["policies"]["EVAL-SW-001"]["scope_by_stage"]["model_request"]
        )
        self.assertNotIn("scope_by_stage", json.dumps(self.backend.calls))
        self.assertNotIn("destination.approved", json.dumps(self.backend.calls))

    def test_partial_or_false_predicates_do_not_short_circuit(self):
        binding = self.config["policies"]["EVAL-SW-001"]
        binding["requires_metadata"].append("authorization.allowed")
        binding["predicates"].append(
            {"field": "authorization.allowed", "op": "equals", "value": True}
        )
        self.assertEqual(self.evaluate()["decision"], "evaluation_error")
        self.assertEqual(len(self.backend.calls), 1)
        self.case["trusted_facts"]["authorization.allowed"] = False
        self.assertEqual(self.evaluate()["decision"], "block")

    def test_incomplete_coverage_cannot_short_circuit(self):
        self.case["request"]["coverage"] = {
            "inspected": ["item"],
            "omitted": ["file"],
            "complete": False,
        }
        self.assertEqual(self.evaluate()["decision"], "evaluation_error")
        self.assertFalse(self.backend.calls)

    def test_untrusted_stale_mutated_and_disabled_facts_do_not_short_circuit(self):
        original = evidence_for(self.case)
        facts = json.loads(original.facts_json)
        variants = [EvidenceContext("0" * 64, original.facts_json)]
        for change in [
            {"source": "attacker"},
            {"complete": False},
            {"observed_at": (utc_now() - timedelta(seconds=400)).isoformat()},
        ]:
            bad = [{**facts[0], **change}]
            variants.append(EvidenceContext.from_verified(self.case["request"], bad))
        for context in variants:
            with self.subTest(context=context):
                self.assertEqual(self.evaluate(context)["decision"], "evaluation_error")
        self.config["metadata"]["enabled"] = False
        self.assertEqual(self.evaluate()["decision"], "evaluation_error")
        self.config["metadata"]["enabled"] = True
        self.config["metadata"]["sources"]["destination"]["enabled"] = False
        self.assertEqual(self.evaluate()["decision"], "evaluation_error")

    def test_fact_freshness_rechecked_after_other_policy_model_call(self):
        now = utc_now()
        clock = [now]
        self.backend.effect = lambda: clock.__setitem__(0, now + timedelta(seconds=400))
        self.config["policies"]["EVAL-DOC-001"] = {
            "enabled": True,
            "mode": "monitor",
            "strategy": "semantic",
        }
        with patch("humanwill_policies.evaluation.utc_now", side_effect=lambda: clock[0]):
            result = self.evaluate()
        software = next(p for p in result["policies"] if p["policy_id"] == "EVAL-SW-001")
        self.assertEqual(software["status"], "error")
        self.assertEqual(software["reasons"], ["stale_metadata"])

    def test_v2_and_explicit_opt_out_preserve_semantic_path(self):
        self.config["policies"]["EVAL-SW-001"]["predicate_short_circuit"] = False
        self.assertEqual(self.evaluate()["decision"], "allow")
        self.assertEqual(len(self.backend.calls), 1)
        self.config = yaml.safe_load((ROOT / "config.yaml").read_text())
        for key, binding in self.config["policies"].items():
            binding["enabled"] = key == "EVAL-SW-001"
        result = self.evaluate()
        self.assertEqual(result["format"], "humanwill.result/2")
        self.assertEqual(result["rubric"], "humanwill.choice/1")
        self.assertEqual(len(self.backend.calls), 2)

    def test_invalid_scopes_and_v2_new_fields_are_rejected(self):
        base = copy.deepcopy(self.config)
        for variant in ["missing_stage", "two_scopes", "wrong_strategy", "v2"]:
            self.config = copy.deepcopy(base)
            b = self.config["policies"]["EVAL-SW-001"]
            if variant == "missing_stage":
                b["scope_by_stage"].pop("prompt")
            if variant == "two_scopes":
                b["scope"] = "other"
            if variant == "wrong_strategy":
                b["strategy"] = "predicates"
            if variant == "v2":
                self.config["format"] = "humanwill.config/2"
            with self.assertRaises(PolicyError):
                load_configuration(self.bundle, self.config)
