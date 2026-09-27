"""LiteLLM 1.102.1 deployment callback restricting the supported gateway surface.

Imported only inside a LiteLLM host; LiteLLM is not a service dependency.
"""

from fastapi import HTTPException
from litellm.integrations.custom_logger import CustomLogger

from ..errors import PolicyError
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
