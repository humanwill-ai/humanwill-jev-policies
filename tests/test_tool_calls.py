"""Structured proposals: stage boundaries, strict parsing and atomic host decisions."""

import copy
import json
import os
from unittest.mock import patch

import httpx
import test_service
from test_evaluation import ScriptedBackend, answer
from test_foundation import Workspace, write_collection, write_policy
from test_service import settings

from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.connectors.chat import (
    MAX_TOOL_CALLS,
    litellm_events,
    tool_calls,
    validate_request,
    validate_response,
)
from humanwill_policies.errors import PolicyError
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.runtime import EvidenceContext, utc_now
from humanwill_policies.service import create_app


def call(name="upload", arguments=None, id="call-1"):
    return {
        "id": id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments or {"destination": "internal"}),
        },
    }


def proposal(calls=None, texts=None):
    return {
        "litellm_version": "1.102.1",
        "input_type": "response",
        "texts": texts or [],
        "tool_calls": calls if calls is not None else [call()],
    }


def deployment(**extra):
    value = settings("litellm")
    value["principals"]["test"].update(
        inspect_tool_calls=True, stages=["model_request", "response", "tool_action"], **extra
    )
    return value


class ParsingTests(Workspace):
    def test_proposals_preserve_nested_arguments_and_have_separate_actions(self):
        args = {"array": [1, False, None, {"value": "x"}], "text": "a\nb"}
        batch = litellm_events(proposal([call(arguments=args), call(id="call-2")], ["hello"]))
        self.assertEqual(
            [row["stage"] for row in batch], ["response", "tool_action", "tool_action"]
        )
        self.assertEqual(batch[1]["content"][0]["arguments"], args)
        self.assertIn("New tool-call proposals", batch[0]["content"][1]["text"])

    def test_history_and_definitions_never_become_new_actions(self):
        rows = [
            {"role": "user", "content": "continue"},
            {"role": "assistant", "content": None, "tool_calls": [call()]},
            {"role": "tool", "content": "done", "tool_call_id": "call-1"},
        ]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "upload",
                    "description": "available",
                    "parameters": {"type": "object"},
                },
            }
        ]
        payload = {
            "litellm_version": "1.102.1",
            "input_type": "request",
            "texts": ["continue", "done"],
            "tools": tools,
            "structured_messages": rows,
            "tool_calls": [call()],
        }
        batch = litellm_events(payload)
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch[0]["stage"], "model_request")
        self.assertIn('"tool_call_id":"call-1"', batch[0]["content"][2]["text"])
        self.assertIn("Available tool definitions", batch[0]["content"][3]["text"])
        for key, value in [("texts", ["continue"]), ("tool_calls", [])]:
            with self.assertRaises(PolicyError):
                litellm_events(payload | {key: value})

    def test_reject_ambiguous_partial_or_nonfunction_calls(self):
        for args in ['{"x":1,"x":2}', '{"x":NaN}', "[]", "null", '{"x":', '"text"']:
            item = call()
            item["function"]["arguments"] = args
            with self.subTest(args=args), self.assertRaises(PolicyError):
                tool_calls([item])
        for calls in [
            [call(), call()],
            [call() | {"type": "custom"}],
            [call() | {"index": 0}],
            [],
            [call() | {"id": ""}],
            [call(id=f"c-{i}") for i in range(MAX_TOOL_CALLS + 1)],
        ]:
            with self.subTest(calls=calls), self.assertRaises(PolicyError):
                tool_calls(calls)

    def test_reject_streaming_multimodal_legacy_and_incomplete_response(self):
        request = {"messages": [{"role": "user", "content": "hello"}]}
        for fields in [
            {"stream": True},
            {"functions": []},
            {"modalities": ["text"]},
            {"messages": [{"role": "user", "content": []}]},
            {"tools": [{"type": "web_search"}]},
        ]:
            with self.assertRaises(PolicyError):
                validate_request(request | fields)
        response = {
            "choices": [
                {
                    "message": {"role": "assistant", "content": None, "tool_calls": [call()]},
                    "finish_reason": "tool_calls",
                }
            ]
        }
        self.assertEqual(validate_response(response), ([], [call()]))
        for reason in ["length", "stop", None]:
            bad = copy.deepcopy(response)
            bad["choices"][0]["finish_reason"] = reason
            with self.assertRaises(PolicyError):
                validate_response(bad)


