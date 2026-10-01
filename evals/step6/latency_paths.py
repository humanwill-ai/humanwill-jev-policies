"""Frozen serial LiteLLM path comparison; real Jev, synthetic downstream only."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from humanwill_policies.providers import JevBackend, MockBackend

from .backends import choice_answer
from .live_support import Ledger, credential, ledger_total
from .preview_latency import (
    ROOT,
    TOKEN,
    application,
    dump_yaml,
    gateway_config,
    port,
    server,
    stats,
    wait_http,
)
from .question_context import sha256
from .restart_accounting import RestartMeteredBackend

CAMPAIGN = ROOT / "evals/step6/latency-paths-v1"


def downstream(response_text):
    async def complete(request):
        await request.json()
        return JSONResponse(
            {
                "id": "chatcmpl-latency-paths",
                "object": "chat.completion",
                "created": 1,
                "model": "synthetic",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": response_text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        )

    return Starlette(routes=[Route("/v1/chat/completions", complete, methods=["POST"])])


def prompt_text(workload, index):
    target = (128, 4096, 12000)[index % 3]
    text = workload["prompt"] + "\n"
    text += "# Synthetic local code review notes about unit test coverage.\n" * 220
    return text[:target]


async def measure(number, workload, backend, evaluator, count, save):
    rows = []
    async with httpx.AsyncClient(trust_env=False, timeout=45) as client:
        for index in range(count):
            if backend.fatal:
                raise RuntimeError("Accounting stopped; reconcile before continuing")
            call_start, assessment_start = len(backend.calls), len(evaluator.records)
            prompt = prompt_text(workload, index)
            start = time.perf_counter()
            response = await client.post(
                f"http://127.0.0.1:{number}/v1/chat/completions",
                headers={"Authorization": "Bearer sk-synthetic-host-client"},
                json={"model": "synthetic", "messages": [{"role": "user", "content": prompt}]},
            )
            duration = (time.perf_counter() - start) * 1000
            calls = copy.deepcopy(backend.calls[call_start:])
            assessments = copy.deepcopy(evaluator.records[assessment_start:])
            row = {
                "index": index,
                "cold": index == 0,
                "input_chars": len(prompt),
                "duration_ms": duration,
                "status": response.status_code,
                "provider_calls": calls,
                "assessments": assessments,
            }
            rows.append(row)
            save(row)
            response.raise_for_status()
            assert response.json()["choices"][0]["message"]["content"] == workload["response"]
            if backend.fatal:
                raise RuntimeError("New accounting failure; stopping campaign")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--litellm", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--keychain-helper", type=Path)
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    frozen = json.loads((CAMPAIGN / "protocol.json").read_text())
    for name, expected in frozen["sha256"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f"Frozen campaign input changed: {name}")
    if not args.offline:
        if not args.allow_external:
            parser.error("Synthetic live calls require --allow-external")
        if subprocess.check_output(["git", "status", "--porcelain"]):
            parser.error("Commit the frozen experiment first")
    args.output.mkdir(parents=True, exist_ok=False)
    ledger_path = (
        args.output / "spending.json" if args.offline else ROOT / "artifacts/quality/spending.json"
    )
    with ledger_path.with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not args.offline:
            if sha256(ledger_path) != frozen["starting_ledger_sha256"]:
                raise ValueError("Starting ledger changed")
            credential(args.keychain_helper)
        ledger = Ledger(ledger_path)
        configuration = yaml.safe_load(
            (ROOT / "evals/step6/direct-policy-v2/config.yaml").read_text()
        )
        configuration["policy_assessment"] = "q05_stage_aware"
        underlying = (
            MockBackend(
                {
                    pid: choice_answer(
                        "not_applicable", ["applicable", "not_applicable", "insufficient_evidence"]
                    )
                    for pid in ("EVAL-SW-001", "EVAL-PROD-001", "EVAL-SRC-001")
                }
            )
            if args.offline
            else JevBackend(configuration["provider"])
        )
        backend = RestartMeteredBackend(
            underlying,
            ledger,
            {} if args.offline else {int(k): v for k, v in frozen["carried_reservations"].items()},
        )
        original = backend.evaluate
        attempts = 0
        exchanges = []

        async def bounded(payload, **kwargs):
            nonlocal attempts
            if attempts >= frozen["max_physical_calls"]:
                backend.fatal = True
                raise RuntimeError("Frozen call ceiling reached")
            attempts += 1
            record = {"payload": copy.deepcopy(payload)}
            exchanges.append(record)
            answer = await original(payload, **kwargs)
            record["answer"] = copy.deepcopy(answer)
            return answer

        backend.evaluate = bounded
        app, evaluator = application(configuration, backend)
        before = ledger_total(ledger)
        report = {
            "started_at": datetime.now(UTC).isoformat(),
            "simulated": args.offline,
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "configuration": configuration,
            "protocol": frozen,
            "cost_before_usd": before,
            "groups": {},
        }

        def save():
            report.update(
                cost_after_usd=ledger_total(ledger),
                new_cost_usd=ledger_total(ledger) - before,
                physical_calls=len(backend.calls),
                accounting_stopped=backend.fatal,
            )
            (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            (args.output / "exchanges.json").write_text(json.dumps(exchanges, indent=2) + "\n")

        workloads = json.loads((CAMPAIGN / "workloads.json").read_text())
        try:
            with (
                tempfile.TemporaryDirectory(prefix="hw-latency-paths-") as tmp,
                server(app) as policyport,
            ):
                for workload in workloads:
                    with server(downstream(workload["response"])) as modelport:
                        for arm in workload["arm_order"]:
                            key = workload["id"] + "/" + arm
                            rows = report["groups"][key] = []
                            hostport = port()
                            conf = gateway_config("litellm", hostport, policyport, modelport)
                            if arm == "baseline":
                                conf.pop("guardrails")
                            elif arm == "prompt_only":
                                conf["guardrails"][0]["litellm_params"]["mode"] = ["pre_call"]
                            else:
                                assert arm == "prompt_and_response"
                            dump_yaml(Path(tmp) / "litellm.yaml", conf)
                            env = dict(os.environ)
                            env.pop("PYTHONPATH", None)
                            env.pop("OPENROUTER_API_KEY", None)
                            env.update(
                                HOST_FIXTURE_TOKEN=TOKEN + "-litellm",
                                LITELLM_LOCAL_MODEL_COST_MAP="True",
                                DO_NOT_TRACK="1",
                                DEBUG="false",
                            )
                            with (args.output / (key.replace("/", "-") + ".log")).open("w") as log:
                                process = subprocess.Popen(
                                    [
                                        str(args.litellm.resolve()),
                                        "--config",
                                        str(Path(tmp) / "litellm.yaml"),
                                        "--port",
                                        str(hostport),
                                    ],
                                    cwd=tmp,
                                    env=env,
                                    stdout=log,
                                    stderr=log,
                                )
                                try:
                                    wait_http(
                                        f"http://127.0.0.1:{hostport}/health/liveliness", process
                                    )

                                    def record(row, target=rows):
                                        target.append(row)
                                        save()

                                    asyncio.run(
                                        measure(
                                            hostport,
                                            workload,
                                            backend,
                                            evaluator,
                                            2 if args.offline else frozen["requests_per_arm"],
                                            record,
                                        )
                                    )
                                    print(
                                        key,
                                        stats([r["duration_ms"] for r in rows if not r["cold"]]),
                                        flush=True,
                                    )
                                finally:
                                    process.terminate()
                                    try:
                                        process.wait(timeout=10)
                                    except subprocess.TimeoutExpired:
                                        process.kill()
                                        process.wait(timeout=5)
        finally:
            save()
            os.environ.pop("OPENROUTER_API_KEY", None)


if __name__ == "__main__":
    main()
