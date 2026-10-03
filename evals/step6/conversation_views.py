"""Research-only explicit policy subjects with flat and grouped views; no runtime adoption."""

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
from .conversation_live import statistics
from .conversation_structure import flatten, partition
from .conversation_structure import load_inputs as previous_inputs
from .conversation_structure import transform as structural_transform
from .live_support import Ledger, credential, ledger_total
from .policy_isolation import RecordedBackend
from .question_context import sha256
from .restart_accounting import RestartMeteredBackend
from .reviewed_live import ROOT
from .run import write_json

BASE = ROOT / "evals/step6/conversation-views-v1"
ARMS = ("flat", "structured", "policy_views")


SUBJECTS = {
    "current_operation": {
        "kind": "current_operation",
        "view": "state.conversation",
        "meaning": (
            "Assess the operation currently requested or continued, using the complete "
            "conversation. Earlier messages supply references and unresolved tasks; "
            "grouping does not mark them approved or inactive."
        ),
    },
    "whole_payload": {
        "kind": "whole_payload",
        "view": "state.content",
        "meaning": (
            "Assess all content being sent in this model request, including every earlier "
            "message, quotation and tool result. Later cancellation does not remove "
            "earlier content from the transmitted payload."
        ),
    },
}


def load_subjects():
    settings = json.loads((BASE / "subjects.json").read_text())
    if settings.get("format") != "humanwill.experiment.policy-subjects/1":
        raise ValueError("Invalid research subject configuration")
    subjects = settings["policies"]
    if not subjects or any(value not in SUBJECTS for value in subjects.values()):
        raise ValueError("Every policy must have an explicit supported subject")
    return subjects


def transform(payload, arm, subjects=None):
    if arm not in ARMS or payload["state"]["stage"] != "model_request":
        raise ValueError("Unexpected comparison arm or stage")
    if arm != "policy_views":
        return structural_transform(payload, arm)
    subjects = load_subjects() if subjects is None else subjects
    if not set(payload["questions"]) <= set(subjects):
        raise ValueError("Missing explicit policy subject")
    if any(value not in SUBJECTS for value in subjects.values()):
        raise ValueError("Unknown policy subject")
    result = copy.deepcopy(payload)
    content = result["state"]["content"]
    grouped = partition(content)
    if "latest_user_message" in grouped:
        if flatten(grouped) != content:
            raise ValueError("Representation lost or altered content")
        # Full original list remains authoritative for transmission-content rules.
        # The second view is lossless and only describes supplied role boundaries.
        result["state"]["conversation"] = grouped
        for pid, question in result["questions"].items():
            question["instructions"]["assessment_subject"] = copy.deepcopy(SUBJECTS[subjects[pid]])
    # No user role: byte-identical original input, including questions. Do not invent turns.
    if len(canonical(result).encode()) > 24000:
        raise PolicyError("batch_limit", "Policy views exceed the frozen payload limit")
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
    subjects = load_subjects()
    if set(subjects) != set(config.to_dict()["policies"]):
        raise ValueError("Subject configuration must cover exactly the policy bundle")
    return cases, bundle, config


def validate():
    frozen = json.loads((BASE / "protocol.json").read_text())
    for name, expected in frozen["sha256"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f"Frozen policy-view comparison changed: {name}")
    inputs = load_inputs()
    if [c["id"] for c in inputs[0]] != frozen["case_ids"]:
        raise ValueError("Case order or IDs changed")
    return frozen, inputs


async def assess(case, bundle, config, backend, arm):
    # The previous clarified runtime wrapper retains exactly the same questions,
    # metadata and bounded follow-ups. The candidate adds views and an explicit subject.
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
                "complete": len(rows) == len(cases) * frozen["repeats"] * len(ARMS),
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
