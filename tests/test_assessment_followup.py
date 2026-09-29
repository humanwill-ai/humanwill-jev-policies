"""Runtime follow-up contracts: scripted replies only, never real API calls."""

import asyncio
import copy
import json
from datetime import timedelta
from unittest.mock import patch

import httpx
import test_evaluation
import test_service
from test_direct_policy import v5
from test_evaluation import ScriptedBackend, answer, event
from test_foundation import Workspace, write_collection, write_policy
from test_service import TOKEN, llm

from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.config import preview
from humanwill_policies.errors import PolicyError
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.hooks import assess
from humanwill_policies.runtime import EgressPermit, utc_now
from humanwill_policies.serialization import digest


def scope(choice="not_applicable", confidence=1):
    return answer(choice, confidence, scoped=True)


class SequenceBackend(ScriptedBackend):
    def __init__(self, responses, *, second_delay=0, second_error=None):
        super().__init__()
        self.responses = responses
        self.second_delay, self.second_error = second_delay, second_error

    async def evaluate(self, payload, **kwargs):
        index = len(self.calls)
        if index >= len(self.responses):
            raise AssertionError("Unexpected extra model call")
        self._answers = json.dumps(self.responses[index])
        self.delay = self.second_delay if index == len(self.responses) - 1 else 0
        self.error = self.second_error if index == len(self.responses) - 1 else None
        result = await super().evaluate(payload, **kwargs)
        result["usage"] = {"input_tokens": 20, "output_tokens": 10, "cost": 0.001}
        return result


