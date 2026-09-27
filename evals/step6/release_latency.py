"""Real LiteLLM and hook-process latency with live Jev; synthetic content only."""

import argparse
import asyncio
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import JevBackend, MockBackend
from humanwill_policies.runtime import EvidenceContext
from humanwill_policies.service import create_app

from .backends import choice_answer
from .live_support import ConcurrentMeteredBackend, Ledger, credential, ledger_total
from .metrics import percentile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/hosts"))
from gateways import config as gateway_config  # noqa: E402
from support import TOKEN, downstream, dump_yaml, port, server, wait_http  # noqa: E402


def stats(values):
    return {"n": len(values), **{f"p{p}_ms": percentile(values, p / 100) for p in (50, 95, 99)}}


def text_for(index):
    target = (128, 4096, 12000)[index % 3]
    text = "Review this project code locally: def add(a,b): return a+b.\n"
    text += "# Synthetic engineering notes about local test coverage.\n" * 250
    return text[:target]


class RecordingEvaluator(Evaluator):
    async def evaluate(self, *args, **kwargs):
        result = await super().evaluate(*args, **kwargs)
        self.records.append(result)
        return result


def application(configuration, backend):
    bundle = load_bundle(ROOT / "evals/step6/policies-v2")
    evaluator = RecordingEvaluator(bundle, load_configuration(bundle, configuration), backend)
    evaluator.records = []

    async def resolver(principal, event):
        # This fixture owns the approved route, response destination and public
        # classification. No claim or metadata from the caller is promoted.
        values = {
            "destination.coding_route_approved": True,
            "destination.onward_approved": event["stage"] == "response",
            "authorization.destructive_permitted": False,
            "documents.classification": "public",
            "destination.approved": True,
        }
        facts = [
            {
                "field": k,
                "value": v,
                "source": "synthetic-authority",
                "complete": True,
                "subject_ref": event["request_id"],
                "observed_at": datetime.now(UTC).isoformat(),
            }
            for k, v in values.items()
        ]
        return EvidenceContext.from_verified(event, facts)

    stages = {
        "litellm": ["model_request", "response"],
        "copilot_local": ["prompt", "tool_action"],
        "copilot_cli": ["prompt", "tool_action"],
    }
    principals = {}
    for name, allowed in stages.items():
        env = "LATENCY_" + name.upper() + "_TOKEN"
        os.environ[env] = TOKEN + "-" + name
        principals[name] = {
            "connector": name,
            "token_env": env,
            "stages": allowed,
            "on_protocol_error": "block",
        }
    app = create_app(
        evaluator,
        {
            "format": "humanwill.service/1",
            "allow_external_evaluation": True,
            "request_timeout_ms": 18000,
            "max_in_flight": 8,
            "principals": principals,
        },
        evidence_resolver=resolver,
    )
    return app, evaluator


async def requests_to(number, count, concurrency, backend):
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(
        base_url=f"http://127.0.0.1:{number}",
        trust_env=False,
        timeout=45,
        headers={"Authorization": "Bearer sk-synthetic-host-client"},
    ) as client:

        async def one(index):
            async with semaphore:
                if backend.fatal:
                    raise RuntimeError("Live accounting failed; reconcile before continuing")
                start = time.perf_counter()
                response = await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "synthetic",
                        "messages": [{"role": "user", "content": text_for(index)}],
                    },
                )
                return {
                    "index": index,
                    "input_chars": len(text_for(index)),
                    "duration_ms": (time.perf_counter() - start) * 1000,
                    "status": response.status_code,
                }

        return await asyncio.gather(*(one(index) for index in range(count)))


