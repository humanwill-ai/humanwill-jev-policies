"""Synthetic beta engineering measurement through real LiteLLM and live Jev."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
import yaml
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.providers import JevBackend, MockBackend
from humanwill_policies.service import create_app

from .backends import choice_answer
from .live_support import Ledger, credential, ledger_total
from .preview_latency import (
    ROOT,
    TOKEN,
    RecordingEvaluator,
    dump_yaml,
    gateway_config,
    port,
    server,
    stats,
    wait_http,
)
from .question_context import sha256
from .restart_accounting import RestartMeteredBackend

CAMPAIGN = ROOT / "evals/step6/beta-tools-v1"


def action(label):
    return {
        "destination": f"https://{'internal' if label == 'allow' else 'public'}.example.test",
        "source_code": "def add(a, b): return a + b",
    }


def tool_model():
    async def complete(request):
        body = await request.json()
        label = body["messages"][-1]["content"]
        return JSONResponse(
            {
                "id": "synthetic-beta",
                "object": "chat.completion",
                "created": 1,
                "model": "synthetic",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-beta",
                                    "type": "function",
                                    "function": {
                                        "name": "upload_project_code",
                                        "arguments": json.dumps(action(label)),
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        )

    return Starlette(routes=[Route("/v1/chat/completions", complete, methods=["POST"])])


def tool_server(effects):
    mcp = FastMCP("Synthetic beta tools", stateless_http=True, json_response=True)

    @mcp.tool()
    def upload_project_code(destination: str, source_code: str) -> str:
        """Synthetic upload: record arguments locally without network or file I/O."""
        effects.append({"destination": destination, "source_code": source_code})
        return "recorded"

    return mcp.streamable_http_app()


@contextmanager
def host(binary, conf, root, log_path):
    number = port()
    dump_yaml(root / "host.yaml", conf)
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "OPENROUTER_API_KEY")}
    env.update(
        HOST_FIXTURE_TOKEN=TOKEN,
        HUMANWILL_MCP_TOKEN=TOKEN + "-mcp",
        LITELLM_LOCAL_MODEL_COST_MAP="True",
        DO_NOT_TRACK="1",
        DEBUG="false",
    )
    with log_path.open("w") as log:
        process = subprocess.Popen(
            [str(binary), "--config", str(root / "host.yaml"), "--port", str(number)],
            cwd=root,
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            wait_http(f"http://127.0.0.1:{number}/health/liveliness", process)
            yield number
        finally:
            process.terminate()
            process.wait(timeout=20)


async def measure(path, arm, number, backend, evaluator, effects, rows, save):
    async def one(index, label, invoke):
        if backend.fatal:
            raise RuntimeError("Accounting stopped")
        before = len(effects)
        c, e = len(backend.calls), len(evaluator.records)
        start = time.perf_counter()
        allowed, detail = await invoke(label)
        duration = (time.perf_counter() - start) * 1000
        expected = arm == "baseline" or label == "allow"
        row = {
            "path": path,
            "arm": arm,
            "index": index,
            "cold": index == 0,
            "label": label,
            "duration_ms": duration,
            "allowed": allowed,
            "expected_allow": expected,
            "detail": detail,
            "provider_calls": copy.deepcopy(backend.calls[c:]),
            "assessments": copy.deepcopy(evaluator.records[e:]),
            "side_effects": copy.deepcopy(effects[before:]),
        }
        rows.append(row)
        save()
        if path == "mcp":
            assert effects[before:] == ([action(label)] if allowed else []), row
        if arm == "guarded":
            assert row["assessments"] and row["provider_calls"], "Missing real inspection"
        # Preserve semantic errors as results, not reasons to selectively rerun.
        if backend.fatal:
            raise RuntimeError("New unknown charge; stop")

    if path == "proposal":
        async with httpx.AsyncClient(trust_env=False, timeout=45) as client:

            async def invoke(label):
                response = await client.post(
                    f"http://127.0.0.1:{number}/v1/chat/completions",
                    headers={"Authorization": "Bearer sk-synthetic-host-client"},
                    json={
                        "model": "synthetic",
                        "stream": False,
                        "messages": [{"role": "user", "content": label}],
                    },
                )
                if response.status_code == 200:
                    call = response.json()["choices"][0]["message"]["tool_calls"][0]
                    assert call["function"]["name"] == "upload_project_code"
                    assert json.loads(call["function"]["arguments"]) == action(label)
                return response.status_code == 200, {"status": response.status_code}

            for index in range(24):
                await one(index, "allow" if index % 2 == 0 else "block", invoke)
    else:
        async with (
            streamablehttp_client(
                f"http://127.0.0.1:{number}/mcp/",
                headers={"Authorization": "Bearer sk-synthetic-master-key"},
            ) as (read, write, _),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            listed = await session.list_tools()
            assert len(listed.tools) == 1
            name = listed.tools[0].name

            async def invoke(label):
                result = await session.call_tool(name, action(label))
                return not result.isError, {"isError": result.isError}

            for index in range(24):
                await one(index, "allow" if index % 2 == 0 else "block", invoke)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--litellm", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--keychain-helper", type=Path, required=True)
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    frozen = json.loads((CAMPAIGN / "protocol.json").read_text())
    if not args.offline and (
        not args.allow_external or subprocess.check_output(["git", "status", "--porcelain"])
    ):
        parser.error("Explicit egress and a clean committed protocol are required")
    for name, expected in frozen["sha256"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f"Frozen input changed: {name}")
    ledger_path = (
        args.output / "spending.json" if args.offline else ROOT / "artifacts/quality/spending.json"
    )
    args.output.mkdir(parents=True, exist_ok=False)
    with ledger_path.with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not args.offline and sha256(ledger_path) != frozen["starting_ledger_sha256"]:
            raise ValueError("Starting ledger changed")
        if not args.offline:
            credential(args.keychain_helper)
        ledger = Ledger(ledger_path)
        before = ledger_total(ledger)
        bundle = load_bundle(CAMPAIGN / "policies")
        configuration = yaml.safe_load((CAMPAIGN / "config.yaml").read_text())
        config = load_configuration(bundle, configuration)

        class Scripted(MockBackend):
            transport = "openrouter"
            model = "typesafe/jev-1.13"
            accepted_models = ("typesafe/jev-1.13-20260917",)

            async def evaluate(self, payload, **kwargs):
                choice = (
                    "violation"
                    if "public.example.test" in json.dumps(payload["state"]["content"])
                    else "compliant"
                )
                answer = await MockBackend(
                    {
                        k: choice_answer(choice, q["criteria"])
                        for k, q in payload["questions"].items()
                    }
                ).evaluate(payload, **kwargs)
                answer["model"] = self.accepted_models[0]
                return answer

        backend = RestartMeteredBackend(
            Scripted({}) if args.offline else JevBackend(configuration["provider"]),
            ledger,
            {} if args.offline else {int(k): v for k, v in frozen["carried_reservations"].items()},
        )
        original = backend.evaluate
        exchanges = []

        async def bounded(payload, **kwargs):
            if len(exchanges) >= frozen["max_physical_calls"] or (
                ledger_total(ledger) - before + 0.01 > frozen["max_new_cost_usd"]
            ):
                backend.fatal = True
                raise RuntimeError("Campaign ceiling reached")
            exchange = {"payload": copy.deepcopy(payload)}
            exchanges.append(exchange)
            answer = await original(payload, **kwargs)
            exchange["answer"] = copy.deepcopy(answer)
            return answer

        backend.evaluate = bounded
        evaluator = RecordingEvaluator(bundle, config, backend)
        evaluator.records = []
        os.environ["BETA_SERVICE_TOKEN"] = TOKEN
        os.environ["BETA_MCP_TOKEN"] = TOKEN + "-mcp"
        app = create_app(
            evaluator,
            {
                "format": "humanwill.service/1",
                "allow_external_evaluation": True,
                "request_timeout_ms": 20000,
                "max_in_flight": 1,
                "principals": {
                    "gateway": {
                        "connector": "litellm",
                        "token_env": "BETA_SERVICE_TOKEN",
                        "stages": ["model_request", "response", "tool_action"],
                        "inspect_tool_calls": True,
                        "on_protocol_error": "block",
                    },
                    "mcp": {
                        "connector": "native",
                        "token_env": "BETA_MCP_TOKEN",
                        "stages": ["tool_action"],
                        "on_protocol_error": "block",
                    },
                },
            },
        )
        rows = []
        report = {
            "simulated": args.offline,
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "protocol": frozen,
            "rows": rows,
        }

        def save():
            report.update(
                cost_before_usd=before,
                cost_after_usd=ledger_total(ledger),
                new_cost_usd=ledger_total(ledger) - before,
                physical_calls=len(backend.calls),
                accounting_stopped=backend.fatal,
            )
            (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            (args.output / "exchanges.json").write_text(json.dumps(exchanges, indent=2) + "\n")

        effects = []
        try:
            with (
                tempfile.TemporaryDirectory(prefix="hw-beta-") as tmp,
                server(app) as policyport,
                server(tool_model()) as modelport,
                server(tool_server(effects)) as mcpport,
            ):
                for path in ("proposal", "mcp"):
                    for arm in ("baseline", "guarded"):
                        if path == "proposal":
                            conf = gateway_config("litellm", 0, policyport, modelport)
                            conf["litellm_settings"]["callbacks"] = [
                                "humanwill_policies.connectors.litellm_profile.tool_profile"
                            ]
                        else:
                            conf = {
                                "mcp_servers": {
                                    "fixture": {
                                        "url": f"http://127.0.0.1:{mcpport}/mcp",
                                        "transport": "http",
                                    }
                                },
                                "general_settings": {"master_key": "sk-synthetic-master-key"},
                                "guardrails": [
                                    {
                                        "guardrail_name": "humanwill-mcp",
                                        "litellm_params": {
                                            "guardrail": (
                                                "humanwill_policies.connectors.litellm_mcp."
                                                "HumanWillMCPGuardrail"
                                            ),
                                            "mode": "pre_mcp_call",
                                            "default_on": True,
                                            "service_url": f"http://127.0.0.1:{policyport}",
                                            "timeout_ms": 25000,
                                        },
                                    }
                                ],
                            }
                        if arm == "baseline":
                            conf.pop("guardrails")
                        with host(
                            args.litellm.resolve(),
                            conf,
                            Path(tmp),
                            args.output / f"{path}-{arm}.log",
                        ) as number:
                            asyncio.run(
                                measure(path, arm, number, backend, evaluator, effects, rows, save)
                            )
                report["timings"] = {
                    f"{path}/{arm}/{label}": stats(
                        [
                            r["duration_ms"]
                            for r in rows
                            if (r["path"], r["arm"], r["label"]) == (path, arm, label)
                        ]
                    )
                    for path in ("proposal", "mcp")
                    for arm in ("baseline", "guarded")
                    for label in ("allow", "block")
                }
        finally:
            save()
        print(
            json.dumps({k: v for k, v in report.items() if k not in ("rows", "protocol")}, indent=2)
        )


if __name__ == "__main__":
    main()
