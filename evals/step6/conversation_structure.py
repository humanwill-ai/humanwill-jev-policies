"""Research-only structured conversation input; shipped runtime and old campaigns unchanged."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
import random
import subprocess
from pathlib import Path

from humanwill_policies.errors import PolicyError
from humanwill_policies.providers import JevBackend
from humanwill_policies.runtime import utc_now
from humanwill_policies.serialization import canonical

from .conversation_live import assess as assess_flat
from .conversation_live import load_inputs as previous_inputs
from .conversation_live import statistics
from .live_support import Ledger, credential, ledger_total
from .policy_isolation import RecordedBackend
from .question_context import sha256
from .restart_accounting import RestartMeteredBackend
from .reviewed_live import ROOT
from .run import write_json

BASE = ROOT / "evals/step6/conversation-structure-v1"
ARMS = ("flat", "structured")


def partition(content):
    """Structure supplied roles only; never parse text, infer approval or drop content."""
    latest = next(
        (
            i
            for i in range(len(content) - 1, -1, -1)
            if content[i]["kind"] == "text" and content[i].get("role") == "user"
        ),
        None,
    )
    if latest is None:
        return {"unsegmented_messages": copy.deepcopy(content)}
    return {
        "earlier_messages": copy.deepcopy(content[:latest]),
        "latest_user_message": copy.deepcopy(content[latest]),
        "messages_after_latest_user": copy.deepcopy(content[latest + 1 :]),
    }


def flatten(grouped):
    if set(grouped) == {"unsegmented_messages"}:
        return copy.deepcopy(grouped["unsegmented_messages"])
    if set(grouped) != {"earlier_messages", "latest_user_message", "messages_after_latest_user"}:
        raise ValueError("Invalid structural representation")
    return copy.deepcopy(
        grouped["earlier_messages"]
        + [grouped["latest_user_message"]]
        + grouped["messages_after_latest_user"]
    )


def transform(payload, arm):
    if arm not in ARMS or payload["state"]["stage"] != "model_request":
        raise ValueError("Unexpected comparison arm or stage")
    result = copy.deepcopy(payload)
    if arm == "structured":
        original = result["state"]["content"]
        result["state"]["content"] = partition(original)
        if flatten(result["state"]["content"]) != original:
            raise ValueError("Representation lost or altered content")
    if len(canonical(result).encode()) > 24000:
        raise PolicyError("batch_limit", "Structured input exceeds the frozen payload limit")
    return result


class VariantBackend:
    def __init__(self, backend, arm):
        self.backend, self.arm = backend, arm
        self.transport, self.model = backend.transport, backend.model
        self.accepted_models = backend.accepted_models

    async def evaluate(self, payload, **kwargs):
        return await self.backend.evaluate(transform(payload, self.arm), **kwargs)


def load_inputs():
    cases, bundle, config = previous_inputs()
    cases += json.loads((BASE / "controls.json").read_text())["cases"]
    return cases, bundle, config


def validate():
    frozen = json.loads((BASE / "protocol.json").read_text())
    for name, expected in frozen["sha256"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f"Frozen structural conversation input changed: {name}")
    inputs = load_inputs()
    if [c["id"] for c in inputs[0]] != frozen["case_ids"]:
        raise ValueError("Case order or IDs changed")
    return frozen, inputs


async def assess(case, bundle, config, backend, arm):
    # The previous clarified runtime wrapper retains exactly the same questions,
    # metadata and bounded follow-ups. Only the final wire state representation changes.
    return await assess_flat(case, bundle, config, VariantBackend(backend, arm), "clarified")


async def measure(output, ledger):
    frozen, (cases, bundle, config) = validate()
    output.mkdir(parents=True, exist_ok=False)
    before = ledger_total(ledger)
    ceiling = min(ledger.data["cap_usd"], before + frozen["additional_cap_usd"])
    backend = RestartMeteredBackend(
        JevBackend(config.to_dict()["provider"]),
        ledger,
        {int(k): v for k, v in frozen["carried_reservations"].items()},
    )
    write_json(
        output / "manifest.json",
        {
            "protocol": frozen,
            "started_at": utc_now().isoformat(),
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "accounted_before_usd": before,
            "ceiling_usd": ceiling,
            "bundle_sha256": bundle.sha256,
            "configuration_sha256": config.sha256,
        },
    )
    rows = []
    rng = random.Random(frozen["seed"])
    try:
        for rep in range(frozen["repeats"]):
            order = list(cases)
            rng.shuffle(order)
            for case in order:
                arms = list(ARMS)
                rng.shuffle(arms)
                for arm in arms:
                    if len(backend.calls) >= frozen["max_physical_calls"]:
                        raise ValueError("Frozen call ceiling reached")
                    caller = RecordedBackend(
                        backend,
                        output / "provider-exchanges.jsonl",
                        f"{rep}/{case['id']}/{arm}",
                        ledger,
                        ceiling,
                    )
                    start = len(ledger.data["calls"])
                    result = await assess(case, bundle, config, caller, arm)
                    row = {
                        k: copy.deepcopy(case[k])
                        for k in (
                            "id",
                            "category",
                            "expected_composed",
                            "expected_by_policy",
                            "expected_choices",
                        )
                    }
                    charges = ledger.data["calls"][start:]
                    row.update(
                        repeat=rep,
                        arm=arm,
                        result=result,
                        physical_calls=len(caller.records),
                        ledger_indices=list(range(start, len(ledger.data["calls"]))),
                        metered_cost_usd=sum(
                            c["cost_usd"] if c["cost_usd"] is not None else c["reserved_usd"]
                            for c in charges
                        ),
                    )
                    rows.append(row)
                    with (output / "results.jsonl").open("a") as stream:
                        stream.write(json.dumps(row) + "\n")
                    print(
                        json.dumps(
                            {
                                "completed": len(rows),
                                "repeat": rep,
                                "id": case["id"],
                                "arm": arm,
                                "decision": result["decision"],
                            }
                        ),
                        flush=True,
                    )
                    if backend.fatal:
                        return
    finally:
        write_json(
            output / "summary.json",
            {
                "complete": len(rows) == len(cases) * frozen["repeats"] * 2,
                "observations": len(rows),
                "results": {a: statistics([r for r in rows if r["arm"] == a]) for a in ARMS},
                "passes": {
                    str(rep): {
                        a: statistics([r for r in rows if r["arm"] == a and r["repeat"] == rep])
                        for a in ARMS
                    }
                    for rep in range(frozen["repeats"])
                },
                "physical_calls": len(backend.calls),
                "accounted_before_usd": before,
                "accounted_after_usd": ledger_total(ledger),
                "new_accounted_usd": ledger_total(ledger) - before,
                "unknown_ledger_indices": [
                    i for i, c in enumerate(ledger.data["calls"]) if c["cost_usd"] is None
                ],
                "provider_calls": backend.calls,
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--keychain-helper", type=Path)
    args = parser.parse_args()
    frozen, (cases, _, _) = validate()
    if args.validate_only:
        print(json.dumps({"cases": len(cases), "repeats": frozen["repeats"], "calls": 0}))
        return
    if not args.allow_external or args.output is None or args.output.exists():
        parser.error("Fresh output and explicit synthetic egress required")
    if subprocess.check_output(["git", "status", "--porcelain"]):
        parser.error("Commit frozen experiment before live calls")
    path = ROOT / "artifacts/quality/spending.json"
    try:
        with path.with_suffix(".lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if sha256(path) != frozen["starting_ledger_sha256"]:
                raise ValueError("Starting ledger changed")
            credential(args.keychain_helper)
            asyncio.run(measure(args.output, Ledger(path)))
    finally:
        os.environ.pop("OPENROUTER_API_KEY", None)


if __name__ == "__main__":
    main()
