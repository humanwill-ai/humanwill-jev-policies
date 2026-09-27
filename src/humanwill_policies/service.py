"""Authenticated, bounded ASGI service. Deployment controls never come from request data."""

import asyncio
import hmac
import json
import logging
import os
import stat

from jsonschema import Draft202012Validator
from starlette.applications import Starlette
from starlette.requests import ClientDisconnect
from starlette.responses import JSONResponse
from starlette.routing import Route

from .connectors import events
from .contracts import MAX_REQUEST_BYTES, schema, validate_contract
from .errors import PolicyError
from .providers import decode_json
from .runtime import EgressPermit
from .serialization import digest, parse_yaml

LOG = logging.getLogger("humanwill.audit")
SERVICE_SCHEMA = schema("service")


def read_settings(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError
            data = stream.read(65537)
        if len(data) > 65536:
            raise ValueError
        settings = parse_yaml(data.decode(), "service configuration")
    except (OSError, UnicodeError, ValueError):
        raise PolicyError("invalid_service_config", "Cannot read service configuration") from None
    if next(Draft202012Validator(SERVICE_SCHEMA).iter_errors(settings), None):
        raise PolicyError("invalid_service_config", "Invalid service configuration")
    return settings


def create_app(evaluator, settings, *, evidence_resolver=None):
    """Resolver is trusted deployment code; called only when metadata is enabled.

    It receives (principal ID, normalized event) and returns EvidenceContext, not
    raw request headers. No network endpoint accepts an EvidenceContext assertion.
    """
    if next(Draft202012Validator(SERVICE_SCHEMA).iter_errors(settings), None):
        raise PolicyError("invalid_service_config", "Invalid service configuration")
    settings = json.loads(json.dumps(settings))
    timeout = settings.get("request_timeout_ms", 7000) / 1000
    if timeout * 1000 <= evaluator.limits.timeout_ms:
        raise PolicyError("invalid_deadline", "Service deadline must exceed evaluation deadline")
    slots = asyncio.Semaphore(settings.get("max_in_flight", 8))
    settings_sha256 = digest(settings)
    credentials = []
    for name, principal in settings["principals"].items():
        token = os.environ.get(principal["token_env"], "")
        if len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
            raise PolicyError(
                "missing_credentials", "Service tokens need 32+ non-space ASCII chars"
            )
        if any(hmac.compare_digest(token, old) for old, _, _ in credentials):
            raise PolicyError(
                "duplicate_credentials", "Each service principal needs a unique token"
            )
        connector = principal["connector"]
        allowed = (
            {"prompt", "tool_action", "model_request", "response"}
            if connector == "native"
            else {"model_request", "response"}
            if connector in ("litellm", "agentgateway")
            else {"prompt", "tool_action"}
        )
        if not set(principal["stages"]) <= allowed:
            raise PolicyError("unsupported_stage", "Principal has an unsupported stage")
        if principal["on_protocol_error"] == "allow_monitor" and any(
            set(p.stages).intersection(principal["stages"])
            and evaluator.config["policies"][p.id]["enabled"]
            and evaluator.config["policies"][p.id]["mode"] == "enforce"
            for p in evaluator.bundle.policies
        ):
            raise PolicyError(
                "unsafe_failure_mode", "Protocol fail-open requires monitoring policies"
            )
        credentials.append((token, name, principal))

    def audit(**fields):
        LOG.info(
            json.dumps({"service_configuration_sha256": settings_sha256, **fields}, sort_keys=True)
        )

    def reply(connector, block, result=None, error=None):
        headers = {"Cache-Control": "no-store"}
        if result:
            headers["X-HumanWill-Request-ID"] = result["request_id"]
        if connector == "litellm":
            body = (
                {"action": "BLOCKED", "blocked_reason": "HumanWill policy check denied"}
                if block
                else {"action": "NONE"}
            )
        elif connector == "agentgateway":
            body = (
                {"action": {"body": "HumanWill policy check denied", "status_code": 403}}
                if block
                else {"action": {}}
            )
        else:
            body = result if result is not None else {"error": error or "evaluation_error"}
        return JSONResponse(
            body,
            status_code=200 if result or connector in ("litellm", "agentgateway") else 422,
            headers=headers,
        )

    async def health(request):
        return JSONResponse({"status": "ready"}, headers={"Cache-Control": "no-store"})

    async def endpoint(request):
        connector = request.path_params.get("connector")
        path = request.url.path
        if path == "/beta/litellm_basic_guardrail_api":
            connector = "litellm"
        elif path in ("/request", "/response"):
            connector = "agentgateway"
        elif path == "/v1/evaluate":
            connector = "native"
        authorization = request.headers.getlist("authorization")
        supplied = (
            authorization[0][7:]
            if len(authorization) == 1 and authorization[0].startswith("Bearer ")
            else ""
        )
        # LiteLLM's generic API uses x-api-key, not Bearer, for api_key config.
        api_keys = request.headers.getlist("x-api-key")
        if connector == "litellm" and not authorization and len(api_keys) == 1:
            supplied = api_keys[0]
        elif api_keys:
            supplied = ""  # Reject ambiguous authentication.
        match = None
        for token, name, principal in credentials:
            if supplied.isascii() and hmac.compare_digest(supplied, token):
                match = (name, principal)
        if match is None:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        name, principal = match
        if principal["connector"] != connector:
            return JSONResponse({"error": "forbidden_connector"}, status_code=403)
        result = None
        try:
            if slots.locked():
                raise PolicyError("service_overloaded", "Service at capacity")
            async with slots, asyncio.timeout(timeout):
                if request.headers.get("content-encoding", "identity") != "identity":
                    events.unsupported()
                if request.headers.get("content-type", "").split(";")[0] != "application/json":
                    events.unsupported()
                data = bytearray()
                async for chunk in request.stream():
                    data.extend(chunk)
                    if len(data) > MAX_REQUEST_BYTES:
                        raise PolicyError("payload_limit", "Request too large")
                payload = decode_json(bytes(data))
                if connector == "native":
                    normalized = payload
                    validate_contract("request", normalized)
                elif connector == "litellm":
                    normalized = events.litellm(payload)
                elif connector == "agentgateway":
                    if request.headers.getlist("x-humanwill-text-profile") != ["v1"]:
                        events.unsupported()
                    normalized = events.agentgateway(
                        payload, "model_request" if path == "/request" else "response"
                    )
                else:
                    normalized = events.hook(payload, connector, request.path_params["event"])
                if normalized["stage"] not in principal["stages"]:
                    return JSONResponse({"error": "forbidden_stage"}, status_code=403)
                evidence = None
                if evaluator.config["metadata"]["enabled"] and evidence_resolver is not None:
                    evidence = await evidence_resolver(name, normalized)
                permit = (
                    EgressPermit(
                        digest(normalized), evaluator.bundle.sha256, evaluator.backend.transport
                    )
                    if settings.get("allow_external_evaluation", False)
                    else None
                )
                result = await evaluator.evaluate(normalized, evidence=evidence, egress=permit)
                # CLI prompt is always assessment-only regardless of another principal's mode.
                if connector == "copilot_cli" and normalized["stage"] == "prompt":
                    result["enforcement"] = {"requested": "none", "actual": "not_requested"}
                audit(
                    principal=name,
                    connector=connector,
                    stage=normalized["stage"],
                    request_id=result["request_id"],
                    request_sha256=result["request_sha256"],
                    bundle_sha256=result["bundle_sha256"],
                    configuration_sha256=result["configuration_sha256"],
                    decision=result["decision"],
                    enforcement=result["enforcement"],
                    duration_ms=result["duration_ms"],
                    coverage=result["coverage"],
                    policies=[
                        {
                            "id": p["policy_id"],
                            "version": p["policy_version"],
                            "judgment": p["judgment"],
                            "mode": p["mode"],
                            "reasons": p["reasons"],
                        }
                        for p in result["policies"]
                    ],
                    errors=[e["code"] for e in result["errors"]],
                )
                return reply(connector, result["enforcement"]["requested"] == "block", result)
        except (PolicyError, TimeoutError, ClientDisconnect) as exc:
            code = exc.code if isinstance(exc, PolicyError) else "service_timeout_or_disconnect"
        except Exception:
            code = "service_error"  # Never log exception text, body, or tokens.
        block = principal["on_protocol_error"] == "block"
        audit(
            principal=name,
            connector=connector,
            error=code,
            requested="block" if block else "none",
            actual="unconfirmed",
        )
        return reply(connector, block, error=code)

    return Starlette(
        routes=[
            Route("/healthz", health),
            Route("/readyz", health),
            Route("/v1/evaluate", endpoint, methods=["POST"]),
            Route("/beta/litellm_basic_guardrail_api", endpoint, methods=["POST"]),
            Route("/request", endpoint, methods=["POST"]),
            Route("/response", endpoint, methods=["POST"]),
            Route("/v1/hooks/{connector}/{event}", endpoint, methods=["POST"]),
        ]
    )
