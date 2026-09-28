"""Research-only effect-aware scope wording; no production template replacement."""

import copy
import json

from humanwill_policies.errors import PolicyError
from humanwill_policies.serialization import canonical, digest

from .reviewed_live import BASE

DIRECTORY = BASE / "effect-question-v1"
QUESTION = DIRECTORY / "question.json"
OBSERVATIONS = DIRECTORY / "observations.json"


def context_for(case, original, condition):
    if condition not in ("question_only", "question_and_context"):
        raise ValueError("Unknown experiment condition")
    if original["id"] != case["id"] or original["request_sha256"] != digest(case["request"]):
        raise ValueError("Context must match the exact event")
    record = copy.deepcopy(original)
    previous = json.loads((BASE / "focused-policy-v1/protocol.json").read_text())
    if case["id"] in previous["short_context"]:
        record["context"]["operation_semantics"] = previous["short_context"][case["id"]]
    observations = json.loads(OBSERVATIONS.read_text())["cases"]
    if condition == "question_and_context" and case["id"] in observations:
        observation = observations[case["id"]]
        if observation["request_sha256"] != digest(case["request"]):
            raise ValueError("Tool-effect observation belongs to a different event")
        record["context"]["operation_semantics"] = observation["description"]
    return record


def transform(payload):
    question = json.loads(QUESTION.read_text())
    result = copy.deepcopy(payload)
    for q in result["questions"].values():
        if set(q["criteria"]) != set(question["criteria"]):
            raise PolicyError("unsupported_experiment", "Only scoped predicates supported")
        q["instructions"]["task"] = question["task"]
        q["criteria"] = copy.deepcopy(question["criteria"])
    if len(canonical(result).encode()) > 24000:
        raise PolicyError("batch_limit", "Effect-aware payload exceeds provider limit")
    return result


class EffectBackend:
    def __init__(self, delegate, request_id, exchanges=None):
        self.delegate, self.request_id, self.exchanges = delegate, request_id, exchanges
        self.transport, self.model = delegate.transport, delegate.model
        self.accepted_models = delegate.accepted_models

    async def evaluate(self, payload, **kwargs):
        request = transform(payload)
        exchange = {"request_id": self.request_id, "payload": request}
        try:
            response = await self.delegate.evaluate(request, **kwargs)
            exchange["raw_response"] = response
            return response
        except PolicyError as exc:
            exchange["error"] = exc.code
            raise
        finally:
            if self.exchanges is not None:
                with self.exchanges.open("a") as stream:
                    stream.write(json.dumps(exchange) + "\n")
