"""Fixed-route OpenAI-compatible relay for hosts whose webhook loses tool structure."""

import os
from urllib.parse import urlsplit

import httpx

from ..contracts import MAX_REQUEST_BYTES
from ..errors import PolicyError
from ..providers import decode_json
from .chat import validate_request
from .events import event, unsupported

# No client credentials, route overrides, extra body, provider tools or streaming.
REQUEST_FIELDS = {
    "model",
    "messages",
    "tools",
    "tool_choice",
    "parallel_tool_calls",
    "stream",
    "temperature",
    "top_p",
    "max_tokens",
    "max_completion_tokens",
    "stop",
    "seed",
    "n",
    "presence_penalty",
    "frequency_penalty",
    "response_format",
    "user",
}


def credentials(backend):
    url = urlsplit(backend["url"])
    if (
        url.scheme not in ("https", "http")
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
        or not url.path.endswith("/chat/completions")
        or (url.scheme == "http" and url.hostname not in ("localhost", "127.0.0.1", "::1"))
    ):
        raise PolicyError(
            "invalid_backend", "Backend needs HTTPS or loopback HTTP and a fixed path"
        )
    key = os.environ.get(backend.get("api_key_env", ""), "")
    if (backend.get("api_key_env") and not key) or (url.scheme == "https" and not key):
        raise PolicyError("missing_credentials", "Configure a backend credential")
    if key and (not key.isascii() or any(c.isspace() for c in key)):
        raise PolicyError("missing_credentials", "Invalid backend credential")
    return {"Authorization": "Bearer " + key} if key else {}


def request_event(body, backend):
    if set(body) - REQUEST_FIELDS or body.get("model") != backend["model"]:
        unsupported()
    return event("model_request", validate_request(body))


async def forward(body, backend, headers, *, transport=None):
    # The outer service timeout covers input read, all assessments and generation.
    # Never follow redirects or send connector/client headers to the upstream.
    async with httpx.AsyncClient(
        trust_env=False, follow_redirects=False, timeout=60, transport=transport
    ) as client:
        async with client.stream("POST", backend["url"], json=body, headers=headers) as response:
            if (
                response.status_code != 200
                or response.headers.get("content-type", "").split(";")[0] != "application/json"
            ):
                raise PolicyError("backend_error", "Model backend did not return a JSON success")
            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > MAX_REQUEST_BYTES:
                    raise PolicyError("response_limit", "Model response exceeds byte limit")
    return decode_json(bytes(data))