class FollowupTests(Workspace):
    config = test_evaluation.EvaluationTests.config
    enforcing = test_evaluation.EvaluationTests.enforcing
    metadata_config = test_evaluation.EvaluationTests.metadata_config
    fact = test_evaluation.EvaluationTests.fact
    run_evaluation = test_evaluation.EvaluationTests.run_evaluation
    app = test_service.ServiceTests.app
    post = test_service.ServiceTests.post

    def configured(self, **extra):
        config = v5(self.metadata_config("scoped_predicates"))
        config["policy_assessment"] = "q05_q04"
        config["outcome_thresholds"] = dict(
            applicable=0.8, not_applicable=0.7, insufficient_evidence=0.8
        )
        config.update(extra)
        return config

    def test_recovers_agreement_with_exact_questions_preview_and_both_usage_records(self):
        config = self.configured()
        backend = SequenceBackend(
            [{"RULE": scope(confidence=0.5)}, {"RULE": scope(confidence=0.7)}]
        )
        result = self.run_evaluation(backend, config)
        self.assertEqual(result["decision"], "allow")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["enforcement"]["requested"], "none")
        trace = result["policy_assessment"]
        self.assertEqual(trace["accepted"], ["RULE"])
        self.assertEqual(trace["primary_answers"]["RULE"]["confidence"], 0.5)
        self.assertEqual(trace["secondary_answers"]["RULE"]["confidence"], 0.7)
        self.assertEqual(trace["batch_index"], 1)
        self.assertAlmostEqual(sum(b["cost_usd"] for b in result["evaluation"]["batches"]), 0.002)
        self.assertEqual(backend.calls[0]["state"], backend.calls[1]["state"])
        bundle = load_bundle(self.root)
        shown = preview(bundle, load_configuration(bundle, config))["policies"][0]
        self.assertEqual(
            backend.calls[0]["questions"]["RULE"], shown["evaluation_questions"]["prompt"]
        )
        self.assertEqual(
            backend.calls[1]["questions"]["RULE"], shown["followup_questions"]["prompt"]
        )
        from evals.step6.short_questions import transform

        self.assertEqual(transform(backend.calls[0], "q04"), backend.calls[1])

    def test_bad_secondary_never_replaces_primary(self):
        tied = scope(confidence=0.9)
        tied["probabilities"] = dict(applicable=0.5, not_applicable=0.5, insufficient_evidence=0)
        for secondary, reason in [
            (scope("applicable"), "conflicting_scope"),
            (scope("insufficient_evidence"), "still_indeterminate"),
            (scope(confidence=0.69), "low_confidence"),
            (tied, "low_confidence"),
        ]:
            backend = SequenceBackend([{"RULE": scope(confidence=0.5)}, {"RULE": secondary}])
            result = self.run_evaluation(backend, self.configured())
            self.assertEqual(result["decision"], "evaluation_error")
            self.assertEqual(result["policy_assessment"]["rejected"], {"RULE": reason})
            self.assertEqual(result["policies"][0]["evidence"]["confidence"], 0.5)

    def test_accepted_scope_does_not_replace_trusted_authorization(self):
        for facts, decision in [
            (None, "evaluation_error"),
            ([self.fact([])], "block"),
            ([self.fact()], "allow"),
        ]:
            backend = SequenceBackend(
                [{"RULE": scope("applicable", 0.5)}, {"RULE": scope("applicable", 0.8)}]
            )
            result = self.run_evaluation(backend, self.configured(), facts=facts)
            self.assertEqual(result["decision"], decision)
            self.assertEqual(result["policy_assessment"]["accepted"], ["RULE"])
        # Facts becoming stale during the extra call still fail before enforcement.
        now = utc_now()
        backend = SequenceBackend(
            [{"RULE": scope("applicable", 0.5)}, {"RULE": scope("applicable", 0.8)}]
        )
        with patch(
            "humanwill_policies.evaluation.utc_now", side_effect=[now, now + timedelta(seconds=301)]
        ):
            result = self.run_evaluation(
                backend, self.configured(), facts=[self.fact(observed_at=now.isoformat())]
            )
        self.assertEqual(result["decision"], "evaluation_error")
        self.assertEqual(result["enforcement"]["requested"], "block")

    def test_no_followup_for_settled_unknown_missing_malformed_or_disabled_profile(self):
        for first in [scope(), scope("insufficient_evidence", 0.3), scope("applicable")]:
            backend = SequenceBackend([{"RULE": first}])
            result = self.run_evaluation(backend, self.configured())
            self.assertEqual(len(backend.calls), 1)
            self.assertEqual(result["policy_assessment"]["status"], "not_needed")
        bad = scope(confidence=0.5)
        bad["probabilities"]["not_applicable"] = 0.99
        backend = SequenceBackend([{"RULE": bad}])
        result = self.run_evaluation(backend, self.configured())
        self.assertEqual(len(backend.calls), 1)
        self.assertEqual(result["policies"][0]["reasons"], ["malformed_response"])
        for profile in ("q05", "standard"):
            backend = SequenceBackend([{"RULE": scope(confidence=0.5)}])
            self.run_evaluation(backend, self.configured(policy_assessment=profile))
            self.assertEqual(len(backend.calls), 1)

    def test_batch_preserves_settled_answers_and_skips_when_any_primary_blocks(self):
        write_policy(self.root, "other.md", "OTHER")
        write_collection(self.root, ["rule.md", "other.md"])
        config = self.configured()
        config["policies"]["OTHER"] = copy.deepcopy(config["policies"]["RULE"])
        for settled in ("not_applicable", "applicable"):
            first = {"RULE": scope(confidence=0.5), "OTHER": scope(settled)}
            second = {
                "RULE": scope(),
                "OTHER": scope("applicable" if settled == "not_applicable" else "not_applicable"),
            }
            backend = SequenceBackend([first, second])
            result = self.run_evaluation(backend, config, facts=[self.fact([])])
            self.assertEqual(len(backend.calls), 2 if settled == "not_applicable" else 1)
            other = next(p for p in result["policies"] if p["policy_id"] == "OTHER")
            self.assertEqual(other["evidence"]["choice"], settled)
            if len(backend.calls) == 2:
                self.assertEqual(set(backend.calls[1]["questions"]), {"RULE", "OTHER"})

    def test_split_batches_total_call_and_byte_limits(self):
        write_policy(self.root, "other.md", "OTHER")
        write_collection(self.root, ["rule.md", "other.md"])
        config = self.configured(evaluation={"questions_per_batch": 1, "max_batches": 3})
        config["policies"]["OTHER"] = copy.deepcopy(config["policies"]["RULE"])
        backend = SequenceBackend(
            [{"OTHER": scope(confidence=0.5)}, {"RULE": scope(confidence=0.5)}, {"OTHER": scope()}]
        )
        result = self.run_evaluation(backend, config)
        self.assertEqual(len(backend.calls), 3)
        self.assertEqual(result["decision"], "evaluation_error")
        self.assertEqual(result["policy_assessment"]["rejected"], {"RULE": "call_limit"})
        config["evaluation"]["max_batches"] = 2
        backend = SequenceBackend(
            [{"OTHER": scope(confidence=0.5)}, {"RULE": scope(confidence=0.5)}]
        )
        result = self.run_evaluation(backend, config)
        self.assertEqual(len(backend.calls), 2)
        self.assertEqual(result["policy_assessment"]["error"], "batch_limit")

    def test_timeout_failure_malformed_and_fallback(self):
        bad = scope()
        bad["probabilities"]["not_applicable"] = 0.99
        for second, kwargs, code in [
            ({"RULE": bad}, {}, "malformed_response"),
            ({"RULE": scope()}, {"second_delay": 0.1}, "evaluation_timeout"),
            ({"RULE": scope()}, {"second_error": ValueError("PRIVATE TOKEN")}, "backend_error"),
        ]:
            for fallback in ("allow", "block"):
                config = self.configured(evaluation={"timeout_ms": 50})
                config["policies"]["RULE"]["on_error"] = fallback
                backend = SequenceBackend([{"RULE": scope(confidence=0.5)}, second], **kwargs)
                result = self.run_evaluation(backend, config)
                self.assertEqual(result["decision"], "evaluation_error")
                self.assertEqual(result["enforcement"]["requested"], fallback)
                self.assertEqual(result["policy_assessment"]["error"], code)
                self.assertNotIn("PRIVATE", json.dumps(result))
                self.assertEqual(len(backend.calls), 2)
                self.assertEqual(
                    result["evaluation"]["batches"][1]["cost_usd"],
                    0.001 if code == "malformed_response" else None,
                )

    def test_egress_cancellation_and_concurrency_cover_extra_call(self):
        backend = SequenceBackend(
            [{"RULE": scope(confidence=0.5)}, {"RULE": scope()}], second_delay=10
        )
        result = self.run_evaluation(backend, self.configured(), permit=False)
        self.assertFalse(backend.calls)
        self.assertEqual(result["decision"], "evaluation_error")

        async def exercise():
            bundle = load_bundle(self.root)
            config = self.configured(evaluation={"max_in_flight": 1})
            engine = Evaluator(bundle, load_configuration(bundle, config), backend)
            request = event()
            permit = EgressPermit(digest(request), bundle.sha256, backend.transport)
            task = asyncio.create_task(engine.evaluate(request, egress=permit))
            for _ in range(100):
                if len(backend.calls) == 2:
                    break
                await asyncio.sleep(0.001)
            self.assertEqual(len(backend.calls), 2)
            overloaded = await engine.evaluate(request, egress=permit)
            self.assertEqual(overloaded["policies"][0]["reasons"], ["evaluation_overloaded"])
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual(backend.cancelled, 1)
            self.assertFalse(engine._slots.locked())

        asyncio.run(exercise())

    def test_connector_paths_use_final_decision_and_cli_prompt_stays_assessment_only(self):
        for recovered in (True, False):
            for connector, path, body in [
                ("litellm", "/beta/litellm_basic_guardrail_api", llm()),
                (
                    "agentgateway",
                    "/request",
                    {"body": {"messages": [{"role": "user", "content": "test"}]}},
                ),
            ]:
                backend = SequenceBackend(
                    [
                        {"RULE": scope(confidence=0.5)},
                        {"RULE": scope(confidence=0.9 if recovered else 0.5)},
                    ]
                )
                output = self.post(
                    self.app(connector, config=self.configured(), backend=backend), path, body
                ).json()
                self.assertEqual(len(backend.calls), 2)
                if connector == "litellm":
                    self.assertEqual(output["action"], "NONE" if recovered else "BLOCKED")
                else:
                    self.assertEqual(
                        output["action"].get("status_code"), None if recovered else 403
                    )
            for runtime, name, body in [
                (
                    "copilot_local",
                    "UserPromptSubmit",
                    {"hook_event_name": "UserPromptSubmit", "prompt": "test"},
                ),
                (
                    "copilot_local",
                    "PreToolUse",
                    {"hook_event_name": "PreToolUse", "tool_name": "shell", "tool_input": {}},
                ),
                ("copilot_cli", "userPromptSubmitted", {"prompt": "test"}),
                ("copilot_cli", "preToolUse", {"toolName": "shell", "toolArgs": {}}),
            ]:
                backend = SequenceBackend(
                    [
                        {"RULE": scope(confidence=0.5)},
                        {"RULE": scope(confidence=0.9 if recovered else 0.5)},
                    ]
                )
                app = self.app(runtime, config=self.configured(), backend=backend)
                result = asyncio.run(
                    assess(
                        body,
                        runtime,
                        name,
                        "http://localhost",
                        TOKEN,
                        6000,
                        transport=httpx.ASGITransport(app),
                    )
                )
                self.assertEqual(
                    result["enforcement"]["requested"],
                    "none" if name == "userPromptSubmitted" or recovered else "block",
                )
                self.assertEqual(len(backend.calls), 2)

    def test_profile_schema_and_legacy_config_rejects_option(self):
        bundle = load_bundle(self.root)
        for config in [
            self.configured(policy_assessment="typo"),
            {**self.config(), "policy_assessment": "q05_q04"},
        ]:
            with self.assertRaises(PolicyError):
                load_configuration(bundle, config)

    def test_followup_byte_limit_and_content_only_rules(self):
        backend = SequenceBackend([{"RULE": scope(confidence=0.5)}, {"RULE": scope()}])
        self.run_evaluation(backend, self.configured())
        from humanwill_policies.serialization import canonical

        first_size = len(canonical(backend.calls[0]).encode())
        second_size = len(canonical(backend.calls[1]).encode())
        self.assertGreater(second_size, first_size)
        limited = SequenceBackend([{"RULE": scope(confidence=0.5)}])
        result = self.run_evaluation(
            limited, self.configured(evaluation={"max_batch_bytes": first_size})
        )
        self.assertEqual(len(limited.calls), 1)
        self.assertEqual(result["policy_assessment"]["error"], "batch_limit")
        # Content-only semantic rules work with metadata off; Q04 authorization wording
        # must never be applied to their compliant/violation vocabulary.
        config = v5(self.enforcing())
        config["policy_assessment"] = "q05_q04"
        semantic = SequenceBackend([{"RULE": answer(confidence=0.5)}])
        result = self.run_evaluation(semantic, config)
        self.assertEqual(result["decision"], "evaluation_error")
        self.assertEqual(len(semantic.calls), 1)
        self.assertEqual(
            set(semantic.calls[0]["questions"]["RULE"]["criteria"]),
            {"compliant", "violation", "insufficient_evidence"},
        )

    def test_historical_live_guard_is_not_rewritten_for_new_runtime(self):
        from evals.step6.q04_comparison import validate_experiment

        with self.assertRaisesRegex(ValueError, "Frozen"):
            validate_experiment()
