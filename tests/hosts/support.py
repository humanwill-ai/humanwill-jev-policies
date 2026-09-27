"""Synthetic local endpoints for REAL host-process tests; never a semantic accuracy test."""

import asyncio
import json
import os
import socket
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
import uvicorn
import yaml
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import JevBackend
from humanwill_policies.service import create_app

TOKEN = "synthetic-host-test-token-000000000000"


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def server(app):
    number = port()
    runner = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=number, log_level="error", access_log=False)
    )
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    for _ in range(200):
        if runner.started:
            break
        time.sleep(0.02)
    else:
        raise RuntimeError("Fixture server failed to start")
    try:
        yield number
    finally:
        runner.should_exit = True
        thread.join(5)
        assert not thread.is_alive()


def policy_app(root, connector, mode="enforce", captures=None):
    root.mkdir(parents=True, exist_ok=True)
    (root / "policies.md").write_text(
        '---\nkind: collection\nid: tests\nversion: "1"\nincludes: [rule.md]\n'
        "---\nSynthetic tests.\n"
    )
    (root / "rule.md").write_text(
        '---\nkind: policy\nid: TEST\nversion: "1"\ntitle: Synthetic fixture\n'
        "stages: [prompt, model_request, response, tool_action]\n---\n"
        "Block the synthetic HW_DENY marker."
        " This is not a calibrated real policy.\n"
    )
    provider = {
        "transport": "openrouter",
        "model": "synthetic-fixture",
        "accepted_models": ["synthetic-fixture"],
        "api_key_env": "HOST_FIXTURE_PROVIDER_KEY",
    }
    config = {
        "format": "humanwill.config/2",
        "metadata": {"enabled": False},
        "provider": provider,
        "evaluation": {"timeout_ms": 300},
        "policies": {
            "TEST": {
                "enabled": True,
                "mode": mode,
                "strategy": "semantic",
                "evaluation_profile": {
                    "id": "synthetic-only",
                    "model": provider["model"],
                    "dataset_sha256": "0" * 64,
                    "min_confidence": 0.9,
                },
            }
        },
    }
    if mode == "monitor":
        config["policies"]["TEST"].pop("evaluation_profile")

    async def judge(request):
        payload = json.loads(request.content)
        if captures is not None:
            captures.append(payload)
        state = json.dumps(payload["state"])
        if "HW_TIMEOUT" in state:
            await asyncio.sleep(2)
        if "HW_ERROR" in state:
            return httpx.Response(500, json={"error": "synthetic"})
        choice = "violation" if "HW_DENY" in state else "compliant"
        answer = {
            "type": "choice",
            "choice": choice,
            "confidence": 1.0,
            "probabilities": {
                k: float(k == choice) for k in ("compliant", "violation", "insufficient_evidence")
            },
        }
        return httpx.Response(
            200,
            json={
                "model": provider["model"],
                "usage": {},
                "answers": {k: answer for k in payload["questions"]},
            },
        )

    os.environ["HOST_FIXTURE_PROVIDER_KEY"] = "synthetic-never-sent-to-network"
    os.environ["HOST_FIXTURE_TOKEN"] = TOKEN
    bundle = load_bundle(root)
    engine = Evaluator(
        bundle,
        load_configuration(bundle, config),
        JevBackend(provider, http_transport=httpx.MockTransport(judge)),
    )
    settings = {
        "format": "humanwill.service/1",
        "allow_external_evaluation": True,
        "request_timeout_ms": 1000,
        "principals": {
            "fixture": {
                "token_env": "HOST_FIXTURE_TOKEN",
                "connector": connector,
                "stages": ["model_request", "response"]
                if connector in ("litellm", "agentgateway")
                else ["prompt", "tool_action"],
                "on_protocol_error": "block",
            }
        },
    }
    app = create_app(engine, settings)
    return app


def downstream(calls):
    async def completion(request):
        body = await request.json()
        calls.append(body)
        text = (
            "HW_DENY_RESPONSE"
            if "MAKE_BAD_OUTPUT" in json.dumps(body)
            else "SYNTHETIC_ALLOWED_RESPONSE"
        )
        return JSONResponse(
            {
                "id": "chatcmpl-synthetic",
                "object": "chat.completion",
                "created": 1,
                "model": "synthetic",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        )

    return Starlette(
        routes=[
            Route("/v1/chat/completions", completion, methods=["POST"]),
            Route("/chat/completions", completion, methods=["POST"]),
        ]
    )


def wait_http(url, process):
    for _ in range(300):
        if process.poll() is not None:
            raise RuntimeError("Host exited during startup; inspect local log")
        try:
            httpx.get(url, timeout=0.2, trust_env=False)
            return
        except httpx.TransportError:
            time.sleep(0.1)
    raise RuntimeError("Host did not start")


def dump_yaml(path, body):
    Path(path).write_text(yaml.safe_dump(body, sort_keys=False))
