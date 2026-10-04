"""Bounded command hook client; stdout is exclusively the host's JSON contract."""

import asyncio
import json
import os
import sys
from urllib.parse import urlsplit

import httpx

from .contracts import MAX_REQUEST_BYTES, validate_contract
from .errors import PolicyError
from .hook_events import HOOKS, hook, hook_output
from .json_codec import decode_json, digest


def check_url(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise PolicyError(
            "invalid_service_url", "Use an HTTP(S) service origin without credentials"
        )
    if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "::1", "localhost"):
        raise PolicyError("insecure_service_url", "Remote service connections require HTTPS")


async def assess(payload, runtime, name, url, token, timeout_ms, *, transport=None):
    check_url(url)
    normalized = hook(payload, runtime, name)
    if len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
        raise PolicyError("missing_credentials", "Hook service token is missing or invalid")
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
            f"{url.rstrip('/')}/v1/hooks/{runtime}/{name}",
            headers={"Authorization": "Bearer " + token, "Accept-Encoding": "identity"},
            json=payload,
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
    normalized["request_id"] = result["request_id"]
    if (
        result["request_sha256"] != digest(normalized)
        or result["coverage"] != normalized["coverage"]
    ):
        raise PolicyError("event_mismatch", "Verdict does not cover this event")
    if result["simulated"] and result["enforcement"]["requested"] != "none":
        raise PolicyError("service_response", "Simulated verdict cannot request enforcement")
    return result


def run(args):
    # The deployment-selected runtime/event determines denial output even for malformed stdin.
    if args.event not in HOOKS[args.runtime]:
        print(json.dumps(hook_output(args.runtime, args.event, True)))
        return 2
    blocked = args.on_error == "block"
    diagnostic = {"event": args.event, "runtime": args.runtime, "actual": "unconfirmed"}
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise PolicyError("payload_limit", "Hook payload too large")
        payload = decode_json(raw)
        # Never transmit cwd, transcript_path, session identifiers or unrelated host fields.
        normalized = hook(payload, args.runtime, args.event)
        if normalized["stage"] == "prompt":
            payload = {"prompt": payload["prompt"]}
        elif args.runtime == "copilot_local":
            payload = {"tool_name": payload["tool_name"], "tool_input": payload["tool_input"]}
        else:
            payload = {"toolName": payload["toolName"], "toolArgs": payload["toolArgs"]}
        if args.runtime == "copilot_local":
            payload["hook_event_name"] = args.event
        result = asyncio.run(
            assess(
                payload,
                args.runtime,
                args.event,
                args.url,
                os.environ.get(args.token_env, ""),
                args.timeout_ms,
            )
        )
        blocked = result["enforcement"]["requested"] == "block"
        diagnostic.update(
            request_id=result["request_id"],
            decision=result["decision"],
            requested=result["enforcement"]["requested"],
            simulated=result["simulated"],
        )
    except Exception as exc:
        diagnostic["error"] = exc.code if isinstance(exc, PolicyError) else "hook_evaluation_error"
        diagnostic["requested"] = "block" if blocked else "none"
    assessment_only = args.runtime == "copilot_cli" and args.event == "userPromptSubmitted"
    if assessment_only:
        diagnostic.update(requested="none", actual="not_requested", assessment_only=True)
    diagnostic["output"] = "deny" if blocked and not assessment_only else "default_permissions"
    print(json.dumps(diagnostic), file=sys.stderr)
    print(json.dumps(hook_output(args.runtime, args.event, blocked)))
    return 0
