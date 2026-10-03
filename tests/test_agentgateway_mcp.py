"""Optional ExtMCP gRPC wire tests: bounded failures and exact invocation binding."""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

try:
    import grpc

    from humanwill_policies.connectors.agentgateway_mcp import (
        SERVICE,
        Processor,
        create_server,
        normalize,
    )
    from humanwill_policies.connectors.ext_mcp import ext_mcp_pb2 as wire
except ImportError:
    grpc = None

from humanwill_policies.errors import PolicyError
from humanwill_policies.serialization import canonical

TOKEN = "synthetic-extmcp-token-0000000000000"


def request(**kwargs):
    return wire.McpRequest(
        **{
            "service_names": ["company"],
            "method": "tools/call",
            "mcp_request": b'{"name":"upload","arguments":{"nested":[1,false,null]}}',
            **kwargs,
        }
    )


@unittest.skipIf(grpc is None, "Install the agentgateway-mcp extra for gRPC checks")
class ExtMCPTests(unittest.TestCase):
    def processor(self, **kw):
        return Processor(
            url="http://localhost", token=TOKEN, gateway_token=TOKEN, targets=["company"], **kw
        )

    def test_normalization_full_arguments_no_credentials_or_claims(self):
        req = request()
        req.headers.add(key="authorization", value=b"PRIVATE_TOKEN")
        req.metadata_context.update({"role": "CLAIMED_ADMIN"})
        event = normalize(req, {"company"})
        self.assertEqual(event["content"][0]["arguments"], {"nested": [1, False, None]})
        self.assertNotIn("PRIVATE_TOKEN", canonical(event))
        self.assertNotIn("CLAIMED_ADMIN", canonical(event))
        for body in [b'{"name":"ping"}', b'{"name":"ping","arguments":null}']:
            self.assertEqual(
                normalize(request(mcp_request=body), {"company"})["content"][0]["arguments"], {}
            )

    def test_unsupported_methods_targets_and_payloads_rejected(self):
        for kw in [
            {"method": "tools/list"},
            {"service_names": []},
            {"service_names": ["company", "other"]},
            {"service_names": ["other"]},
            {"mcp_request": b'[{"name":"upload"}]'},
            {"mcp_request": b'{"name":"upload","name":"other"}'},
            {"mcp_request": b'{"name":"upload","arguments":[]}'},
            {"mcp_request": b'{"name":"upload","task":{}}'},
            {"mcp_request": b'{"name":"upload","_meta":{"authorized":true}}'},
            {"mcp_request": b"x" * 262145},
        ]:
            with self.subTest(kw=list(kw)), self.assertRaises(PolicyError):
                normalize(request(**kw), {"company"})

    def invoke(self, body=None, *, metadata=None, effect=None, method="CheckRequest"):
        async def run():
            srv = create_server(self.processor())
            port = srv.add_insecure_port("127.0.0.1:0")
            await srv.start()
            try:
                async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
                    call = channel.unary_unary(
                        f"/{SERVICE}/{method}",
                        request_serializer=lambda m: m.SerializeToString(),
                        response_deserializer=(
                            wire.McpRequestResult.FromString
                            if method == "CheckRequest"
                            else wire.McpResponseResult.FromString
                        ),
                    )
                    mock = (
                        AsyncMock(side_effect=effect)
                        if isinstance(effect, Exception)
                        else AsyncMock(
                            return_value=effect or {"enforcement": {"requested": "none"}}
                        )
                    )
                    with patch("humanwill_policies.connectors.agentgateway_mcp.assess", mock):
                        result = await call(
                            body or request(),
                            metadata=metadata
                            if metadata is not None
                            else (("authorization", "Bearer " + TOKEN),),
                            timeout=1,
                        )
                    return result, mock
            finally:
                await srv.stop(0)

        return asyncio.run(run())

    def test_actual_wire_pass_block_error_and_no_mutation(self):
        result, mock = self.invoke()
        self.assertEqual(result.WhichOneof("result"), "pass")
        self.assertFalse(result.HasField("header_mutation"))
        self.assertFalse(result.HasField("metadata"))
        self.assertEqual(mock.await_count, 1)
        for effect in (
            {"enforcement": {"requested": "block"}},
            TimeoutError("PRIVATE"),
            ValueError("PRIVATE"),
        ):
            result, mock = self.invoke(effect=effect)
            self.assertEqual(result.WhichOneof("result"), "error")
            self.assertNotIn("PRIVATE", result.error.reason)
            self.assertEqual(mock.await_count, 1)

    def test_authentication_uses_transport_not_body_headers(self):
        req = request()
        req.headers.add(key="authorization", value=("Bearer " + TOKEN).encode())
        for metadata in (
            (),
            (("authorization", "wrong"),),
            (("authorization", "Bearer " + TOKEN),) * 2,
        ):
            with self.assertRaises(grpc.RpcError) as error:
                self.invoke(req, metadata=metadata)
            self.assertEqual(error.exception.code(), grpc.StatusCode.UNAUTHENTICATED)

    def test_wrong_phase_and_unknown_payload_never_call_evaluator(self):
        result, mock = self.invoke(wire.McpResponse(method="tools/call"), method="CheckResponse")
        self.assertEqual(result.WhichOneof("result"), "error")
        self.assertEqual(mock.await_count, 0)
        result, mock = self.invoke(request(method="tools/list"))
        self.assertEqual(result.WhichOneof("result"), "error")
        self.assertEqual(mock.await_count, 0)

    def test_config_and_transport_size_limit(self):
        with self.assertRaises(PolicyError):
            self.processor(timeout_ms=10000)
        with self.assertRaises(PolicyError):
            create_server(self.processor(), max_in_flight=0)
        with self.assertRaises(grpc.RpcError) as error:
            self.invoke(
                request(
                    mcp_request=json.dumps(
                        {"name": "x", "arguments": {"text": "x" * 262144}}
                    ).encode()
                )
            )
        self.assertEqual(error.exception.code(), grpc.StatusCode.RESOURCE_EXHAUSTED)
