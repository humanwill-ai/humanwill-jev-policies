"""Loopback load/failure exercise with a synthetic provider; no external calls."""

import argparse
import asyncio
import json
import math
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path

import httpx
from support import TOKEN, policy_app, server

from humanwill_policies import load_bundle
from humanwill_policies.errors import PolicyError


def event(text="ordinary synthetic work"):
    return {
        "format": "humanwill.request/1",
        "request_id": "operations-fixture",
        "stage": "prompt",
        "content": [{"id": "text", "kind": "text", "role": "user", "text": text}],
        "coverage": {"complete": True, "inspected": ["text"], "omitted": []},
    }


def distribution(values):
    values = sorted(values)
    return {
        "count": len(values),
        **{
            f"p{p}_ms": round(values[math.ceil(len(values) * p / 100) - 1], 3) for p in (50, 95, 99)
        },
    }


async def exercise(number):
    async with httpx.AsyncClient(
        base_url=f"http://127.0.0.1:{number}",
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=5,
        trust_env=False,
        limits=httpx.Limits(max_connections=40),
    ) as client:

        async def assess(text="ordinary synthetic work"):
            start = time.perf_counter()
            response = await client.post("/v1/evaluate", json=event(text))
            return response, (time.perf_counter() - start) * 1000

        cold, cold_ms = await assess()
        assert cold.status_code == 200 and cold.json()["decision"] == "allow"
        initial_hash = cold.json()["bundle_sha256"]
        warm = [await assess() for _ in range(100)]
        assert all(r.status_code == 200 and r.json()["decision"] == "allow" for r, _ in warm)
        burst = []
        for _ in range(10):
            burst.extend(await asyncio.gather(*(assess() for _ in range(8))))
        assert all(r.status_code == 200 and r.json()["decision"] == "allow" for r, _ in burst)
        failures = await asyncio.gather(*(assess("HW_TIMEOUT") for _ in range(32)))
        outcomes = Counter()
        for response, _ in failures:
            body = response.json()
            if response.status_code == 200:
                assert body["decision"] == "evaluation_error"
                assert body["enforcement"]["requested"] == "block"
                outcomes["evaluation_error_fail_closed"] += 1
            else:
                assert body["error"] == "service_overloaded", body
                outcomes["service_overloaded"] += 1
        assert outcomes["evaluation_error_fail_closed"]
        # Hold all HTTP service slots while reading bodies, independently of
        # the evaluator's smaller concurrency limit and immediate rejections.
        release = asyncio.Event()
        started = asyncio.Queue()

        async def slow_body():
            raw = json.dumps(event()).encode()
            yield raw[:1]
            await started.put(True)
            await release.wait()
            yield raw[1:]

        held = [
            asyncio.create_task(
                client.post(
                    "/v1/evaluate",
                    content=slow_body(),
                    headers={"Content-Type": "application/json"},
                )
            )
            for _ in range(8)
        ]
        for _ in held:
            await started.get()
        await asyncio.sleep(0.1)
        try:
            overloaded, _ = await assess()
            assert overloaded.json().get("error") == "service_overloaded"
        finally:
            release.set()
            await asyncio.gather(*held)
        for marker in ("HW_ERROR", "HW_DENY"):
            response, _ = await assess(marker)
            assert response.status_code == 200
            assert response.json()["enforcement"]["requested"] == "block"
        recovery, _ = await assess()
        assert recovery.json()["decision"] == "allow"
        assert (await client.get("/readyz")).status_code == 200
        unauthorized = await client.post(
            "/v1/evaluate", json=event(), headers={"Authorization": "Bearer invalid"}
        )
        assert unauthorized.status_code == 401
        return {
            "first_request_ms": round(cold_ms, 3),
            "warm_serial": distribution([ms for _, ms in warm]),
            "concurrency_8": distribution([ms for _, ms in burst]),
            "timeout_burst_32": {
                "outcomes": dict(outcomes),
                "latency": distribution([ms for _, ms in failures]),
            },
            "provider_error_denied": True,
            "violation_denied": True,
            "post_failure_recovery": True,
            "service_slot_saturation_rejected": True,
            "authentication_rejected": True,
            "bundle_sha256": initial_hash,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/operations/service.json"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="humanwill-operations-") as tmp:
        root = Path(tmp)
        app = policy_app(root, "native")
        with server(app) as number:
            report = asyncio.run(exercise(number))
            original = (root / "rule.md").read_text()
            (root / "rule.md").write_text("invalid policy front matter")
            try:
                load_bundle(root)
            except PolicyError:
                report["invalid_bundle_rejected"] = True
            else:
                raise AssertionError("Invalid bundle accepted")
            # Running service retains the validated snapshot until restart.
            response = httpx.post(
                f"http://127.0.0.1:{number}/v1/evaluate",
                json=event(),
                headers={"Authorization": f"Bearer {TOKEN}"},
                trust_env=False,
            )
            assert response.json()["bundle_sha256"] == report["bundle_sha256"]
            report["running_snapshot_immutable"] = True
            (root / "rule.md").write_text(original)
        assert load_bundle(root).sha256 == report["bundle_sha256"]
        with server(policy_app(root, "native")) as number:
            response = httpx.post(
                f"http://127.0.0.1:{number}/v1/evaluate",
                json=event(),
                headers={"Authorization": f"Bearer {TOKEN}"},
                trust_env=False,
            )
            assert response.json()["decision"] == "allow"
            assert response.json()["bundle_sha256"] == report["bundle_sha256"]
        report["restored_bundle_restart"] = True
    report.update(
        source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        working_tree_dirty=bool(subprocess.check_output(["git", "status", "--porcelain"])),
        provider="in-process synthetic HTTP transport; zero provider network calls",
        measurement="Loopback HTTP to Uvicorn; includes client/network/service overhead",
        limits="Not Jev/gateway latency, sustained capacity, or production load evidence.",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
