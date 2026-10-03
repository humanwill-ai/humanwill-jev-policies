"""Actual Agentgateway + ExtMCP connector + HTTP service + observable MCP effects."""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import grpc
from mcp import ClientSession, McpError
from mcp.client.streamable_http import streamablehttp_client
from mcp_calls import tool_server
from support import TOKEN, dump_yaml, policy_app, port, server, wait_http

GATEWAY_TOKEN = "synthetic-gateway-mcp-token-00000000000"


def configuration(hostport, grpcport, upstreams, tokenfile):
    return {
        "binds": [
            {
                "port": hostport,
                "listeners": [
                    {
                        "routes": [
                            {
                                "matches": [{"path": {"exact": "/mcp"}}],
                                "policies": {
                                    "mcpGuardrails": {
                                        "processors": [
                                            {
                                                "kind": "remote",
                                                "host": f"127.0.0.1:{grpcport}",
                                                "failureMode": "failClosed",
                                                "methods": {"tools/call": "request"},
                                                "requestHeaders": {"allowed": [":method"]},
                                                "policies": {
                                                    "backendAuth": {"key": {"file": str(tokenfile)}}
                                                },
                                            }
                                        ]
                                    }
                                },
                                "backends": [
                                    {
                                        "mcp": {
                                            "prefixMode": "always",
                                            "targets": [
                                                {
                                                    "name": name,
                                                    "mcp": {
                                                        "host": f"http://127.0.0.1:{number}/mcp"
                                                    },
                                                }
                                                for name, number in upstreams.items()
                                            ],
                                        }
                                    }
                                ],
                            }
                        ]
                    }
                ],
            }
        ],
    }


async def wait_grpc(number):
    async with grpc.aio.insecure_channel(f"127.0.0.1:{number}") as channel:
        await asyncio.wait_for(channel.channel_ready(), 10)


async def exercise(hostport, effects, captures, faults, mode, bridge, reports):
    async with (
        streamablehttp_client(f"http://127.0.0.1:{hostport}/mcp") as (read, write, _),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        listed = await session.list_tools()
        names = {row.name for row in listed.tools}
        assert names == {n + "_record_action" for n in effects}, names
        assert not captures and not any(effects.values()), "Discovery became execution"
        reports.append({"mode": mode, "case": "discovery", "passed": True})

        async def call(target, arguments):
            try:
                result = await session.call_tool(target + "_record_action", arguments)
                return not result.isError
            except McpError:
                return False

        for label in [
            "allow",
            "HW_DENY",
            "HW_ERROR",
            "HW_TIMEOUT",
            "MISSING_FACTS",
            "outage",
            "other_target",
            "unconfigured_target",
        ]:
            target = {"other_target": "second", "unconfigured_target": "unconfigured"}.get(
                label, "company"
            )
            faults["unavailable"] = label == "outage"
            args = {"destination": label, "payload": {"nested": [1, False, None, {"n": 9}]}}
            before, judgments = len(effects[target]), len(captures)
            permitted = await call(target, args)
            expected = label in ("allow", "other_target") or (
                mode == "monitor" and label not in ("outage", "unconfigured_target")
            )
            assert permitted == expected, (mode, label, permitted)
            assert len(effects[target]) == before + int(expected), (mode, label, effects)
            if expected:
                assert effects[target][-1] == args
            if label not in ("outage", "unconfigured_target"):
                assert len(captures) > judgments, "Invocation bypassed evaluator"
                content = captures[judgments]["state"]["content"]
                assert content[0]["name"] == "record_action"
                assert content[0]["arguments"] == args
                assert json.dumps(target) in content[1]["text"]
            reports.append({"mode": mode, "case": label, "executed": expected, "passed": True})
        faults["unavailable"] = False
        args = [
            {"destination": d, "payload": {"id": i}}
            for i, d in enumerate(["allow", "HW_DENY", "allow", "HW_DENY"])
        ]
        before = len(effects["company"])
        results = await asyncio.gather(*(call("company", a) for a in args))
        expected = [True, mode == "monitor", True, mode == "monitor"]
        assert results == expected
        assert sorted(effects["company"][before:], key=lambda a: a["payload"]["id"]) == [
            a for a, ok in zip(args, expected, strict=True) if ok
        ]
        reports.append({"mode": mode, "case": "concurrent_calls", "passed": True})
        bridge.terminate()
        bridge.wait(timeout=10)
        before = len(effects["company"])
        assert not await call("company", {"destination": "allow", "payload": {}})
        assert len(effects["company"]) == before
        reports.append({"mode": mode, "case": "processor_unavailable", "passed": True})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    args = parser.parse_args()
    binary = str(Path(args.binary).resolve())
    out = Path("artifacts/hosts")
    out.mkdir(parents=True, exist_ok=True)
    reports = []
    for mode in ("enforce", "monitor"):
        effects = {n: [] for n in ("company", "second", "unconfigured")}
        captures, faults = [], {}
        with (
            tempfile.TemporaryDirectory(prefix="humanwill-extmcp-") as tmp,
            server(tool_server(effects["company"]).streamable_http_app()) as first,
            server(tool_server(effects["second"]).streamable_http_app()) as second,
            server(tool_server(effects["unconfigured"]).streamable_http_app()) as third,
        ):
            root = Path(tmp)
            with server(
                policy_app(root / "policies", "native", mode, captures, faults, tool_profile=True)
            ) as policyport:
                hostport, grpcport = port(), port()
                tokenfile = root / "gateway-token"
                tokenfile.write_text(GATEWAY_TOKEN)
                tokenfile.chmod(0o600)
                conf = configuration(
                    hostport,
                    grpcport,
                    {"company": first, "second": second, "unconfigured": third},
                    tokenfile,
                )
                dump_yaml(root / "config.yaml", conf)
                env = {
                    **os.environ,
                    "HUMANWILL_MCP_TOKEN": TOKEN,
                    "HUMANWILL_AGENTGATEWAY_MCP_TOKEN": GATEWAY_TOKEN,
                }
                env.pop("PYTHONPATH", None)
                with (
                    (out / f"agentgateway-mcp-{mode}.log").open("w") as hostlog,
                    (out / f"extmcp-{mode}.log").open("w") as bridgelog,
                ):
                    bridge = subprocess.Popen(
                        [
                            sys.executable,
                            "-m",
                            "humanwill_policies",
                            "agentgateway-mcp",
                            "--url",
                            f"http://127.0.0.1:{policyport}",
                            "--port",
                            str(grpcport),
                            "--target",
                            "company",
                            "--target",
                            "second",
                            "--timeout-ms",
                            "2000",
                        ],
                        cwd=root,
                        env=env,
                        stdout=bridgelog,
                        stderr=bridgelog,
                    )
                    proc = None
                    try:
                        asyncio.run(wait_grpc(grpcport))
                        proc = subprocess.Popen(
                            [binary, "-f", str(root / "config.yaml")],
                            cwd=root,
                            env=env,
                            stdout=hostlog,
                            stderr=hostlog,
                        )
                        wait_http(f"http://127.0.0.1:{hostport}/health/liveliness", proc)
                        asyncio.run(
                            exercise(hostport, effects, captures, faults, mode, bridge, reports)
                        )
                    finally:
                        for child in (proc, bridge):
                            if child is not None and child.poll() is None:
                                child.terminate()
                                child.wait(timeout=15)
    record = {
        "host": "Agentgateway 1.5.0",
        "scope": "synthetic evaluator; actual MCP side effects",
        "scenarios": reports,
        "completed_epoch": time.time(),
    }
    (out / "agentgateway-mcp-report.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
