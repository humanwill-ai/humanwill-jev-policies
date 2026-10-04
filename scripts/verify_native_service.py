"""Run the actual policy HTTP service with a synthetic backend and native hooks."""

import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_evaluation import ScriptedBackend, answer  # noqa: E402
from test_service import TOKEN, ServiceTests  # noqa: E402
from verify_native_hook import PROFILES  # noqa: E402

from humanwill_policies.hook_events import hook_output  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("Preserve old reports")
    results = []
    for runtime in ("copilot_local", "copilot_cli"):
        fixture = ServiceTests()
        fixture.setUp()
        backend = ScriptedBackend()
        app = fixture.app(runtime, backend=backend)
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="critical", lifespan="off"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started:
                if time.monotonic() > deadline:
                    raise RuntimeError("Service startup failed")
                time.sleep(0.01)
            for _, event, payload in (p for p in PROFILES if p[0] == runtime):
                for blocked in (False, True):
                    backend._answers = json.dumps(
                        {"RULE": answer("violation" if blocked else "compliant")}
                    )
                    command = [
                        str(args.binary.resolve()),
                        "--runtime",
                        runtime,
                        "--event",
                        event,
                        "--url",
                        f"http://127.0.0.1:{port}",
                    ]
                    result = subprocess.run(
                        command,
                        input=json.dumps(payload),
                        text=True,
                        capture_output=True,
                        env=dict(os.environ, HUMANWILL_HOOK_TOKEN=TOKEN),
                        check=True,
                        timeout=5,
                    )
                    assert json.loads(result.stdout) == hook_output(runtime, event, blocked), (
                        result.stderr
                    )
                    diagnostic = json.loads(result.stderr)
                    assert "error" not in diagnostic, diagnostic
                    assert diagnostic["decision"] == ("block" if blocked else "allow")
                    results.append(
                        {"runtime": runtime, "event": event, "block": blocked, "pass": True}
                    )
        finally:
            server.should_exit = True
            thread.join(5)
            sock.close()
            fixture.doCleanups()
    args.report.write_text(
        json.dumps(
            {
                "actual_service": True,
                "scripted_backend": True,
                "provider_calls": 0,
                "results": results,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"{len(results)} actual-service/native-client checks passed; zero provider calls")


if __name__ == "__main__":
    main()
