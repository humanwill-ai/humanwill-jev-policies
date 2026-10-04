"""Compare fresh hook processes against a synthetic loopback HTTP service.

No Jev, real policy evaluation, external content, or host/IDE scheduling is involved.
Run Python versions sequentially on an otherwise idle machine. Results include
process startup, imports, normalization, HTTP, reply validation, and host output.
"""

import argparse
import copy
import hashlib
import json
import math
import os
import platform
import random
import statistics
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from humanwill_policies.hook_events import hook, hook_output
from humanwill_policies.json_codec import digest

TOKEN = "synthetic-loopback-benchmark-token-000000000"
PROFILES = {
    "local_prompt": ("copilot_local", "UserPromptSubmit", {"prompt": "Review synthetic code."}),
    "cli_tool": (
        "copilot_cli",
        "preToolUse",
        {"toolName": "bash", "toolArgs": '{"command":"echo synthetic"}'},
    ),
}


def summary(values):
    return {
        "n": len(values),
        "median_ms": round(statistics.median(values), 3),
        "p95_ms": round(sorted(values)[math.ceil(0.95 * len(values)) - 1], 3),
        "min_ms": round(min(values), 3),
        "max_ms": round(max(values), 3),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-python", type=Path, required=True)
    parser.add_argument("--client-python", type=Path, required=True)
    parser.add_argument("--baseline-wheel", type=Path, required=True)
    parser.add_argument("--client-wheel", type=Path, required=True)
    parser.add_argument("--native-binary", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=30)
    args = parser.parse_args()
    if args.samples < 20 or args.report.exists():
        parser.error("Use >=20 samples and a new report path")
    root = Path(__file__).resolve().parents[1]
    fixture = json.loads((root / "tests/fixtures/result-hook.json").read_text())
    observed = []
    failures = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            try:
                assert self.headers["Authorization"] == "Bearer " + TOKEN
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                _, v1, hooks, runtime, event = self.path.split("/")
                assert (v1, hooks) == ("v1", "hooks")
                normalized = hook(payload, runtime, event)
                result = copy.deepcopy(fixture)
                normalized["request_id"] = result["request_id"]
                result["request_sha256"] = digest(normalized)
                result["coverage"] = normalized["coverage"]
                # Scripted reply: this benchmarks transport/validation, not judgment accuracy.
                blocked = "SYNTHETIC_BLOCK" in json.dumps(payload)
                result["decision"] = "block" if blocked else "allow"
                result["enforcement"]["requested"] = result["decision"]
                if blocked:
                    policy = result["policies"][0]
                    policy["judgment"] = "violation"
                    policy["evidence"].update(
                        choice="violation",
                        probabilities={
                            "compliant": 0.0,
                            "violation": 1.0,
                            "insufficient_evidence": 0.0,
                        },
                    )
                data = json.dumps(result).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                observed.append((runtime, event, blocked))
            except Exception as exc:
                failures.append(type(exc).__name__)
                self.send_error(500)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    env = dict(os.environ)
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONOPTIMIZE"):
        env.pop(name, None)
    env.update(PYTHONNOUSERSITE="1", HUMANWILL_HOOK_TOKEN=TOKEN)
    executables = {
        "released": args.baseline_python.absolute().parent / "humanwill-policies",
        "client": args.client_python.absolute().parent / "humanwill-hook",
    }
    if args.native_binary:
        executables["native"] = args.native_binary.resolve()
    rng = random.Random(20261004)
    raw = {}
    warmup = {}
    try:
        with tempfile.TemporaryDirectory(prefix="humanwill-hook-timing-") as cwd:
            versions = {
                label: subprocess.check_output(
                    [str(path), "--version"], env=env, cwd=cwd, text=True
                ).strip()
                for label, path in executables.items()
            }
            for case in [
                "version",
                "local_prompt_allow",
                "local_prompt_block",
                "cli_tool_allow",
                "cli_tool_block",
            ]:
                raw[case] = {label: [] for label in executables}
                warmup[case] = {}
                for sample in range(args.samples + 1):
                    order = list(executables)
                    rng.shuffle(order)
                    for label in order:
                        command = [str(executables[label])]
                        payload = None
                        if case == "version":
                            command += ["--version"]
                        else:
                            profile, decision = case.rsplit("_", 1)
                            runtime, event, payload = copy.deepcopy(PROFILES[profile])
                            blocked = decision == "block"
                            if blocked:
                                if profile == "local_prompt":
                                    payload["prompt"] += " SYNTHETIC_BLOCK"
                                else:
                                    payload["toolArgs"] = '{"command":"echo SYNTHETIC_BLOCK"}'
                            if runtime == "copilot_local":
                                payload["hook_event_name"] = event
                            if label == "released":
                                command += ["hook"]
                            command += [
                                "--runtime",
                                runtime,
                                "--event",
                                event,
                                "--url",
                                f"http://127.0.0.1:{server.server_port}",
                            ]
                        before = len(observed)
                        started = time.perf_counter_ns()
                        result = subprocess.run(
                            command,
                            input=json.dumps(payload) if payload else None,
                            capture_output=True,
                            text=True,
                            cwd=cwd,
                            env=env,
                            timeout=15,
                            check=True,
                        )
                        elapsed = (time.perf_counter_ns() - started) / 1e6
                        if case != "version":
                            assert json.loads(result.stdout) == hook_output(runtime, event, blocked)
                            diagnostic = json.loads(result.stderr)
                            assert "error" not in diagnostic and diagnostic["decision"] == decision
                            assert len(observed) == before + 1 and not failures
                        else:
                            assert result.stdout.strip() == versions[label]
                        if sample == 0:
                            warmup[case][label] = elapsed
                        else:
                            raw[case][label].append(elapsed)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    report = {
        "scope": (
            "Fresh installed console process to validated hook output; "
            "synthetic loopback replies, no Jev/IDE/TLS"
        ),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "python": subprocess.check_output(
            [str(args.client_python.absolute()), "--version"], text=True
        ).strip(),
        "versions": versions,
        "wheel_sha256": {
            label: hashlib.sha256(path.read_bytes()).hexdigest()
            for label, path in {
                "released": args.baseline_wheel,
                "client": args.client_wheel,
            }.items()
        },
        "method": (
            "Seeded randomized order within paired rounds; one excluded warmup per case/client; "
            "warm filesystem cache; sequential processes"
        ),
        "samples_per_cell": args.samples,
        "http_calls": len(observed),
        "provider_calls": 0,
        "native_sha256": (
            hashlib.sha256(args.native_binary.read_bytes()).hexdigest()
            if args.native_binary
            else None
        ),
        "summary": {
            case: {
                **{label: summary(values) for label, values in arms.items()},
                "paired_saving_ms": summary(
                    [old - new for old, new in zip(arms["released"], arms["client"], strict=True)]
                ),
                **(
                    {
                        "native_vs_client_saving_ms": summary(
                            [
                                old - new
                                for old, new in zip(arms["client"], arms["native"], strict=True)
                            ]
                        )
                    }
                    if "native" in arms
                    else {}
                ),
            }
            for case, arms in raw.items()
        },
        "excluded_warmup_ms": warmup,
        "raw_ms": raw,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