class ToolServiceTests(Workspace):
    post = test_service.ServiceTests.post

    def make_app(
        self,
        *,
        mode="enforce",
        on_error="block",
        backend=None,
        resolver=None,
        metadata=False,
        upstream_transport=None,
        service_timeout=None,
        **deployment_extra,
    ):
        write_collection(self.root, ["rule.md"])
        write_policy(self.root, stages=["tool_action"])
        config = test_service.ServiceTests.enforcing(self, on_error=on_error)
        if service_timeout:
            config["evaluation"] = {"timeout_ms": 100}
        config["policies"]["RULE"]["mode"] = mode
        if metadata:
            config["metadata"]["enabled"] = True
            config["metadata"]["sources"] = {
                "destination": {
                    "enabled": True,
                    "source": "test-authority",
                }
            }
            config["policies"]["RULE"].update(
                strategy="predicates",
                requires_metadata=["destination.approved"],
                predicates=[{"field": "destination.approved", "op": "equals", "value": True}],
            )
        bundle = load_bundle(self.root)
        engine = Evaluator(bundle, load_configuration(bundle, config), backend or ScriptedBackend())
        with patch.dict(
            os.environ, {"SERVICE_TEST_TOKEN": "synthetic-connector-token-0000000000000000"}
        ):
            service_settings = deployment(**deployment_extra)
            if service_timeout:
                service_settings["request_timeout_ms"] = service_timeout
            return create_app(
                engine,
                service_settings,
                evidence_resolver=resolver,
                upstream_transport=upstream_transport,
            )

    config = test_service.ServiceTests.config

    def test_action_only_policy_blocks_even_when_response_stage_has_no_rules(self):
        backend = ScriptedBackend({"RULE": answer("violation")})
        app = self.make_app(backend=backend)
        result = self.post(app, "/beta/litellm_basic_guardrail_api", proposal())
        self.assertEqual(result.json()["action"], "BLOCKED")
        self.assertEqual(len(backend.calls), 1)

    def test_all_calls_must_pass_and_arguments_never_appear_in_audit(self):
        class SecondDenies(ScriptedBackend):
            async def evaluate(self, payload, **kw):
                self._answers = json.dumps(
                    {"RULE": answer("violation" if self.calls else "compliant")}
                )
                return await super().evaluate(payload, **kw)

        backend = SecondDenies()
        app = self.make_app(backend=backend)
        with self.assertLogs("humanwill.audit", level="INFO") as logs:
            result = self.post(
                app,
                "/beta/litellm_basic_guardrail_api",
                proposal([call(), call(id="c2", arguments={"secret": "PRIVATE"})]),
            )
        self.assertEqual(result.json()["action"], "BLOCKED")
        self.assertEqual(len(backend.calls), 2)
        self.assertNotIn("PRIVATE", str(logs.output))

    def test_monitor_and_error_fallback_are_explicit(self):
        for mode, fallback, choice, expected in [
            ("monitor", "block", "violation", "NONE"),
            ("enforce", "block", "insufficient_evidence", "BLOCKED"),
            ("enforce", "allow", "insufficient_evidence", "NONE"),
            ("enforce", "allow", "violation", "BLOCKED"),
        ]:
            with self.subTest(mode=mode, fallback=fallback, choice=choice):
                app = self.make_app(
                    mode=mode, on_error=fallback, backend=ScriptedBackend({"RULE": answer(choice)})
                )
                self.assertEqual(
                    self.post(app, "/beta/litellm_basic_guardrail_api", proposal()).json()[
                        "action"
                    ],
                    expected,
                )

    def test_malformed_later_call_never_reaches_evaluator(self):
        backend = ScriptedBackend()
        app = self.make_app(backend=backend)
        bad = call(id="c2")
        bad["function"]["arguments"] = "{"
        self.assertEqual(
            self.post(app, "/beta/litellm_basic_guardrail_api", proposal([call(), bad])).json()[
                "action"
            ],
            "BLOCKED",
        )
        self.assertFalse(backend.calls)

    def test_multiple_actions_share_one_service_deadline(self):
        backend = ScriptedBackend(delay=0.06)
        app = self.make_app(backend=backend, service_timeout=150)
        response = self.post(
            app,
            "/beta/litellm_basic_guardrail_api",
            proposal([call(id="c1"), call(id="c2"), call(id="c3"), call(id="c4")]),
        )
        self.assertEqual(response.json()["action"], "BLOCKED")
        self.assertLess(len(backend.calls), 4)
        self.assertGreater(backend.cancelled, 0)

    def test_profile_needs_explicit_action_stage_and_cannot_use_old_webhook(self):
        for connector, stages in [
            ("litellm", ["response"]),
            ("agentgateway", ["model_request", "response", "tool_action"]),
        ]:
            with self.assertRaises(PolicyError):
                value = deployment()
                value["principals"]["test"].update(connector=connector, stages=stages)
                # Validate independently through a minimal evaluator stub with the same config.
                from types import SimpleNamespace

                with patch.dict(os.environ, {"SERVICE_TEST_TOKEN": "x" * 32}):
                    create_app(SimpleNamespace(limits=SimpleNamespace(timeout_ms=5000)), value)

    def test_missing_metadata_blocks_and_trusted_facts_are_resolved_per_action(self):
        backend = ScriptedBackend()
        app = self.make_app(metadata=True, backend=backend)
        self.assertEqual(
            self.post(app, "/beta/litellm_basic_guardrail_api", proposal()).json()["action"],
            "BLOCKED",
        )
        observed = []

        async def resolve(principal, request):
            facts = []
            if request["stage"] == "tool_action":
                destination = request["content"][0]["arguments"]["destination"]
                observed.append(destination)
                facts = [
                    {
                        "field": "destination.approved",
                        "value": destination == "internal",
                        "source": "test-authority",
                        "complete": True,
                        "subject_ref": destination,
                        "observed_at": utc_now().isoformat(),
                    }
                ]
            return EvidenceContext.from_verified(request, facts)

        app = self.make_app(metadata=True, backend=backend, resolver=resolve)
        result = self.post(
            app,
            "/beta/litellm_basic_guardrail_api",
            proposal([call(), call(id="c2", arguments={"destination": "external"})]),
        )
        self.assertEqual(result.json()["action"], "BLOCKED")
        self.assertEqual(observed, ["internal", "external"])
        self.assertFalse(backend.calls)

    def test_relay_withholds_proposals_and_uses_fixed_route_and_credentials(self):
        received = []

        def upstream(request):
            received.append(request)
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [call()],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                },
            )

        app = self.make_app(
            connector="agentgateway",
            model_backend={"url": "http://127.0.0.1:9999/v1/chat/completions", "model": "fixed"},
            backend=ScriptedBackend({"RULE": answer("violation")}),
            upstream_transport=httpx.MockTransport(upstream),
        )
        body = {"model": "fixed", "messages": [{"role": "user", "content": "test"}]}
        result = self.post(app, "/v1/chat/completions", body)
        self.assertEqual(result.status_code, 403)
        self.assertNotIn("tool_calls", result.text)
        self.assertEqual(len(received), 1)
        self.assertNotIn("authorization", received[0].headers)
        for fields in [{"model": "other"}, {"api_base": "https://external.test"}, {"stream": True}]:
            self.assertNotEqual(
                self.post(app, "/v1/chat/completions", body | fields).status_code, 200
            )
        self.assertEqual(len(received), 1)
        self.assertEqual(
            self.post(app, "/response", {"body": {"choices": []}}).json()["action"]["status_code"],
            403,
        )

    def test_relay_does_not_follow_redirect_or_release_invalid_upstream(self):
        for upstream in [
            httpx.Response(302, headers={"location": "https://elsewhere.test"}),
            httpx.Response(200, text="event: x", headers={"content-type": "text/event-stream"}),
            httpx.Response(200, json={"choices": []}),
            httpx.Response(
                200, content=b"x" * 262145, headers={"content-type": "application/json"}
            ),
        ]:
            received = []

            def forward(request, received=received, upstream=upstream):
                received.append(request)
                return upstream

            app = self.make_app(
                connector="agentgateway",
                model_backend={
                    "url": "http://127.0.0.1:9999/v1/chat/completions",
                    "model": "fixed",
                },
                upstream_transport=httpx.MockTransport(forward),
            )
            response = self.post(
                app,
                "/v1/chat/completions",
                {"model": "fixed", "messages": [{"role": "user", "content": "test"}]},
            )
            self.assertEqual(response.status_code, 502)
            self.assertEqual(len(received), 1)
