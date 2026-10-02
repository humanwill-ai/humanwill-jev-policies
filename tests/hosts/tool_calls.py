"""Actual pinned LiteLLM process: withhold complete proposals until action checks pass."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

import httpx
from gateways import config
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from support import TOKEN, dump_yaml, policy_app, port, server, wait_http


def tool(destination="internal", id="call-1"):
    return {
        "id": id,
        "type": "function",
        "function": {"name": "upload", "arguments": json.dumps({"destination": destination})},
    }


def model_app(calls):
    async def completion(request):
        body = await request.json()
        calls.append(body)
        label = body["messages"][-1]["content"]
        tools = [tool()]
        text = None
        if label == "block":
            tools = [tool("HW_DENY")]
        elif label == "multiple_block":
            tools.append(tool("HW_DENY", "call-2"))
        elif label == "multiple_allow":
            tools.append(tool("internal-two", "call-2"))
        elif label == "malformed":
            tools[0]["function"]["arguments"] = "{"
        elif label == "error":
            tools = [tool("HW_ERROR")]
        elif label == "timeout":
            tools = [tool("HW_TIMEOUT")]
        elif label == "missing_metadata":
            tools = [tool("MISSING_FACTS")]
        elif label == "mixed":
            text = "A proposed upload"
        elif label == "truncated":
            tools[0]["function"]["arguments"] = '{"destination":"internal"}'
        return JSONResponse(
            {
                "id": "synthetic",
                "object": "chat.completion",
                "created": 1,
                "model": "synthetic",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": text, "tool_calls": tools},
                        "finish_reason": "length" if label == "truncated" else "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        )

    return Starlette(routes=[Route("/v1/chat/completions", completion, methods=["POST"])])


def relay_config(hostport, policyport):
    return {
        "binds": [
            {
                "port": hostport,
                "listeners": [
                    {
                        "routes": [
                            {
                                "matches": [{"path": {"exact": "/v1/chat/completions"}}],
                                "backends": [
                                    {
                                        "host": f"127.0.0.1:{policyport}",
                                        "policies": {"backendAuth": {"key": TOKEN}},
                                    }
                                ],
                            }
                        ]
                    }
                ],
            }
        ]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary")
    parser.add_argument("--host", choices=("litellm", "agentgateway", "relay"), default="litellm")
    args = parser.parse_args()
    if args.host != "relay" and not args.binary:
        parser.error("--binary is required for gateway host tests")
    binary = str(Path(args.binary).resolve()) if args.binary else None
    reports = []
    out = Path("artifacts/hosts")
    out.mkdir(parents=True, exist_ok=True)
    for mode in ("enforce", "monitor"):
        with tempfile.TemporaryDirectory(prefix="humanwill-tools-") as tmp:
            root = Path(tmp)
            captures, calls, faults = [], [], {}
            connector = "litellm" if args.host == "litellm" else "agentgateway"
            with (
                server(model_app(calls)) as modelport,
                server(
                    policy_app(
                        root / "policies",
                        connector,
                        mode,
                        captures,
                        faults,
                        tool_profile=True,
                        model_backend=None
                        if connector == "litellm"
                        else {
                            "url": f"http://127.0.0.1:{modelport}/v1/chat/completions",
                            "model": "synthetic",
                        },
                    )
                ) as policyport,
            ):
                hostport = policyport if args.host == "relay" else port()
                conf = config("litellm", hostport, policyport, modelport)
                if args.host == "litellm":
                    conf["litellm_settings"]["callbacks"] = [
                        "humanwill_policies.connectors.litellm_profile.tool_profile"
                    ]
                else:
                    conf = relay_config(hostport, policyport)
                dump_yaml(root / "config.yaml", conf)
                env = {
                    **os.environ,
                    "LITELLM_LOCAL_MODEL_COST_MAP": "True",
                    "DO_NOT_TRACK": "1",
                    "DEBUG": "false",
                }
                env.pop("PYTHONPATH", None)
                with (out / f"{args.host}-tools-{mode}.log").open("w") as log:
                    command = (
                        [binary, "--config", str(root / "config.yaml"), "--port", str(hostport)]
                        if args.host == "litellm"
                        else [binary, "-f", str(root / "config.yaml")]
                    )
                    proc = (
                        subprocess.Popen(command, env=env, cwd=root, stdout=log, stderr=log)
                        if args.host != "relay"
                        else None
                    )
                    try:
                        if proc:
                            wait_http(f"http://127.0.0.1:{hostport}/health/liveliness", proc)
                        for label in [
                            "allow",
                            "block",
                            "multiple_block",
                            "multiple_allow",
                            "mixed",
                            "malformed",
                            "error",
                            "timeout",
                            "missing_metadata",
                            "history",
                            "truncated",
                            "stream",
                            "unavailable",
                        ]:
                            body = {
                                "model": "synthetic",
                                "stream": label == "stream",
                                "messages": [{"role": "user", "content": label}],
                                "tools": [
                                    {
                                        "type": "function",
                                        "function": {
                                            "name": "upload",
                                            "parameters": {"type": "object"},
                                        },
                                    }
                                ],
                            }
                            if label == "history":
                                body["messages"] = [
                                    {
                                        "role": "assistant",
                                        "content": None,
                                        "tool_calls": [tool("HW_DENY", "old-call")],
                                    },
                                    {"role": "tool", "tool_call_id": "old-call", "content": "done"},
                                    {"role": "user", "content": "history"},
                                ]
                            faults["unavailable"] = label == "unavailable"
                            before, measured = len(calls), len(captures)
                            response = httpx.post(
                                f"http://127.0.0.1:{hostport}/v1/chat/completions",
                                headers={
                                    "Authorization": "Bearer "
                                    + (
                                        TOKEN
                                        if args.host == "relay"
                                        else "sk-synthetic-host-client"
                                    )
                                },
                                json=body,
                                timeout=20,
                                trust_env=False,
                            )
                            blocked = label in (
                                "malformed",
                                "truncated",
                                "stream",
                                "unavailable",
                            ) or (
                                mode == "enforce"
                                and label
                                in (
                                    "block",
                                    "multiple_block",
                                    "error",
                                    "timeout",
                                    "missing_metadata",
                                )
                            )
                            assert (response.status_code != 200) == blocked, (
                                mode,
                                label,
                                response.status_code,
                                response.text[:1000],
                            )
                            if blocked:
                                assert '"tool_calls"' not in response.text, (label, response.text)
                            else:
                                result = response.json()["choices"][0]["message"]["tool_calls"]
                                assert len(result) == (
                                    2
                                    if label == "multiple_allow" or label == "multiple_block"
                                    else 1
                                )
                                assert result[0]["function"]["name"] == "upload"
                            if label in ("stream", "unavailable"):
                                assert len(calls) == before, label
                            if label == "history":
                                assert len(captures) - measured == 1, (
                                    "history assessed as new action"
                                )
                            reports.append(
                                {
                                    "mode": mode,
                                    "case": label,
                                    "status": response.status_code,
                                    "downstream_calls": len(calls) - before,
                                    "evaluator_calls": len(captures) - measured,
                                    "passed": True,
                                }
                            )
                    finally:
                        if proc:
                            proc.terminate()
                            try:
                                proc.wait(10)
                            except subprocess.TimeoutExpired:
                                proc.kill()
                                proc.wait()
    (out / f"{args.host}-tool-calls-report.json").write_text(json.dumps(reports, indent=2) + "\n")
    print(f"{len(reports)} {args.host} tool-call scenarios passed")


if __name__ == "__main__":
    main()
