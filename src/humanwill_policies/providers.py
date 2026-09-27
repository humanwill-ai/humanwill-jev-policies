"""Typed Jev adapters. Fixed routes, no redirects, retries, fallback, or content logging."""

import json
import math
import os
from typing import Protocol

import httpx

from .errors import PolicyError
from .serialization import canonical, json_value

ENDPOINTS = {
    "openrouter": "https://openrouter.ai/api/alpha/decisions",
    "typesafe": "https://api.typesafe.ai/v1/systemone",
}


def decode_json(data: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    try:
        result = json.loads(data, object_pairs_hook=pairs)
        json_value(result)
        if not isinstance(result, dict):
            raise ValueError
        return result
    except (ValueError, UnicodeError, RecursionError, PolicyError):
        raise PolicyError("malformed_json", "Invalid JSON object") from None


class Backend(Protocol):
    transport: str
    model: str
    accepted_models: tuple[str, ...]

    async def evaluate(self, payload: dict, *, timeout: float, max_bytes: int) -> dict: ...


class MockBackend:
    """Explicit scripted answers; never infer an allow when the script is incomplete."""

    transport = "mock"
    model = "mock"
    accepted_models = ("mock",)

    def __init__(self, answers: dict):
        json_value(answers)
        self._answers = canonical(answers)

    async def evaluate(self, payload, *, timeout, max_bytes):
        answers = json.loads(self._answers)
        response = {
            "model": "mock",
            "answers": {key: answers[key] for key in payload["questions"] if key in answers},
            "usage": {"input_tokens": 0, "output_tokens": 0, "cost": 0},
        }
        if len(canonical(response).encode()) > max_bytes:
            raise PolicyError("response_limit", "Evaluator response exceeds byte limit")
        return response


class JevBackend:
    def __init__(self, provider: dict, *, http_transport=None):
        self.transport = provider["transport"]
        if self.transport not in ENDPOINTS:
            raise PolicyError("unsupported_transport", "Unknown provider route")
        self.model = provider["model"]
        self.accepted_models = tuple(provider.get("accepted_models", [self.model]))
        self._key_env = provider["api_key_env"]
        self._http_transport = http_transport

    async def evaluate(self, payload, *, timeout, max_bytes):
        key = os.environ.get(self._key_env)
        if not key or any(ord(char) < 33 or ord(char) > 126 for char in key):
            raise PolicyError("missing_credentials", "Set the configured provider key locally")
        try:
            async with httpx.AsyncClient(
                trust_env=False,
                follow_redirects=False,
                timeout=timeout,
                transport=self._http_transport,
                limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
            ) as client:
                async with client.stream(
                    "POST",
                    ENDPOINTS[self.transport],
                    content=canonical(payload).encode(),
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Accept-Encoding": "identity",
                    },
                ) as response:
                    if response.status_code != 200:
                        code = {
                            401: "provider_auth",
                            403: "provider_auth",
                            402: "provider_budget",
                            429: "provider_rate_limit",
                            529: "provider_overloaded",
                        }.get(response.status_code, "provider_http_error")
                        raise PolicyError(code, f"Evaluator returned HTTP {response.status_code}")
                    if response.headers.get("content-encoding", "identity") != "identity":
                        raise PolicyError(
                            "unsupported_encoding", "Compressed replies are unsupported"
                        )
                    if response.headers.get("content-type", "").split(";")[0] != "application/json":
                        raise PolicyError("malformed_response", "Evaluator must return JSON")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(body) + len(chunk) > max_bytes:
                            raise PolicyError(
                                "response_limit", "Evaluator response exceeds byte limit"
                            )
                        body.extend(chunk)
                    return decode_json(bytes(body))
        except httpx.TimeoutException:
            raise PolicyError("provider_timeout", "Evaluator network timeout") from None
        except httpx.HTTPError:
            raise PolicyError("provider_network", "Evaluator network failure") from None


def validate_response(response, questions, accepted_models):
    """Fail the entire batch on mismatched IDs/models or malformed numeric evidence."""
    try:
        json_value(response)
        if response["model"] not in accepted_models:
            raise PolicyError("model_mismatch", "Returned model is not explicitly accepted")
        answers = response["answers"]
        if not isinstance(answers, dict) or set(answers) != set(questions):
            raise PolicyError("answer_ids", "Evaluator answer IDs do not match the batch")
        for key, question in questions.items():
            answer = answers[key]
            labels = set(question["criteria"])
            probabilities = answer["probabilities"]
            if answer["type"] != "choice" or set(probabilities) != labels:
                raise ValueError
            numbers = [answer["confidence"], *probabilities.values()]
            if any(
                type(n) not in (int, float) or not math.isfinite(n) or not 0 <= n <= 1
                for n in numbers
            ):
                raise ValueError
            if not math.isclose(sum(probabilities.values()), 1.0, abs_tol=1e-6):
                raise ValueError
            if answer["choice"] not in labels or probabilities[answer["choice"]] != max(
                probabilities.values()
            ):
                raise ValueError
        usage = response["usage"]
        if not isinstance(usage, dict):
            raise ValueError
        normalized = {"returned_model": response["model"]}
        for source, target in [
            ("input_tokens", "input_tokens"),
            ("output_tokens", "output_tokens"),
            ("cost", "cost_usd"),
        ]:
            value = usage.get(source)
            if value is not None and (
                type(value) not in (int, float) or not math.isfinite(value) or value < 0
            ):
                raise ValueError
            if source != "cost" and value is not None and type(value) is not int:
                raise ValueError
            normalized[target] = value
        # Copy only known answer fields, never provider-supplied prose or debugging data.
        cleaned = {
            key: {field: answer[field] for field in ("choice", "confidence", "probabilities")}
            for key, answer in answers.items()
        }
        return cleaned, normalized
    except PolicyError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError):
        raise PolicyError("malformed_response", "Invalid evaluator answer or usage") from None
