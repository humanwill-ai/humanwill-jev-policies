"""Frozen synthetic multi-turn comparison; only conversation_scope differs between arms."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
import random
import subprocess
from collections import Counter
from pathlib import Path

import yaml

from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.conversation import CONVERSATION_RULE
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import JevBackend
from humanwill_policies.runtime import EgressPermit, EvidenceContext, utc_now
from humanwill_policies.serialization import digest

from .live_support import Ledger, credential, ledger_total
from .metrics import percentile
from .policy_isolation import RecordedBackend
from .question_context import sha256
from .restart_accounting import RestartMeteredBackend
from .reviewed_live import ROOT, observed_policy
from .run import write_json

BASE = ROOT / "evals/step6/conversation-v1"
ARMS = ("previous", "clarified")


def transform(payload, arm):
    if arm not in ARMS or payload["state"]["stage"] != "model_request":
        raise ValueError("Unexpected comparison arm or stage")
    result = copy.deepcopy(payload)
    for question in result["questions"].values():
        if question["instructions"].get("conversation_scope") != CONVERSATION_RULE:
            raise ValueError("Conversation clarification changed or missing")
        if arm == "previous":
            question["instructions"].pop("conversation_scope")
    return result


class VariantBackend:
    def __init__(self, backend, arm):
        self.backend, self.arm = backend, arm
        self.transport, self.model = backend.transport, backend.model
        self.accepted_models = backend.accepted_models

    async def evaluate(self, payload, **kwargs):
        return await self.backend.evaluate(transform(payload, self.arm), **kwargs)


def load_inputs():
    cases = json.loads((BASE / "cases.json").read_text())["cases"]
    bundle = load_bundle(BASE / "policies")
    config = load_configuration(bundle, yaml.safe_load((BASE / "config.yaml").read_text()))
    return cases, bundle, config


def validate():
    frozen = json.loads((BASE / "protocol.json").read_text())
    for name, expected in frozen["sha256"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f"Frozen conversation comparison changed: {name}")
    inputs = load_inputs()
    if [c["id"] for c in inputs[0]] != frozen["case_ids"]:
        raise ValueError("Case order or IDs changed")
    return frozen, inputs


async def assess(case, bundle, config, backend, arm):
    # Fixture-owned authority, identical for every case and arm. Never parse claims
    # or expected labels into approval, and never send these values to the model.
    request = case["request"]
    facts = [
        {
            "field": field,
            "source": "synthetic-authority",
            "subject_ref": "synthetic-conversation-environment",
            "complete": True,
            "observed_at": utc_now().isoformat(),
            "value": value,
        }
        for field, value in [
            ("destination.coding_route_approved", True),
            ("destination.onward_approved", False),
            ("authorization.software_sources_approved", False),
        ]
    ]
    wrapped = VariantBackend(backend, arm)
    return await Evaluator(bundle, config, wrapped).evaluate(
        request,
        evidence=EvidenceContext.from_verified(request, facts),
        egress=EgressPermit(digest(request), bundle.sha256, backend.transport),
    )


def statistics(rows):
    expected = Counter(r["expected_composed"] for r in rows)

    def actual(r):
        return r["result"]["decision"]

    matrix = {
        label: dict(Counter(actual(r) for r in rows if r["expected_composed"] == label))
        for label in ("allow", "block", "evaluation_error")
    }
    return {
        "observations": len(rows),
        "distinct_cases": len({r["id"] for r in rows}),
        "expected": dict(expected),
        "confusion": matrix,
        "exact_events": sum(actual(r) == r["expected_composed"] for r in rows),
        "explicit_false_blocks": matrix["allow"].get("block", 0),
        "false_blocks_if_fail_closed": expected["allow"] - matrix["allow"].get("allow", 0),
        "missed_violations": matrix["block"].get("allow", 0),
        "missed_violations_if_fail_open": expected["block"] - matrix["block"].get("block", 0),
        "unexpected_abstentions": sum(
            matrix[k].get("evaluation_error", 0) for k in ("allow", "block")
        ),
        "unknown_allowed": matrix["evaluation_error"].get("allow", 0),
        "wrong_definitive_policy_answers": [
            [r["repeat"], r["id"], p["policy_id"], observed_policy(p)]
            for r in rows
            for p in r["result"]["policies"]
            if observed_policy(p)
            not in ("evaluation_error", r["expected_by_policy"][p["policy_id"]])
        ],
        "policy_exact": sum(
            observed_policy(p) == r["expected_by_policy"][p["policy_id"]]
            for r in rows
            for p in r["result"]["policies"]
        ),
        "error_reasons": dict(
            Counter(
                reason
                for r in rows
                for p in r["result"]["policies"]
                if p["status"] == "error"
                for reason in p["reasons"]
            )
        ),
        "evaluator_latency_ms": {
            "median": percentile([r["result"]["duration_ms"] for r in rows], 0.5),
            "p95": percentile([r["result"]["duration_ms"] for r in rows], 0.95),
        },
        "provider_calls": sum(r["physical_calls"] for r in rows),
        "metered_cost_usd": sum(r["metered_cost_usd"] for r in rows),
    }


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
