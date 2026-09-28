"""Load the clarified experimental scope question without altering frozen/live defaults."""

import copy
import json
from pathlib import Path

from humanwill_policies.errors import PolicyError
from humanwill_policies.serialization import canonical

QUESTION = Path(__file__).parent / "focused-policy-v2/question.json"


def clarify_payload(payload):
    """Replace only task/criteria; preserve event, policies, context and trusted-data boundary."""
    candidate = json.loads(QUESTION.read_text())
    result = copy.deepcopy(payload)
    for question in result["questions"].values():
        if set(question["criteria"]) != set(candidate["criteria"]):
            raise PolicyError("unsupported_experiment", "Only scoped predicates in this experiment")
        question["instructions"]["task"] = candidate["task"]
        question["criteria"] = copy.deepcopy(candidate["criteria"])
    if len(canonical(result).encode()) > 24000:
        raise PolicyError("batch_limit", "Clarified question exceeds provider request limit")
    return result


class ClarifiedBackend:
    """Opt-in research wrapper; use the normal context/egress/metering guards outside it."""

    def __init__(self, delegate):
        self.delegate = delegate
        self.transport, self.model = delegate.transport, delegate.model
        self.accepted_models = delegate.accepted_models

    async def evaluate(self, payload, **kwargs):
        return await self.delegate.evaluate(clarify_payload(payload), **kwargs)
