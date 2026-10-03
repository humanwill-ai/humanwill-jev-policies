"""Agentgateway 1.5.0 ExtMCP request guard; no tool traffic is relayed here."""

import asyncio
import hmac
import os

import grpc

from ..contracts import MAX_REQUEST_BYTES
from ..errors import PolicyError
from ..hooks import check_url
from ..providers import decode_json
from .ext_mcp import ext_mcp_pb2 as wire
from .mcp import assess, check_token, invocation

SERVICE = "agentgateway.dev.ext_mcp.ExtMcp"
DENIED = "HumanWill MCP policy check denied this operation"


def normalize(request, targets):
    if (
        request.method != "tools/call"
        or len(request.service_names) != 1
        or request.service_names[0] not in targets
        or not request.HasField("mcp_request")
        or len(request.mcp_request) > MAX_REQUEST_BYTES
    ):
        raise PolicyError("unsupported_payload", "Unsupported MCP invocation or target")
    params = decode_json(request.mcp_request)
    if not isinstance(params, dict) or set(params) - {"name", "arguments", "_meta"}:
        raise PolicyError("unsupported_payload", "Unsupported MCP invocation parameters")
    meta = params.get("_meta")
    # A standard progress token is correlation data, not tool authorization.
    # Other extension fields and asynchronous tasks need their own coverage.
    if meta is not None and (not isinstance(meta, dict) or set(meta) - {"progressToken"}):
        raise PolicyError("unsupported_payload", "Unsupported MCP invocation metadata")
    return invocation(
        {
            "mcp_tool_name": params.get("name"),
            "mcp_arguments": {} if params.get("arguments") is None else params["arguments"],
            "mcp_server_name": request.service_names[0],
        }
    )


class Processor:
    def __init__(self, *, url, token, gateway_token, targets, timeout_ms=6000):
        check_url(url)
        check_token(token)
        check_token(gateway_token)
        if not targets or any(not isinstance(t, str) or not t.strip() for t in targets):
            raise PolicyError("invalid_targets", "Configure explicit MCP target names")
        if type(timeout_ms) is not int or not 1 <= timeout_ms <= 9000:
            raise PolicyError("invalid_timeout", "Use an ExtMCP deadline of 1–9000 milliseconds")
        self.url, self.token, self.gateway_token = url, token, gateway_token
        self.targets, self.timeout_ms = frozenset(targets), timeout_ms

    async def authenticate(self, context):
        values = [v for k, v in context.invocation_metadata() if k == "authorization"]
        if len(values) != 1 or not hmac.compare_digest(
            values[0].encode(), ("Bearer " + self.gateway_token).encode()
        ):
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid processor credentials")

    async def check_request(self, request, context):
        await self.authenticate(context)
        try:
            normalized = normalize(request, self.targets)
            result = await assess(normalized, self.url, self.token, self.timeout_ms)
            if result["enforcement"]["requested"] == "block":
                raise PolicyError("policy_denied", DENIED)
            return wire.McpRequestResult(**{"pass": wire.Pass()})
        except Exception:
            # Static denial for malformed input, timeout, provider/service errors;
            # never echo arguments, credentials or provider exception strings.
            return wire.McpRequestResult(
                error=wire.AuthorizationError(
                    code=wire.AuthorizationError.PERMISSION_DENIED, reason=DENIED
                )
            )

    async def check_response(self, request, context):
        await self.authenticate(context)
        # Response hooks are not supported. Fail visibly rather than silently pass.
        return wire.McpResponseResult(
            error=wire.AuthorizationError(
                code=wire.AuthorizationError.INVALID,
                reason="HumanWill supports tools/call request checks only",
            )
        )


def create_server(processor, *, max_in_flight=8):
    if type(max_in_flight) is not int or not 1 <= max_in_flight <= 128:
        raise PolicyError("invalid_capacity", "Use a concurrency limit of 1–128")
    server = grpc.aio.server(
        maximum_concurrent_rpcs=max_in_flight,
        options=[
            ("grpc.so_reuseport", 0),
            ("grpc.max_receive_message_length", MAX_REQUEST_BYTES),
            ("grpc.max_send_message_length", MAX_REQUEST_BYTES),
        ],
    )
    server.add_generic_rpc_handlers(
        (
            grpc.method_handlers_generic_handler(
                SERVICE,
                {
                    "CheckRequest": grpc.unary_unary_rpc_method_handler(
                        processor.check_request,
                        request_deserializer=wire.McpRequest.FromString,
                        response_serializer=wire.McpRequestResult.SerializeToString,
                    ),
                    "CheckResponse": grpc.unary_unary_rpc_method_handler(
                        processor.check_response,
                        request_deserializer=wire.McpResponse.FromString,
                        response_serializer=wire.McpResponseResult.SerializeToString,
                    ),
                },
            ),
        )
    )
    return server


async def serve(args):
    # h2c is deliberately restricted to a loopback sidecar in this first profile.
    # Never expose plaintext bearer tokens on a remote listener.
    processor = Processor(
        url=args.url,
        token=os.environ.get(args.token_env, ""),
        gateway_token=os.environ.get(args.gateway_token_env, ""),
        targets=args.target,
        timeout_ms=args.timeout_ms,
    )
    server = create_server(processor, max_in_flight=args.max_in_flight)
    if not server.add_insecure_port(f"127.0.0.1:{args.port}"):
        raise PolicyError("listener_error", "Unable to bind MCP processor")
    await server.start()
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=1)


def run(args):
    try:
        asyncio.run(serve(args))
    except KeyboardInterrupt:
        pass
    return 0
