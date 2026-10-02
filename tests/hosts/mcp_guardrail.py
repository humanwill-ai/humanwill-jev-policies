"""Callback checks inside the pinned LiteLLM environment; no remote calls."""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from litellm.types.guardrails import GuardrailEventHooks

from humanwill_policies.connectors.litellm_mcp import HumanWillMCPGuardrail


class GuardrailTests(unittest.TestCase):
    def create(self, **kwargs):
        with patch.dict(os.environ, {"HUMANWILL_MCP_TOKEN": "synthetic-mcp-test-token-0000000000"}):
            return HumanWillMCPGuardrail(service_url="http://localhost", **kwargs)

    def data(self):
        return {"mcp_tool_name": "write", "mcp_arguments": {"n": 1}, "mcp_server_name": "fixture"}

    def test_mandatory_pre_execution_only(self):
        guard = self.create()
        for data in (
            {},
            {
                "metadata": {
                    "disable_global_guardrails": True,
                    "opted_out_global_guardrails": ["humanwill-mcp"],
                }
            },
        ):
            self.assertTrue(guard.should_run_guardrail(data, GuardrailEventHooks.pre_mcp_call))
            self.assertFalse(guard.should_run_guardrail(data, GuardrailEventHooks.during_mcp_call))
            self.assertFalse(guard.should_run_guardrail(data, GuardrailEventHooks.post_call))

    def test_unsafe_options_rejected(self):
        with self.assertRaises(RuntimeError):
            HumanWillMCPGuardrail()
        for kw in (
            {"default_on": False},
            {"event_hook": "during_mcp_call"},
            {"run_in_parallel": True},
            {"timeout_ms": 0},
            {"mask_request_content": True},
        ):
            with self.assertRaises(RuntimeError):
                self.create(**kw)

    def test_block_outage_timeout_and_allow(self):
        guard = self.create()
        for response in ({"enforcement": {"requested": "block"}}, TimeoutError(), ValueError()):
            mock = (
                AsyncMock(side_effect=response)
                if isinstance(response, Exception)
                else AsyncMock(return_value=response)
            )
            with (
                patch("humanwill_policies.connectors.litellm_mcp.assess", mock),
                self.assertRaises(HTTPException),
            ):
                asyncio.run(guard.async_pre_call_hook(None, None, self.data(), "call_mcp_tool"))
            self.assertEqual(mock.await_count, 1)
        raw = self.data()
        with patch(
            "humanwill_policies.connectors.litellm_mcp.assess",
            AsyncMock(return_value={"enforcement": {"requested": "none"}}),
        ):
            self.assertIs(
                asyncio.run(guard.async_pre_call_hook(None, None, raw, "call_mcp_tool")), raw
            )

    def test_argument_mutation_while_waiting_denied(self):
        raw = self.data()

        async def changed(*args):
            raw["mcp_arguments"]["n"] = 2
            return {"enforcement": {"requested": "none"}}

        with (
            patch("humanwill_policies.connectors.litellm_mcp.assess", changed),
            self.assertRaises(HTTPException),
        ):
            asyncio.run(self.create().async_pre_call_hook(None, None, raw, "call_mcp_tool"))


if __name__ == "__main__":
    unittest.main()
