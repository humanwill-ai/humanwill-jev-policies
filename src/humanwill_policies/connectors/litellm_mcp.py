"""Pinned LiteLLM MCP pre-execution guardrail. Imported only inside LiteLLM."""

import os
from importlib.metadata import version

from fastapi import HTTPException
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks

from ..hooks import check_url
from .mcp import assess, check_token, invocation


class HumanWillMCPGuardrail(CustomGuardrail):
    def __init__(
        self,
        *,
        service_url=None,
        token_env="HUMANWILL_MCP_TOKEN",
        timeout_ms=6000,
        guardrail_name=None,
        event_hook="pre_mcp_call",
        default_on=True,
        **kwargs,
    ):
        # LiteLLM skips guards whose constructors raise ValueError/TypeError.
        # Configuration failure for this mandatory control must stop startup.
        if version("litellm") != "1.102.1":
            raise RuntimeError("HumanWill MCP profile requires LiteLLM 1.102.1")
        if event_hook != "pre_mcp_call" or default_on is not True:
            raise RuntimeError("HumanWill MCP requires default_on and mode pre_mcp_call")
        # The host also forwards defaults for unrelated providers; ignore those.
        if any(
            kwargs.get(k)
            for k in (
                "run_in_parallel",
                "mask_request_content",
                "mask_response_content",
                "only_scan_new_messages",
                "scan_raw_request",
                "skip_tool_messages",
                "scan_only_tool_results",
                "tags",
                "apply_to_roles",
            )
        ):
            raise RuntimeError("HumanWill MCP does not support masking, scoping or parallel guards")
        if type(timeout_ms) is not int or not 1 <= timeout_ms <= 120000:
            raise RuntimeError("Invalid HumanWill MCP timeout")
        try:
            check_url(service_url)
            token = os.environ.get(token_env, "")
            check_token(token)
        except Exception:
            raise RuntimeError("HumanWill MCP service URL or credentials are invalid") from None
        super().__init__(
            guardrail_name=guardrail_name,
            event_hook=event_hook,
            default_on=True,
            run_in_parallel=False,
        )
        self.service_url, self.token, self.timeout_ms = service_url, token, timeout_ms

    @classmethod
    def get_supported_event_hooks(cls):
        return [GuardrailEventHooks.pre_mcp_call]

    def should_run_guardrail(self, data, event_type):
        # Mandatory on this route even when a request opts out of global guards.
        return event_type == GuardrailEventHooks.pre_mcp_call

    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        if call_type == "list_mcp_tools":
            return data  # Discovery is not execution; no tool-poisoning claim.
        try:
            if call_type != "call_mcp_tool":
                raise ValueError("Unsupported MCP event")
            request = invocation(data)
            result = await assess(request, self.service_url, self.token, self.timeout_ms)
            current = invocation(data)
            if current["content"] != request["content"]:
                raise ValueError("Invocation changed during assessment")
            if result["enforcement"]["requested"] == "block":
                raise ValueError("Policy denied invocation")
        except Exception:
            # Do not expose arguments, credentials or provider exceptions to clients/logs.
            raise HTTPException(403, "HumanWill MCP policy check denied this operation") from None
        return data  # Never rewrite tool names or arguments; no retries.
