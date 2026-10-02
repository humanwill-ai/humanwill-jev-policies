"""Installed wheel + actual LiteLLM + actual MCP server, synthetic evaluator only."""

import argparse
import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.fastmcp import FastMCP
from support import TOKEN, dump_yaml, policy_app, port, server, wait_http


def tool_server(effects):
    mcp = FastMCP("HumanWill synthetic tools", stateless_http=True, json_response=True)

    @mcp.tool()
    def record_action(destination: str, payload: dict) -> str:
        """Record a synthetic side effect for enforcement tests; no external I/O."""
        effects.append({"destination": destination, "payload": payload})
        return "recorded"

    return mcp


async def exercise(hostport, effects, captures, faults, mode, reports):
    async with (
        streamablehttp_client(
            f"http://127.0.0.1:{hostport}/mcp/",
            headers={"Authorization": "Bearer sk-synthetic-master-key"},
        ) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
        assert len(tools.tools) == 1, tools
        assert not effects and not captures, "Discovery must not be assessed as execution"
        name = tools.tools[0].name
        reports.append({"mode": mode, "case": "discovery", "passed": True})
        for label in ["allow", "HW_DENY", "HW_ERROR", "HW_TIMEOUT", "MISSING_FACTS", "outage"]:
            faults["unavailable"] = label == "outage"
            before, judgments = len(effects), len(captures)
            args = {"destination": label, "payload": {"nested": [1, False, None, {"x": "y"}]}}
            result = await session.call_tool(name, args)
            expected = label == "allow" or (mode == "monitor" and label != "outage")
            assert result.isError == (not expected), (mode, label, result)
            assert len(effects) == before + int(expected), (mode, label, effects)
            if expected:
                assert effects[-1] == args, "Executed arguments differ from supplied arguments"
            if label != "outage":
                assert len(captures) > judgments, "MCP invocation skipped evaluator"
                content = captures[judgments]["state"]["content"]
                assert content[0]["arguments"] == args
                assert content[0]["name"] == "record_action"
            reports.append({"mode": mode, "case": label, "executed": expected, "passed": True})
        faults["unavailable"] = False
        before = len(effects)
        arguments = [
            {"destination": name, "payload": {"id": index}}
            for index, name in enumerate(["allow-a", "HW_DENY", "allow-b", "HW_DENY"])
        ]
        results = await asyncio.gather(*(session.call_tool(name, args) for args in arguments))
        expected = [True, mode == "monitor", True, mode == "monitor"]
        assert [not result.isError for result in results] == expected
        assert sorted(effects[before:], key=lambda x: x["payload"]["id"]) == [
            args for args, permitted in zip(arguments, expected, strict=True) if permitted
        ]
        reports.append({"mode": mode, "case": "concurrent_isolated_calls", "passed": True})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    args = parser.parse_args()
    binary = str(Path(args.binary).resolve())
    reports = []
    out = Path("artifacts/hosts")
    out.mkdir(parents=True, exist_ok=True)
    for mode in ("enforce", "monitor"):
        effects, captures, faults = [], [], {}
        with (
            tempfile.TemporaryDirectory(prefix="humanwill-mcp-") as tmp,
            server(tool_server(effects).streamable_http_app()) as mcpport,
        ):
            root = Path(tmp)
            with server(
                policy_app(root / "policies", "native", mode, captures, faults, tool_profile=True)
            ) as policyport:
                hostport = port()
                conf = {
                    "mcp_servers": {
                        "fixture": {"url": f"http://127.0.0.1:{mcpport}/mcp", "transport": "http"}
                    },
                    "guardrails": [
                        {
                            "guardrail_name": "humanwill-mcp",
                            "litellm_params": {
                                "guardrail": (
                                    "humanwill_policies.connectors.litellm_mcp.HumanWillMCPGuardrail"
                                ),
                                "mode": "pre_mcp_call",
                                "default_on": True,
                                "service_url": f"http://127.0.0.1:{policyport}",
                                "timeout_ms": 2000,
                            },
                        }
                    ],
                    "general_settings": {"master_key": "sk-synthetic-master-key"},
                }
                dump_yaml(root / "config.yaml", conf)
                env = {
                    **os.environ,
                    "HUMANWILL_MCP_TOKEN": TOKEN,
                    "LITELLM_LOCAL_MODEL_COST_MAP": "True",
                    "DO_NOT_TRACK": "1",
                    "DEBUG": "false",
                }
                env.pop("PYTHONPATH", None)
                with (out / f"litellm-mcp-{mode}.log").open("w") as log:
                    proc = subprocess.Popen(
                        [binary, "--config", str(root / "config.yaml"), "--port", str(hostport)],
                        cwd=root,
                        env=env,
                        stdout=log,
                        stderr=log,
                    )
                    try:
                        wait_http(f"http://127.0.0.1:{hostport}/health/liveliness", proc)
                        asyncio.run(exercise(hostport, effects, captures, faults, mode, reports))
                    finally:
                        proc.terminate()
                        proc.wait(timeout=15)
                if mode == "enforce":
                    # The pinned host normally skips ValueError-invalid guards and
                    # starts unprotected. This profile must instead fail startup.
                    for label in ("disabled", "missing_token"):
                        conf["guardrails"][0]["litellm_params"]["default_on"] = label != "disabled"
                        invalid_env = {**env}
                        if label == "missing_token":
                            invalid_env.pop("HUMANWILL_MCP_TOKEN")
                        dump_yaml(root / "config.yaml", conf)
                        with (out / f"litellm-mcp-invalid-{label}.log").open("w") as log:
                            failed = subprocess.run(
                                [
                                    binary,
                                    "--config",
                                    str(root / "config.yaml"),
                                    "--port",
                                    str(hostport),
                                ],
                                cwd=root,
                                env=invalid_env,
                                stdout=log,
                                stderr=log,
                                timeout=45,
                            )
                        assert failed.returncode != 0, (
                            "Invalid guardrail started an unprotected proxy"
                        )
                        reports.append({"case": "startup_" + label, "passed": True})
    (out / "litellm-mcp-report.json").write_text(json.dumps(reports, indent=2) + "\n")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