async def hook_requests(number, runtime, count, concurrency, backend):
    semaphore = asyncio.Semaphore(concurrency)
    name = "UserPromptSubmit" if runtime == "copilot_local" else "preToolUse"

    async def one(index):
        async with semaphore:
            if backend.fatal:
                raise RuntimeError("Live accounting failed; reconcile before continuing")
            text = text_for(index)
            body = (
                {"hook_event_name": name, "prompt": text}
                if runtime == "copilot_local"
                else {
                    "toolName": "shell",
                    "toolArgs": {"command": "git diff --stat", "description": text},
                }
            )
            env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
            start = time.perf_counter()
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "humanwill_policies",
                "hook",
                "--runtime",
                runtime,
                "--event",
                name,
                "--url",
                f"http://127.0.0.1:{number}",
                "--token-env",
                "LATENCY_" + runtime.upper() + "_TOKEN",
                "--timeout-ms",
                "20000",
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            output, _ = await asyncio.wait_for(process.communicate(json.dumps(body).encode()), 25)
            return {
                "index": index,
                "input_chars": len(text),
                "duration_ms": (time.perf_counter() - start) * 1000,
                "exit_code": process.returncode,
                "host_output": json.loads(output),
            }

    return await asyncio.gather(*(one(i) for i in range(count)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--litellm", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--keychain-helper", type=Path)
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if not args.allow_external and not args.offline:
        parser.error("Synthetic live evaluation requires --allow-external")
    args.output.mkdir(parents=True, exist_ok=False)
    if not args.offline:
        credential(args.keychain_helper)
    ledger_path = (
        args.output / "offline-spending.json"
        if args.offline
        else ROOT / "artifacts/quality/spending.json"
    )
    with ledger_path.with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger = Ledger(ledger_path)
        cost_before = ledger_total(ledger)
        configuration = yaml.safe_load((ROOT / "evals/step6/config-disclosure-v2.yaml").read_text())
        underlying = (
            MockBackend(
                {
                    pid: choice_answer(
                        "not_applicable", ["applicable", "not_applicable", "insufficient_evidence"]
                    )
                    for pid in ("EVAL-SW-001", "EVAL-PROD-001")
                }
            )
            if args.offline
            else JevBackend(configuration["provider"])
        )
        backend = ConcurrentMeteredBackend(underlying, ledger)
        app, evaluator = application(configuration, backend)
        report = {
            "simulated": args.offline,
            "started_at": datetime.now(UTC).isoformat(),
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"])),
            "configuration": configuration,
            "cost_before_usd": cost_before,
            "workloads": {},
            "limits": [
                "Synthetic workload, not customer production capacity.",
                "Real LiteLLM; controlled local downstream model, live Jev/OpenRouter.",
                "Hook timings include Python startup and HTTP; exclude IDE/CLI scheduling.",
                "Matched adjacent baseline; subtract paired durations, not percentiles.",
                "All policies monitor; decisions are observed, not enforced by this workload.",
            ],
        }

        def save():
            report.update(
                cost_after_usd=ledger_total(ledger),
                new_cost_usd=ledger_total(ledger) - cost_before,
                provider_peak_concurrency=backend.peak_active,
                provider_calls=backend.calls,
                assessments=evaluator.records,
                accounting_stopped=backend.fatal,
            )
            (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")

        try:
            with tempfile.TemporaryDirectory(prefix="humanwill-latency-") as tmp:
                root = Path(tmp)
                with server(app) as policyport, server(downstream([])) as modelport:
                    for enabled in (False, True):
                        hostport = port()
                        conf = gateway_config("litellm", hostport, policyport, modelport)
                        if not enabled:
                            conf.pop("guardrails")
                        dump_yaml(root / "litellm.yaml", conf)
                        env = dict(os.environ)
                        env.pop("PYTHONPATH", None)
                        env.pop("OPENROUTER_API_KEY", None)
                        env.update(
                            HOST_FIXTURE_TOKEN=TOKEN + "-litellm",
                            LITELLM_LOCAL_MODEL_COST_MAP="True",
                            DO_NOT_TRACK="1",
                            DEBUG="false",
                        )
                        with (args.output / f"litellm-{enabled}.log").open("w") as log:
                            process = subprocess.Popen(
                                [
                                    str(args.litellm.resolve()),
                                    "--config",
                                    str(root / "litellm.yaml"),
                                    "--port",
                                    str(hostport),
                                ],
                                cwd=root,
                                env=env,
                                stdout=log,
                                stderr=log,
                            )
                            try:
                                wait_http(f"http://127.0.0.1:{hostport}/health/liveliness", process)
                                for name, count, concurrency in [
                                    ("first", 1, 1),
                                    ("serial", 24, 1),
                                    ("concurrent4", 48, 4),
                                ]:
                                    rows = asyncio.run(
                                        requests_to(hostport, count, concurrency, backend)
                                    )
                                    key = f"litellm-{'guarded' if enabled else 'baseline'}-{name}"
                                    report["workloads"][key] = {
                                        "rows": rows,
                                        "latency": stats([r["duration_ms"] for r in rows]),
                                    }
                                    save()
                                    print(key, report["workloads"][key]["latency"], flush=True)
                            finally:
                                process.terminate()
                                try:
                                    process.wait(timeout=10)
                                except subprocess.TimeoutExpired:
                                    process.kill()
                                    process.wait(timeout=5)
                    for runtime in ("copilot_local", "copilot_cli"):
                        for concurrency in (1, 4):
                            rows = asyncio.run(
                                hook_requests(policyport, runtime, 24, concurrency, backend)
                            )
                            key = f"hook-{runtime}-concurrency{concurrency}"
                            report["workloads"][key] = {
                                "rows": rows,
                                "latency": stats([r["duration_ms"] for r in rows]),
                            }
                            save()
                            print(key, report["workloads"][key]["latency"], flush=True)
        finally:
            save()
            os.environ.pop("OPENROUTER_API_KEY", None)


if __name__ == "__main__":
    main()
