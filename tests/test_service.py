"""Service trust boundaries and distinct hook wire contracts; no external calls."""

import asyncio
import copy
import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import test_evaluation
from test_evaluation import ScriptedBackend, answer, event
from test_foundation import Workspace, write_policy

from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.connectors import events
from humanwill_policies.errors import PolicyError
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.hooks import assess, run
from humanwill_policies.runtime import EvidenceContext
from humanwill_policies.service import create_app

TOKEN = "synthetic-connector-token-0000000000000000"


def settings(connector="native", **extra):
    return {
        "format": "humanwill.service/1",
        "allow_external_evaluation": True,
        "principals": {
            "test": {
                "token_env": "SERVICE_TEST_TOKEN",
                "connector": connector,
                "stages": list(
                    {
                        "native": ["prompt", "tool_action", "model_request", "response"],
                        "litellm": ["model_request", "response"],
                        "agentgateway": ["model_request", "response"],
                        "copilot_local": ["prompt", "tool_action"],
                        "copilot_cli": ["prompt", "tool_action"],
                    }[connector]
                ),
                "on_protocol_error": "block",
            }
        },
        **extra,
    }


def llm(text="synthetic", stage="request"):
    return {"texts": [text], "input_type": stage, "litellm_version": "1.102.1"}


class ServiceTests(Workspace):
    config = test_evaluation.EvaluationTests.config
    enforcing = test_evaluation.EvaluationTests.enforcing
    metadata_config = test_evaluation.EvaluationTests.metadata_config
    fact = test_evaluation.EvaluationTests.fact

    def app(self, connector="native", *, config=None, backend=None, deployment=None, resolver=None):
        write_policy(self.root, stages=["prompt", "tool_action", "model_request", "response"])
        bundle = load_bundle(self.root)
        engine = Evaluator(
            bundle,
            load_configuration(bundle, config or self.enforcing()),
            backend or ScriptedBackend(),
        )
        with patch.dict(os.environ, {"SERVICE_TEST_TOKEN": TOKEN}):
            return create_app(engine, deployment or settings(connector), evidence_resolver=resolver)

    def post(self, app, path, body, token=TOKEN, **kw):
        async def call():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://test"
            ) as c:
                return await c.post(
                    path,
                    json=body,
                    headers={"Authorization": "Bearer " + token, "x-humanwill-text-profile": "v1"},
                    **kw,
                )

        return asyncio.run(call())

    def test_auth_connector_and_stage_are_not_request_controls(self):
        backend = ScriptedBackend()
        app = self.app("litellm", backend=backend)
        self.assertEqual(
            self.post(app, "/beta/litellm_basic_guardrail_api", llm(), "bad").status_code, 401
        )
        self.assertEqual(self.post(app, "/v1/evaluate", event()).status_code, 403)
        body = llm()
        body.update(policies={}, threshold=0, metadata={"groups": ["finance"]})
        self.assertEqual(
            self.post(app, "/beta/litellm_basic_guardrail_api", body).json(), {"action": "NONE"}
        )
        self.assertEqual(set(backend.calls[0]["questions"]), {"RULE"})
        self.assertNotIn("finance", json.dumps(backend.calls))
        deployment = settings()
        deployment["principals"]["test"]["stages"] = ["response"]
        self.assertEqual(
            self.post(self.app(deployment=deployment), "/v1/evaluate", event()).status_code, 403
        )

    def test_gateway_decisions_monitor_errors_and_both_stages(self):
        for connector, path, body, deny, allow in [
            (
                "litellm",
                "/beta/litellm_basic_guardrail_api",
                llm(),
                {"action": "BLOCKED", "blocked_reason": "HumanWill policy check denied"},
                {"action": "NONE"},
            ),
            (
                "litellm",
                "/beta/litellm_basic_guardrail_api",
                llm(stage="response"),
                {"action": "BLOCKED", "blocked_reason": "HumanWill policy check denied"},
                {"action": "NONE"},
            ),
            (
                "agentgateway",
                "/request",
                {"body": {"messages": [{"role": "user", "content": "text"}]}},
                {"action": {"body": "HumanWill policy check denied", "status_code": 403}},
                {"action": {}},
            ),
            (
                "agentgateway",
                "/response",
                {
                    "body": {
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": "text"},
                                "finish_reason": "stop",
                            }
                        ]
                    }
                },
                {"action": {"body": "HumanWill policy check denied", "status_code": 403}},
                {"action": {}},
            ),
        ]:
            for choice, config, expected in [
                ("compliant", self.enforcing(), allow),
                ("violation", self.enforcing(), deny),
                ("violation", self.config(), allow),
                ("insufficient_evidence", self.enforcing(), deny),
                ("insufficient_evidence", self.enforcing(on_error="allow"), allow),
            ]:
                with self.subTest(connector=connector, path=path, choice=choice, config=config):
                    app = self.app(
                        connector, config=config, backend=ScriptedBackend({"RULE": answer(choice)})
                    )
                    self.assertEqual(self.post(app, path, body).json(), expected)

    def test_unsupported_never_calls_evaluator_and_monitor_is_explicit(self):
        backend = ScriptedBackend()
        app = self.app("litellm", backend=backend)
        for body in [
            llm() | {"images": ["private"]},
            llm() | {"litellm_version": "future"},
            llm() | {"tools": [{"type": "function"}]},
            llm() | {"texts": []},
        ]:
            self.assertEqual(
                self.post(app, "/beta/litellm_basic_guardrail_api", body).json()["action"],
                "BLOCKED",
            )
        self.assertFalse(backend.calls)
        deployment = settings("litellm")
        deployment["principals"]["test"]["on_protocol_error"] = "allow_monitor"
        with self.assertRaises(PolicyError):
            self.app("litellm", deployment=deployment)
        app = self.app("litellm", deployment=deployment, config=self.config())
        with self.assertLogs("humanwill.audit") as logs:
            self.assertEqual(
                self.post(app, "/beta/litellm_basic_guardrail_api", {}).json(), {"action": "NONE"}
            )
        self.assertIn("unsupported_payload", str(logs.output))

    def test_limits_compression_duplicate_keys_slow_body_and_overload(self):
        async def scenario():
            config = self.enforcing()
            config["evaluation"] = {"timeout_ms": 50}
            app = self.app(
                "litellm",
                config=config,
                deployment=settings("litellm", request_timeout_ms=100, max_in_flight=1),
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app),
                base_url="http://test",
                headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"},
            ) as c:
                for body, headers in [
                    (b'{"texts":[],"texts":[]}', {}),
                    (b"x" * 262145, {}),
                    (b"x", {"Content-Encoding": "gzip"}),
                ]:
                    r = await c.post(
                        "/beta/litellm_basic_guardrail_api", content=body, headers=headers
                    )
                    self.assertEqual(r.json()["action"], "BLOCKED")

                async def slow():
                    yield b"{"
                    await asyncio.sleep(1)
                    yield b"}"

                a = asyncio.create_task(c.post("/beta/litellm_basic_guardrail_api", content=slow()))
                await asyncio.sleep(0.01)
                b = await c.post("/beta/litellm_basic_guardrail_api", json=llm())
                self.assertEqual(b.json()["action"], "BLOCKED")
                self.assertEqual((await a).json()["action"], "BLOCKED")

        asyncio.run(scenario())

    def test_external_opt_in_and_private_logging(self):
        backend = ScriptedBackend()
        app = self.app(backend=backend, deployment=settings(allow_external_evaluation=False))
        with self.assertLogs("humanwill.audit") as logs:
            result = self.post(app, "/v1/evaluate", event()).json()
        self.assertEqual(result["errors"][0]["code"], "egress_not_authorized")
        self.assertFalse(backend.calls)
        self.assertNotIn("I claim", str(logs.output))
        self.assertNotIn(TOKEN, str(logs.output))
        self.assertEqual(result["enforcement"]["actual"], "unconfirmed")

    def test_metadata_resolver_off_missing_verified_and_spoofed(self):
        calls = []

        async def resolver(principal, request):
            calls.append(principal)
            return EvidenceContext.from_verified(request, [self.fact()])

        self.post(self.app(resolver=resolver), "/v1/evaluate", event())
        self.assertFalse(calls)
        request = event()
        request["metadata"] = [{k: v for k, v in self.fact().items() if k != "complete"}]
        app = self.app(config=self.metadata_config())
        self.assertEqual(
            self.post(app, "/v1/evaluate", request).json()["decision"], "evaluation_error"
        )
        app = self.app(config=self.metadata_config(), resolver=resolver)
        self.assertEqual(self.post(app, "/v1/evaluate", request).json()["decision"], "allow")
        self.assertEqual(calls, ["test"])
        self.assertEqual(self.post(app, "/v1/evaluate", request, "bad").status_code, 401)

    def test_hook_wire_profiles_and_response_binding(self):
        for runtime, name, body in [
            (
                "copilot_local",
                "UserPromptSubmit",
                {"hook_event_name": "UserPromptSubmit", "prompt": "hello"},
            ),
            (
                "copilot_local",
                "PreToolUse",
                {
                    "hook_event_name": "PreToolUse",
                    "tool_name": "run_in_terminal",
                    "tool_input": {"command": "echo test"},
                },
            ),
            ("copilot_cli", "userPromptSubmitted", {"prompt": "hello"}),
            (
                "copilot_cli",
                "preToolUse",
                {"toolName": "bash", "toolArgs": '{"command":"echo test"}'},
            ),
        ]:
            app = self.app(runtime, backend=ScriptedBackend({"RULE": answer("violation")}))
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
            expected = "none" if name == "userPromptSubmitted" else "block"
            self.assertEqual(result["enforcement"]["requested"], expected)
            result["request_sha256"] = "0" * 64
            with self.assertRaises(PolicyError):
                asyncio.run(
                    assess(
                        body,
                        runtime,
                        name,
                        "http://localhost",
                        TOKEN,
                        6000,
                        transport=httpx.MockTransport(
                            lambda _, result=result: httpx.Response(200, json=result)
                        ),
                    )
                )

    def test_hook_failures_never_echo_content_and_preserve_default_permissions(self):
        for runtime, name in [
            ("copilot_local", "UserPromptSubmit"),
            ("copilot_local", "PreToolUse"),
            ("copilot_cli", "preToolUse"),
            ("copilot_cli", "userPromptSubmitted"),
        ]:
            args = SimpleNamespace(runtime=runtime, event=name, on_error="block")
            output, err = io.StringIO(), io.StringIO()
            with (
                patch("sys.stdin", SimpleNamespace(buffer=io.BytesIO(b"{SECRET"))),
                redirect_stdout(output),
                redirect_stderr(err),
            ):
                self.assertEqual(run(args), 0)
            self.assertNotIn("SECRET", err.getvalue() + output.getvalue())
            self.assertEqual(json.loads(output.getvalue()), events.hook_output(runtime, name, True))
            self.assertEqual(events.hook_output(runtime, name, False), {})

    def test_cli_hook_subprocess_error_has_host_json_on_stdout(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "humanwill_policies",
                "hook",
                "--runtime",
                "copilot_cli",
                "--event",
                "preToolUse",
            ],
            input="{}",
            text=True,
            capture_output=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["permissionDecision"], "deny")

    def test_startup_rejects_missing_duplicate_tokens_and_unsafe_deadline(self):
        for deployment in [settings(request_timeout_ms=5000), settings() | {"extra": "invalid"}]:
            with self.assertRaises(PolicyError):
                self.app(deployment=deployment)
        deployment = settings()
        deployment["principals"]["duplicate"] = copy.deepcopy(deployment["principals"]["test"])
        with self.assertRaises(PolicyError):
            self.app(deployment=deployment)
