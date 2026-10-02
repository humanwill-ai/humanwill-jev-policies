"""LiteLLM 1.102.1 deployment callback restricting the supported gateway surface.

Imported only inside a LiteLLM host; LiteLLM is not a service dependency.
"""

from fastapi import HTTPException
from litellm.integrations.custom_logger import CustomLogger

from ..errors import PolicyError
from .chat import validate_request, validate_response
from .events import messages


class TextChatProfile(CustomLogger):
    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        if call_type not in ("completion", "acompletion") or data.get("stream") not in (
            None,
            False,
        ):
            raise HTTPException(400, "HumanWill supports non-streaming chat completions only")
        raw = data.get("proxy_server_request", {}).get("body", {})
        # Deny client-side guardrail controls, route overrides and non-text surfaces.
        forbidden = {
            "guardrails",
            "api_base",
            "api_key",
            "base_url",
            "tools",
            "tool_choice",
            "functions",
            "function_call",
            "modalities",
            "audio",
            "prediction",
            "extra_body",
        }
        if not isinstance(raw, dict) or any(k in raw for k in forbidden):
            raise HTTPException(400, "HumanWill text profile rejects this request control")
        try:
            messages(data.get("messages"))
        except PolicyError:
            raise HTTPException(
                400, "HumanWill text profile requires plain text messages"
            ) from None
        return data


profile = TextChatProfile()


class ToolChatProfile(CustomLogger):
    """Opt-in full non-streaming function-call profile; use with the matching service."""

    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        if call_type not in ("completion", "acompletion"):
            raise HTTPException(400, "HumanWill supports chat completions only")
        raw = data.get("proxy_server_request", {}).get("body", {})
        forbidden = {"guardrails", "api_base", "api_key", "base_url", "prediction", "extra_body"}
        if not isinstance(raw, dict) or any(k in raw for k in forbidden):
            raise HTTPException(400, "HumanWill rejects this request control")
        try:
            validate_request(raw)
            validate_request(data)
        except PolicyError:
            raise HTTPException(400, "HumanWill requires supported non-streaming chat") from None
        return data

    async def async_post_call_success_hook(self, data, user_api_key_dict, response):
        try:
            validate_response(response.model_dump(exclude_none=True))
        except (PolicyError, AttributeError):
            raise HTTPException(400, "HumanWill rejects incomplete or unsupported output") from None
        return response


tool_profile = ToolChatProfile()
