"""MCP invocation normalization and a bounded, event-bound native service client."""

import asyncio

import httpx

from ..contracts import MAX_REQUEST_BYTES, validate_contract
from ..errors import PolicyError
from ..hooks import check_url
from ..providers import decode_json
from ..serialization import canonical, digest, json_value
from .events import event, unsupported


def invocation(data):
    """Only host-supplied fields; never forward credentials, headers or claimed identity."""
    if not isinstance(data, dict):
        unsupported()
    name, server = data.get("mcp_tool_name"), data.get("mcp_server_name")
    arguments = data.get("mcp_arguments")
    if (
        not isinstance(name, str)
        or not 1 <= len(name) <= 512
        or not isinstance(server, str)
        or not 1 <= len(server) <= 512
        or not isinstance(arguments, dict)
        or data.get("extra_headers")
    ):
        unsupported()
    # The pinned host executes a truthy modified_arguments override. Mutating
    # guardrails are outside this profile: do not approve a different payload.
    if data.get("modified_arguments") and data["modified_arguments"] != arguments:
        unsupported()
    json_value(arguments)
    # Detach nested objects from mutable host state before the network await.
    arguments = decode_json(canonical(arguments).encode())
    return event(
        "tool_action",
        [
            {"kind": "tool_action", "name": name, "arguments": arguments},
            {
                "kind": "text",
                "role": "unknown",
                "text": "MCP invocation before execution. Gateway-resolved server reference: "
                + canonical(server)
                + ". This reference identifies the route; it is not proof of authorization. "
                "Only the supplied arguments are inspected; referenced resource contents and "
                "the tool implementation are unavailable.",
            },
        ],
    )


def check_token(token):
    if len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
        raise PolicyError("missing_credentials", "MCP service token is missing or invalid")


async def assess(request, url, token, timeout_ms, *, transport=None):
    check_url(url)
    check_token(token)
    validate_contract("request", request)
    async with (
        asyncio.timeout(timeout_ms / 1000),
        httpx.AsyncClient(
            trust_env=False,
            follow_redirects=False,
            transport=transport,
            timeout=timeout_ms / 1000,
        ) as client,
    ):
        async with client.stream(
            "POST",
            f"{url.rstrip('/')}/v1/evaluate",
            headers={
                "Authorization": "Bearer " + token,
                "Accept-Encoding": "identity",
                "Content-Type": "application/json",
            },
            content=canonical(request).encode(),
        ) as response:
            if (
                response.status_code != 200
                or response.headers.get("content-encoding", "identity") != "identity"
            ):
                raise PolicyError("service_response", "Policy service did not return a verdict")
            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > MAX_REQUEST_BYTES:
                    raise PolicyError("payload_limit", "Service verdict too large")
    result = decode_json(bytes(data))
    validate_contract("result", result)
    if result["format"] not in ("humanwill.result/2", "humanwill.result/3", "humanwill.result/4"):
        raise PolicyError("service_response", "Unsupported verdict version")
    if (
        result["request_id"] != request["request_id"]
        or result["request_sha256"] != digest(request)
        or result["coverage"] != request["coverage"]
    ):
        raise PolicyError("event_mismatch", "Verdict does not cover this invocation")
    if result["simulated"] and result["enforcement"]["requested"] != "none":
        raise PolicyError("service_response", "Simulated verdict cannot request enforcement")
    return result
