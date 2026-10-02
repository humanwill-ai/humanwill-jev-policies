"""Native MCP trust boundary and verdict binding; no external services."""

import asyncio
import copy
import json

import httpx
import test_service
from test_evaluation import ScriptedBackend, answer
from test_foundation import Workspace
from test_service import TOKEN

from humanwill_policies.connectors.mcp import assess, invocation
from humanwill_policies.errors import PolicyError
from humanwill_policies.serialization import canonical


def data():
    return {
        "mcp_tool_name": "write_file",
        "mcp_server_name": "company-tools",
        "mcp_arguments": {"path": "local", "options": {"n": 2, "flags": [True, None]}},
        "incoming_bearer_token": "NEVER_FORWARD",
        "metadata": {"headers": {"authorization": "NEVER_FORWARD"}},
        "user_api_key_team_id": "CLAIMED_TEAM",
    }


class MCPTests(Workspace):
    app = test_service.ServiceTests.app
    config = test_service.ServiceTests.config
    enforcing = test_service.ServiceTests.enforcing

    def test_structured_snapshot_excludes_credentials_and_claimed_identity(self):
        raw = data()
        request = invocation(raw)
        self.assertEqual(request["stage"], "tool_action")
        self.assertEqual(request["content"][0]["arguments"], raw["mcp_arguments"])
        self.assertNotIn("NEVER_FORWARD", canonical(request))
        self.assertNotIn("CLAIMED_TEAM", canonical(request))
        self.assertIn("company-tools", request["content"][1]["text"])
        raw["mcp_arguments"]["options"]["n"] = 999
        self.assertEqual(request["content"][0]["arguments"]["options"]["n"], 2)

    def test_unknown_or_mutated_payloads_fail_before_egress(self):
        for change in [
            {"mcp_tool_name": ""},
            {"mcp_server_name": None},
            {"mcp_arguments": "{}"},
            {"mcp_arguments": {"n": float("nan")}},
            {"mcp_arguments": {"huge": "x" * 262144}},
            {"modified_arguments": {"different": True}},
            {"extra_headers": {"route": "other"}},
        ]:
            with self.subTest(change=list(change)), self.assertRaises(PolicyError):
                invocation({**data(), **change})

    def test_service_decision_and_monitoring_are_distinct(self):
        for mode in ("enforce", "monitor"):
            config = self.enforcing()
            config["policies"]["RULE"]["mode"] = mode
            app = self.app(config=config, backend=ScriptedBackend({"RULE": answer("violation")}))
            result = asyncio.run(
                assess(
                    invocation(data()),
                    "http://localhost",
                    TOKEN,
                    1000,
                    transport=httpx.ASGITransport(app),
                )
            )
            self.assertEqual(result["decision"], "block")
            self.assertEqual(
                result["enforcement"]["requested"], "block" if mode == "enforce" else "none"
            )

    def test_verdict_binding_rejects_other_event_or_coverage(self):
        request = invocation(data())
        result = asyncio.run(
            assess(
                request, "http://localhost", TOKEN, 1000, transport=httpx.ASGITransport(self.app())
            )
        )
        for key, value in [
            ("request_id", "event-different"),
            ("request_sha256", "0" * 64),
            ("coverage", {"inspected": [], "omitted": [], "complete": True}),
            ("simulated", True),
        ]:
            changed = copy.deepcopy(result)
            changed[key] = value
            if key == "simulated":
                changed["enforcement"]["requested"] = "block"
            with self.subTest(key=key), self.assertRaises(PolicyError):
                asyncio.run(
                    assess(
                        request,
                        "http://localhost",
                        TOKEN,
                        1000,
                        transport=httpx.MockTransport(
                            lambda _, changed=changed: httpx.Response(200, json=changed)
                        ),
                    )
                )

    def test_network_protocol_failures_are_not_success(self):
        request = invocation(data())
        responses = [
            httpx.Response(503),
            httpx.Response(302, headers={"location": "https://other.test"}),
            httpx.Response(200, text="{"),
            httpx.Response(200, text="x" * 262145),
            httpx.Response(200, json={"decision": "allow"}),
        ]
        for response in responses:
            with self.assertRaises(PolicyError):
                asyncio.run(
                    assess(
                        request,
                        "http://localhost",
                        TOKEN,
                        1000,
                        transport=httpx.MockTransport(lambda _, response=response: response),
                    )
                )

    def test_client_deadline_no_retry_and_no_redirect(self):
        calls = []

        async def delayed(request):
            calls.append(json.loads(request.content))
            await asyncio.sleep(0.1)
            return httpx.Response(200)

        with self.assertRaises(TimeoutError):
            asyncio.run(
                assess(
                    invocation(data()),
                    "http://localhost",
                    TOKEN,
                    10,
                    transport=httpx.MockTransport(delayed),
                )
            )
        self.assertEqual(len(calls), 1)
