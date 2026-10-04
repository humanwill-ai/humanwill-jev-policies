"""Synthetic black-box native/Python contract comparison; no provider calls."""

import argparse
import copy
import hashlib
import json
import math
import os
import random
import ssl
import struct
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from humanwill_policies.hook_events import hook, hook_output
from humanwill_policies.json_codec import canonical, digest

TOKEN = "synthetic-native-hook-test-token-000000000000"
ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "tests/fixtures/result-hook.json").read_text())
PROFILES = [
    (
        "copilot_local",
        "UserPromptSubmit",
        {"hook_event_name": "UserPromptSubmit", "prompt": "Review local code."},
    ),
    (
        "copilot_local",
        "PreToolUse",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "bash",
            "tool_input": {"command": "echo synthetic"},
        },
    ),
    ("copilot_cli", "userPromptSubmitted", {"prompt": "Review local code."}),
    ("copilot_cli", "preToolUse", {"toolName": "bash", "toolArgs": '{"command":"echo synthetic"}'}),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--probe", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("Preserve previous reports")
    binary, probe = args.binary.resolve(), args.probe.resolve()
    env = dict(os.environ, HUMANWILL_HOOK_TOKEN=TOKEN)
    # Both proxy bypass and deterministic dependency isolation are tested.
    env.update(
        HTTP_PROXY="http://127.0.0.1:1",
        HTTPS_PROXY="http://127.0.0.1:1",
        ALL_PROXY="http://127.0.0.1:1",
    )
    checks = []
    observed = []
    state = {}
    server_errors = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def handle(self):
            try:
                super().handle()
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                pass  # Expected when the client rejects the TLS certificate or times out.

        def do_POST(self):
            try:
                data = self.rfile.read(int(self.headers["Content-Length"]))
                payload = json.loads(data)
                assert self.headers["Authorization"] == "Bearer " + TOKEN
                assert all(k not in payload for k in ("cwd", "transcript_path", "extra"))
                _, _, _, runtime, event = self.path.split("/")
                observed.append(payload)
                result = copy.deepcopy(FIXTURE)
                normalized = hook(payload, runtime, event)
                normalized["request_id"] = result["request_id"]
                result["request_sha256"] = digest(normalized)
                result["coverage"] = normalized["coverage"]
                if state.get("version", 2) != 2:
                    version = state["version"]
                    result.update(
                        format=f"humanwill.result/{version}",
                        rubric="humanwill.choice/2" if version == 3 else "humanwill.policy/1",
                    )
                if state.get("block"):
                    result["decision"] = "block"
                    result["enforcement"]["requested"] = "block"
                if state.get("mutate"):
                    state["mutate"](result)
                body = state.get("raw", json.dumps(result).encode())
                time.sleep(state.get("delay", 0))
                self.send_response(state.get("status", 200))
                for k, v in state.get("headers", {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            except Exception as exc:
                server_errors.append(repr(exc))
                self.send_error(500)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"

    def run(
        name,
        *,
        profile=PROFILES[0],
        options=None,
        state_value=None,
        error=False,
        block=False,
        payload=None,
        url=origin,
    ):
        state.clear()
        state.update(state_value or {})
        runtime, event, source = profile
        raw = (
            payload
            if isinstance(payload, bytes)
            else json.dumps(payload if payload is not None else source).encode()
        )
        command = [
            str(binary),
            "--runtime",
            runtime,
            "--event",
            event,
            "--url",
            url,
            *(options or []),
        ]
        start = time.monotonic()
        process = subprocess.run(command, input=raw, capture_output=True, env=env, timeout=5)
        elapsed = time.monotonic() - start
        assert process.returncode == 0, (name, process.returncode, process.stderr)
        output, diagnostic = json.loads(process.stdout), json.loads(process.stderr)
        assert output == hook_output(runtime, event, block), (name, output, diagnostic)
        assert ("error" in diagnostic) == error, (name, diagnostic)
        assert "DO_NOT_LOG" not in process.stderr.decode(), name
        checks.append(name)
        return elapsed

    try:
        for profile in PROFILES:
            for version in (2, 3, 4):
                for block in (False, True):
                    run(
                        f"{profile[0]}/{profile[1]}/v{version}/{block}",
                        profile=profile,
                        state_value={"version": version, "block": block},
                        block=block,
                    )
            run(
                "minimize-" + profile[1],
                profile=profile,
                payload={
                    **profile[2],
                    "cwd": "/DO_NOT_LOG",
                    "transcript_path": "/DO_NOT_LOG",
                    "extra": "DO_NOT_LOG",
                },
            )
        for args_value in [
            {"unicode": "café 中文 😀 \x00", "😀": "🙂", "a": '\n\\"', "\ue000": 1, "𐀀": 2},
            {
                "numbers": [
                    0,
                    -0.0,
                    1.0,
                    1e-4,
                    1e-5,
                    1e15,
                    1e16,
                    1e20,
                    1e-308,
                    1.7976931348623157e308,
                    9007199254740993,
                    10**100,
                ]
            },
            {"a": [{"nested": True, "null": None, "empty": []}]},
        ]:
            run(
                "unicode/numeric-binding",
                profile=PROFILES[1],
                payload={**PROFILES[1][2], "tool_input": args_value},
            )
            run(
                "cli-string-binding",
                profile=PROFILES[3],
                payload={**PROFILES[3][2], "toolArgs": json.dumps(args_value)},
            )
        mutations = {
            "wrong_digest": lambda r: r.update(request_sha256="0" * 64),
            "wrong_coverage": lambda r: r["coverage"].update(complete=False),
            "omitted": lambda r: r["coverage"].update(omitted=["unknown"]),
            "simulated": lambda r: r.update(simulated=True),
            "unknown_format": lambda r: r.update(format="humanwill.result/99"),
            "unknown_action": lambda r: r["enforcement"].update(requested="review"),
            "extra_field": lambda r: r.update(extra=True),
            "extra_nested": lambda r: r["policies"][0]["evidence"].update(extra=True),
            "duplicate_policy": lambda r: r["policies"].append(copy.deepcopy(r["policies"][0])),
            "missing_field": lambda r: r.pop("evaluation"),
            "bad_confidence": lambda r: r["policies"][0]["evidence"].update(confidence=1.01),
            "bad_number_type": lambda r: r.update(duration_ms=True),
            "bad_identifier": lambda r: r.update(request_id="invalid id"),
            "wrong_rubric": lambda r: r.update(rubric="unknown"),
            "policy_array_bound": lambda r: r.update(policies=r["policies"] * 501),
            "bad_batch": lambda r: r["evaluation"]["batches"][0].update(input_tokens=-1),
            "bad_enforcement_type": lambda r: r["enforcement"].update(requested=True),
            "invalid_followup": lambda r: r.update(policy_assessment={}),
        }
        for name, mutate in mutations.items():
            run(name, state_value={"mutate": mutate}, error=True, block=True)
            run(
                name + "/monitor",
                state_value={"mutate": mutate},
                options=["--on-error", "allow_monitor"],
                error=True,
            )
        for raw in (
            b'{"a":1,"a":2}',
            b'{"a":NaN}',
            b'{"a":1e999}',
            b"[]",
            b"{}garbage",
            b"\xff",
            b" " * 262145,
        ):
            run("invalid_reply", state_value={"raw": raw}, error=True, block=True)
        for raw in (
            b'{"prompt":"a","prompt":"b"}',
            b'{"a":NaN}',
            b'{"a":1e999}',
            b"[]",
            b"{}garbage",
            b'{"a":"\xff"}',
            b" " * 262145,
            b'{"a":' + b"[" * 26 + b"0" + b"]" * 26 + b"}",
        ):
            before = len(observed)
            run("invalid_input", payload=raw, error=True, block=True)
            assert len(observed) == before
        for url in (
            "http://remote.example.test",
            "https://user:pass@example.test",
            "https://example.test/path",
            "https://example.test?x=1",
            "https://example.test#x",
            "file:///tmp/x",
        ):
            before = len(observed)
            run("unsafe_url", url=url, error=True, block=True)
            assert len(observed) == before
        for status in (302, 401, 503):
            before = len(observed)
            run(
                f"http-{status}",
                state_value={"status": status, "headers": {"Location": origin}},
                error=True,
                block=True,
            )
            assert len(observed) == before + 1
        run(
            "compression",
            state_value={"headers": {"Content-Encoding": "gzip"}},
            error=True,
            block=True,
        )
        for profile in PROFILES:
            elapsed = run(
                "timeout-" + profile[1],
                profile=profile,
                options=["--timeout-ms", "100"],
                state_value={"delay": 0.25},
                error=True,
                block=True,
            )
            assert elapsed < 0.8
            time.sleep(0.2)
        run(
            "missing-token",
            options=["--token-env", "HUMANWILL_NONEXISTENT_TEST_TOKEN"],
            error=True,
            block=True,
        )
        run("unavailable", url="http://127.0.0.1:1", error=True, block=True)
        assert not server_errors, server_errors

        # A self-signed loopback TLS endpoint must be rejected before any HTTP request.
        with tempfile.TemporaryDirectory(prefix="humanwill-native-tls-") as directory:
            cert, key = Path(directory) / "cert.pem", Path(directory) / "key.pem"
            subprocess.run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-keyout",
                    str(key),
                    "-out",
                    str(cert),
                    "-days",
                    "1",
                    "-subj",
                    "/CN=localhost",
                    "-addext",
                    "subjectAltName=DNS:localhost,IP:127.0.0.1",
                ],
                check=True,
                capture_output=True,
            )
            tls = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            tls.socket = context.wrap_socket(tls.socket, server_side=True)
            t = threading.Thread(target=tls.serve_forever, daemon=True)
            t.start()
            before = len(observed)
            try:
                run(
                    "untrusted-tls",
                    url=f"https://localhost:{tls.server_port}",
                    error=True,
                    block=True,
                )
                assert len(observed) == before
                run(
                    "trusted-tls-explicit-ca",
                    url=f"https://localhost:{tls.server_port}",
                    options=["--ca-file", str(cert)],
                )
                assert len(observed) == before + 1
            finally:
                tls.shutdown()
                tls.server_close()
                t.join()

        assessment = {
            "profile": "q05_stage_aware",
            "status": "completed",
            "batch_index": 1,
            "eligible": ["RULE"],
            "accepted": ["RULE"],
            "rejected": {},
            "primary_answers": {},
            "secondary_answers": {},
            "error": None,
        }
        run(
            "valid-result4-followup",
            state_value={
                "version": 4,
                "mutate": lambda r: r.update(policy_assessment=assessment),
            },
        )
        run(
            "simulated-monitor",
            state_value={
                "mutate": lambda r: (
                    r.update(simulated=True),
                    r["enforcement"].update(requested="none"),
                ),
            },
        )
        run(
            "evaluation-error-monitor",
            state_value={
                "mutate": lambda r: (
                    r.update(decision="evaluation_error"),
                    r["enforcement"].update(requested="none"),
                ),
            },
        )

        # Deterministic malformed-input smoke fuzzing; especially useful under ASan/UBSan.
        fuzz_rng = random.Random(20261005)
        base = json.dumps(PROFILES[0][2]).encode()
        for index in range(200):
            raw = bytearray(base)
            for _ in range(fuzz_rng.randrange(1, 8)):
                position = fuzz_rng.randrange(len(raw))
                raw[position] = fuzz_rng.randrange(256)
            process = subprocess.run(
                [
                    str(binary),
                    "--runtime",
                    "copilot_local",
                    "--event",
                    "UserPromptSubmit",
                    "--url",
                    origin,
                ],
                input=bytes(raw),
                capture_output=True,
                env=env,
                timeout=5,
            )
            assert process.returncode == 0, ("fuzz", index, process.stderr)
            json.loads(process.stdout)
            json.loads(process.stderr)  # Sanitizer output would fail this check.
        checks.append("200-malformed-input-mutations-no-crashes")

        # 10,000 finite random doubles plus boundary values; one process per batch.
        rng = random.Random(20261004)
        floats = [0.0, -0.0, 1e-4, 1e-5, 1e15, 1e16, 5e-324]
        while len(floats) < 10000:
            value = struct.unpack("d", rng.randbytes(8))[0]
            if math.isfinite(value):
                floats.append(value)
        for i in range(0, len(floats), 1000):
            value = {"values": floats[i : i + 1000]}
            process = subprocess.run(
                [str(probe)], input=json.dumps(value).encode(), capture_output=True, check=True
            )
            assert process.stdout.decode().strip() == canonical(value), ("canonical floats", i)
        checks.append("10000-finite-double-canonicalization")
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    report = {
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "checks": checks,
        "passed": len(checks),
        "http_calls": len(observed),
        "provider_calls": 0,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": len(checks), "http_calls": len(observed), "provider_calls": 0}))


if __name__ == "__main__":
    main()
