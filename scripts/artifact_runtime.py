"""Real installed service-process startup/restart/rollback; loopback, no model calls."""

import argparse
import json
import os
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
import yaml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    config = yaml.safe_load((root / "demo/config.yaml").read_text())
    config["provider"] = {
        "transport": "openrouter",
        "model": "synthetic-no-calls",
        "accepted_models": ["synthetic-no-calls"],
        "api_key_env": "UNSET_SYNTHETIC_PROVIDER_KEY",
    }
    config_path = root / "runtime.yaml"
    config_path.write_text(yaml.safe_dump(config))
    service = {
        "format": "humanwill.service/1",
        "allow_external_evaluation": False,
        "principals": {
            "native": {
                "token_env": "ARTIFACT_SMOKE_TOKEN",
                "connector": "native",
                "stages": ["prompt"],
                "on_protocol_error": "block",
            }
        },
    }
    service_path = root / "service.yaml"
    service_path.write_text(yaml.safe_dump(service))
    environment = dict(os.environ)
    environment["ARTIFACT_SMOKE_TOKEN"] = "synthetic-artifact-token-not-a-secret-0000"
    environment.pop("UNSET_SYNTHETIC_PROVIDER_KEY", None)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    command = [
        str(args.cli),
        "serve",
        str(root / "demo"),
        "--config",
        str(config_path),
        "--service-config",
        str(service_path),
        "--port",
        str(port),
    ]

    @contextmanager
    def running():
        with (root / "service.log").open("w") as log:
            process = subprocess.Popen(command, env=environment, cwd=root, stdout=log, stderr=log)
            try:
                yield process
            finally:
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    base = f"http://127.0.0.1:{port}"
    for iteration in range(2):
        with (
            running() as process,
            httpx.Client(base_url=base, trust_env=False, timeout=1) as client,
        ):
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Installed service exited at startup")
                try:
                    if client.get("/readyz").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.05)
            else:
                raise RuntimeError("Installed service failed readiness")
            assert client.get("/healthz").status_code == 200
            request = json.loads((root / "demo/request.json").read_text())
            assert client.post("/v1/evaluate", json=request).status_code == 401
            response = client.post(
                "/v1/evaluate",
                json=request,
                headers={"Authorization": "Bearer " + environment["ARTIFACT_SMOKE_TOKEN"]},
            )
            assert response.status_code == 200
            result = response.json()
            assert result["decision"] == "evaluation_error", result
            assert any(item["code"] == "egress_not_authorized" for item in result["errors"]), result
        if iteration == 0:
            original = config_path.read_text()
            config_path.write_text("format: invalid\n")
            with running() as process:
                assert process.wait(timeout=10) == 2
            config_path.write_text(original)
    print(
        json.dumps(
            {
                "startup": "pass",
                "authentication": "pass",
                "external_egress_disabled": "pass",
                "invalid_configuration_rejected": "pass",
                "restart_previous_configuration": "pass",
            }
        )
    )


if __name__ == "__main__":
    main()
