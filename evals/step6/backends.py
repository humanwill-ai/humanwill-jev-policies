"""Evaluation-only alternatives and a conservative persisted API spending ledger."""

import json
import math
import os
import re
import time
from pathlib import Path

import httpx

from humanwill_policies.errors import PolicyError
from humanwill_policies.providers import decode_json
from humanwill_policies.serialization import canonical

CHAT_MODEL = "google/gemini-2.5-flash-lite"
JEV_MODEL = "typesafe/jev-1.13"
JEV_RETURNED = "typesafe/jev-1.13-20260917"
PRIOR_SPEND = 0.000024696
RESERVE = 0.01


def choice_answer(choice, labels):
    # Deterministic baseline encoding, NOT a calibrated probability estimate.
    return {
        "type": "choice",
        "choice": choice,
        "confidence": 1.0,
        "probabilities": {label: float(label == choice) for label in labels},
    }


class KeywordBackend:
    transport = "mock"
    model = "keyword-v1"
    accepted_models = ("keyword-v1",)

    async def evaluate(self, payload, **kwargs):
        text = canonical(payload["state"]["content"]).lower()
        answers = {}
        for key, question in payload["questions"].items():
            pattern = (
                r"project|src/|architecture|specification|patch"
                if key == "EVAL-SW-001"
                else r"\brm\b|\bdrop\b|\btruncate\b|\bdelete\b|\bstop\b|rmtree"
            )
            choice = "applicable" if re.search(pattern, text) else "not_applicable"
            answers[key] = choice_answer(choice, question["criteria"])
        return {
            "model": self.model,
            "answers": answers,
            "usage": {"input_tokens": 0, "output_tokens": 0, "cost": 0},
        }


class Ledger:
    """Caller holds one process lock for the run. Reserve before network activity.

    Failed/interrupted or unpriced calls retain the reservation and halt further
    live work. A reservation is conservative accounting, not a provider-side cap.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.data = json.loads(self.path.read_text())
        else:
            self.data = {"cap_usd": 5.0, "prior_smoke_usd": PRIOR_SPEND, "calls": []}
            self.save()
        if self.data["cap_usd"] != 5.0 or self.data["prior_smoke_usd"] != PRIOR_SPEND:
            raise ValueError("Unexpected budget ledger; reconcile before further calls")

    def save(self):
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.data, indent=2) + "\n")
        temp.replace(self.path)

    def reserve(self, model):
        if any(
            c["cost_usd"] is None or c["cost_usd"] > c["reserved_usd"] for c in self.data["calls"]
        ):
            raise PolicyError("unreconciled_cost", "Reconcile unknown charges before more calls")
        spent = self.data["prior_smoke_usd"] + sum(c["cost_usd"] for c in self.data["calls"])
        if spent + RESERVE > self.data["cap_usd"]:
            raise PolicyError("budget_exhausted", "Insufficient authorized budget")
        self.data["calls"].append(
            {"model": model, "started_unix": time.time(), "reserved_usd": RESERVE, "cost_usd": None}
        )
        self.save()
        return len(self.data["calls"]) - 1

    def settle(self, index, cost):
        if type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0:
            raise PolicyError("unknown_cost", "Call cost is unknown; stop and reconcile")
        self.data["calls"][index]["cost_usd"] = cost
        self.save()
        if cost > RESERVE:
            raise PolicyError("reservation_exceeded", "Charge exceeded reservation; stop")


class MeteredBackend:
    def __init__(self, backend, ledger):
        self.backend, self.ledger = backend, ledger
        self.transport, self.model = backend.transport, backend.model
        self.accepted_models = backend.accepted_models
        self.fatal = False

    async def evaluate(self, payload, **kwargs):
        if self.fatal:
            raise PolicyError("run_stopped", "No further live calls after metering failure")
        index = self.ledger.reserve(self.model)
        try:
            response = await self.backend.evaluate(payload, **kwargs)
            self.ledger.settle(index, response.get("usage", {}).get("cost"))
            return response
        except BaseException:
            self.fatal = True
            raise


class ChatBackend:
    """Research comparator only. Exact same scope question/state; no gold labels."""

    transport = "openrouter"
    model = CHAT_MODEL
    accepted_models = (CHAT_MODEL,)

    def __init__(self, http_transport=None):
        self.http_transport = http_transport

    async def evaluate(self, payload, *, timeout, max_bytes):
        if len(payload["questions"]) != 1:
            raise PolicyError("comparator_batch", "Comparator requires one question")
        key, question = next(iter(payload["questions"].items()))
        labels = list(question["criteria"])
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "type": {"type": "string", "enum": ["choice"]},
                "choice": {"type": "string", "enum": labels},
                "confidence": {"type": "number"},
                "probabilities": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {label: {"type": "number"} for label in labels},
                    "required": labels,
                },
            },
            "required": ["type", "choice", "confidence", "probabilities"],
        }
        body = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 512,
            "provider": {
                "only": ["google-ai-studio"],
                "allow_fallbacks": False,
                "require_parameters": True,
                "max_price": {"prompt": 0.1, "completion": 0.4},
            },
            "messages": [
                {
                    "role": "system",
                    "content": canonical(question)
                    + " Return the choice and self-estimated confidence/probabilities in [0,1]. "
                    "Probabilities must sum to one and choice must have the highest probability.",
                },
                {"role": "user", "content": canonical(payload["state"])},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "policy_scope", "strict": True, "schema": schema},
            },
        }
        encoded = canonical(body).encode()
        if len(encoded) > 24000:
            raise PolicyError("comparator_limit", "Comparator request too large")
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise PolicyError("missing_credentials", "Set key locally")
        async with httpx.AsyncClient(
            trust_env=False, follow_redirects=False, timeout=timeout, transport=self.http_transport
        ) as client:
            async with client.stream(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                content=encoded,
                headers={
                    "Authorization": "Bearer " + api_key,
                    "Content-Type": "application/json",
                    "Accept-Encoding": "identity",
                },
            ) as response:
                if response.status_code != 200:
                    raise PolicyError("comparator_http", f"Comparator HTTP {response.status_code}")
                if response.headers.get("content-encoding", "identity") != "identity":
                    raise PolicyError("comparator_encoding", "Unsupported response encoding")
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > max_bytes:
                        raise PolicyError("response_limit", "Comparator response too large")
        raw = decode_json(bytes(data))
        # Preserve usage even if generated JSON is malformed, so billing is not lost.
        usage = raw.get("usage", {})
        try:
            answer = decode_json(raw["choices"][0]["message"]["content"].encode())
        except (KeyError, TypeError, AttributeError, PolicyError):
            answer = {}
        return {
            "model": raw.get("model"),
            "answers": {key: answer},
            "usage": {
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens"),
                "cost": usage.get("cost"),
            },
        }
