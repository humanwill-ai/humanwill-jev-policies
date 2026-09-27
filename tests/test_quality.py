"""Quality-harness accounting and fixture wiring; no live provider calls."""

import asyncio
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
import yaml

from evals.step6.backends import ChatBackend, KeywordBackend, Ledger, MeteredBackend, choice_answer
from evals.step6.metrics import rate, summarize
from evals.step6.run import ROOT, evidence_for, load_cases
from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.errors import PolicyError
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import MockBackend


class QualityTests(unittest.TestCase):
    def test_gold_scope_wiring_is_not_a_quality_measurement(self):
        bundle = load_bundle(ROOT / "policies")
        base = yaml.safe_load((ROOT / "config.yaml").read_text())
        cases = load_cases(ROOT / "development.json")
        self.assertEqual(len(cases), 60)
        for case in cases:
            config = copy.deepcopy(base)
            for key, binding in config["policies"].items():
                binding["enabled"] = key == case["policy_id"]
            choice = case["expected_scope"] or "insufficient_evidence"
            backend = MockBackend(
                {
                    case["policy_id"]: choice_answer(
                        choice, ["applicable", "not_applicable", "insufficient_evidence"]
                    )
                }
            )
            engine = Evaluator(bundle, load_configuration(bundle, config), backend)
            result = asyncio.run(engine.evaluate(case["request"], evidence=evidence_for(case)))
            self.assertEqual(result["decision"], case["expected"], case["id"])
            self.assertEqual(result["enforcement"]["requested"], "none")

    def test_reservations_survive_errors_and_stop_further_spending(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = Ledger(Path(temp) / "budget.json")
            index = ledger.reserve("test")
            with self.assertRaises(PolicyError):
                Ledger(ledger.path).reserve("test")
            with self.assertRaises(PolicyError):
                ledger.settle(index, None)
            ledger.settle(index, 0.001)
            second = ledger.reserve("test")
            with self.assertRaises(PolicyError):
                ledger.settle(second, 4.999)
            with self.assertRaises(PolicyError):
                ledger.reserve("test")

    def test_metering_failure_cancels_future_calls(self):
        class Failing(KeywordBackend):
            async def evaluate(self, *args, **kwargs):
                raise RuntimeError("synthetic")

        with tempfile.TemporaryDirectory() as temp:
            backend = MeteredBackend(Failing(), Ledger(Path(temp) / "budget.json"))
            with self.assertRaises(RuntimeError):
                asyncio.run(backend.evaluate({}))
            self.assertTrue(backend.fatal)
            with self.assertRaises(PolicyError):
                asyncio.run(backend.evaluate({}))
            self.assertEqual(len(backend.ledger.data["calls"]), 1)

    def test_metrics_keep_error_blocks_and_unknown_cost(self):
        rows = []
        for expected, observed in [
            ("allow", "evaluation_error"),
            ("allow", "block"),
            ("block", "allow"),
            ("block", "evaluation_error"),
            ("evaluation_error", "allow"),
        ]:
            rows.append(
                {
                    "expected": expected,
                    "expected_scope": None,
                    "family": str(len(rows)),
                    "result": {
                        "decision": observed,
                        "duration_ms": 10,
                        "evaluation": {"batches": [{"cost_usd": None, "returned_model": None}]},
                    },
                }
            )
        report = summarize(rows)
        self.assertEqual(report["false_blocks_if_fail_closed"]["rate"], 1)
        self.assertEqual(report["semantic_false_violations"]["rate"], 0.5)
        self.assertEqual(report["missed_violations_if_fail_closed"]["rate"], 0.5)
        self.assertEqual(report["specified_case_errors"]["rate"], 0.5)
        self.assertEqual(report["unknown_incorrectly_allowed"], 1)
        self.assertIsNone(report["api_cost_per_1000_cases"])
        self.assertIsNone(rate(0, 0)["rate"])
        self.assertGreater(rate(0, 8)["wilson95"][1], 0.05)
        self.assertLess(rate(0, 100)["wilson95"][1], 0.05)

    def test_client_facts_never_become_verified_evidence(self):
        case = copy.deepcopy(load_cases(ROOT / "development.json")[-1])
        facts = json.loads(evidence_for(case).facts_json)
        self.assertNotIn("documents.classification", [f["field"] for f in facts])
        case["trusted_facts"] = {"authorization.destructive_permitted": True}
        self.assertEqual(json.loads(evidence_for(case).facts_json), [])

    def test_chat_receives_only_question_and_state_and_preserves_malformed_cost(self):
        seen = []

        def handler(request):
            seen.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "model": ChatBackend.model,
                    "choices": [{"message": {"content": "not json"}}],
                    "usage": {"cost": 0.001, "prompt_tokens": 10, "completion_tokens": 2},
                },
            )

        backend = ChatBackend(httpx.MockTransport(handler))
        payload = {
            "state": {"content": []},
            "questions": {
                "RULE": {
                    "instructions": {"rule": "test"},
                    "criteria": {
                        "applicable": "yes",
                        "not_applicable": "no",
                        "insufficient_evidence": "unknown",
                    },
                }
            },
        }
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "synthetic"}):
            response = asyncio.run(backend.evaluate(payload, timeout=1, max_bytes=10000))
        self.assertEqual(response["usage"]["cost"], 0.001)
        self.assertEqual(response["answers"], {"RULE": {}})
        self.assertFalse(seen[0]["provider"]["allow_fallbacks"])
        self.assertEqual(json.loads(seen[0]["messages"][1]["content"]), payload["state"])
        self.assertNotIn("rationale", json.dumps(seen))
