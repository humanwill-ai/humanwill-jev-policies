"""Research-only Q04 batch versus isolation comparison with provisional fresh workflows."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
import random
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from humanwill_policies import load_configuration
from humanwill_policies.errors import PolicyError
from humanwill_policies.providers import JevBackend, validate_response

from .live_support import Ledger, credential, ledger_total
from .policy_isolation import (
    RecordedBackend,
    StoredBackend,
    eligible_policies,
    evaluate,
    merge_answers,
)
from .q05_full_pack import abstention_summary
from .q05_full_pack import validate_experiment as validate_previous
from .question_context import sha256
from .restart_accounting import RestartMeteredBackend
from .reviewed_live import ROOT, observed_policy
from .run import select_configuration, write_json
from .short_questions import transform
from .source_approval import source_evidence_for

PROTOCOL = ROOT / "evals/step6/q04-comparison-v1/protocol.json"
ARMS = ("batch_q04", "isolate_q04")


def followup_payloads(payload, ids, arm):
    if arm not in ARMS or not set(ids) <= set(payload["questions"]):
        raise ValueError("Invalid follow-up arm or policy IDs")
    if not ids:
        return []
    if arm == "batch_q04":
        return [transform(copy.deepcopy(payload), "q04")]
    result = []
    for pid in sorted(ids):
        isolated = copy.deepcopy(payload)
        isolated["questions"] = {pid: isolated["questions"][pid]}
        result.append(transform(isolated, "q04") if arm == "isolate_q04" else isolated)
    return result


async def refine(primary_record, first_result, arm, caller, thresholds, timeout_ms):
    ids = eligible_policies(first_result)
    response = copy.deepcopy(primary_record["raw_response"])
    payloads = followup_payloads(primary_record["payload"], ids, arm)
    # Each arm represents an independent runtime continuation of the shared first call.
    # Time spent measuring OTHER arms is not part of its hypothetical runtime deadline.
    deadline = time.monotonic() + max(0, timeout_ms - first_result["duration_ms"]) / 1000
    notes = {
        "eligible": ids,
        "accepted": [],
        "rejected": {},
        "calls": 0,
        "unattempted_policy_ids": [p for payload in payloads[2:] for p in payload["questions"]],
    }
    for payload in payloads[:2]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            notes["stopped"] = "total_deadline"
            break
        notes["calls"] += 1
        try:
            async with asyncio.timeout(remaining):
                followup = await caller.evaluate(payload, timeout=remaining, max_bytes=262144)
            answers, _ = validate_response(followup, payload["questions"], caller.accepted_models)
        except TimeoutError:
            notes["stopped"] = "total_deadline"
            break
        except PolicyError as exc:
            notes["rejected"].update({pid: exc.code for pid in payload["questions"] if pid in ids})
            if getattr(caller.backend, "fatal", False):
                break
            continue
        response, accepted, rejected = merge_answers(response, answers, ids, thresholds)
        notes["accepted"].extend(accepted)
        notes["rejected"].update(rejected)
    return response, notes


def validate_experiment():
    frozen = json.loads(PROTOCOL.read_text())
    for path, expected in frozen["sha256"].items():
        if sha256(ROOT / path) != expected:
            raise ValueError(f"Frozen isolation input changed: {path}")
    _, cases, bundle, config, catalog, contexts = validate_previous()
    fresh = json.loads((PROTOCOL.parent / "fresh-cases.json").read_text())["cases"]
    cases = cases + fresh
    contexts.update(
        {
            c["id"]: c
            for c in json.loads((PROTOCOL.parent / "fresh-contexts.json").read_text())["cases"]
        }
    )
    if [c["id"] for c in cases] != frozen["case_ids"]:
        raise ValueError("Case ordering changed")
    return frozen, cases, bundle, config, catalog, contexts


def summarize(rows, repeats):
    report = {}
    for rep in range(repeats):
        report[str(rep)] = {}
        for arm in ("primary", *ARMS):
            selected = [r for r in rows if r["repeat"] == rep and r["arm"] == arm]
            stats = abstention_summary(selected)
            stats["wrong_definitive"] = [
                r["id"]
                for r in selected
                if r["result"]["decision"] != "evaluation_error"
                and r["result"]["decision"] != r["expected_composed"]
            ]
            stats["policy_wrong_definitive"] = [
                [r["id"], p["policy_id"], observed_policy(p)]
                for r in selected
                for p in r["result"]["policies"]
                if p["policy_id"] in r["expected_by_policy"]
                and observed_policy(p) != "evaluation_error"
                and observed_policy(p) != r["expected_by_policy"][p["policy_id"]]
            ]
            report[str(rep)][arm] = stats
    return report


async def measure(output, ledger):
    frozen, cases, bundle, config, catalog, contexts = validate_experiment()
    output.mkdir(parents=True, exist_ok=False)
    before = ledger_total(ledger)
    ceiling = min(ledger.data["cap_usd"], before + frozen["additional_cap_usd"])
    metered = RestartMeteredBackend(
        JevBackend(config["provider"]),
        ledger,
        {int(k): v for k, v in frozen["carried_reservations"].items()},
    )
    write_json(
        output / "manifest.json",
        {
            "protocol": frozen,
            "started_at": datetime.now(UTC).isoformat(),
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "accounted_before_usd": before,
            "accounting_ceiling_usd": ceiling,
            "comparison": "Each two-arm comparison shares one fresh Q05 primary response.",
        },
    )
    rows = []
    rng = random.Random(frozen["seed"])

    def save(case, result, rep, arm, notes):
        row = {
            k: copy.deepcopy(case[k])
            for k in ("id", "expected_composed", "expected_by_policy", "scope_by_policy")
        }
        row.update(
            result=result,
            repeat=rep,
            arm=arm,
            followup=notes,
            cohort="fresh_provisional" if case["id"].startswith("fresh-q04-") else "reviewed",
        )
        rows.append(row)
        with (output / "results.jsonl").open("a") as stream:
            stream.write(json.dumps(row) + "\n")

    try:
        for rep in range(frozen["repeats"]):
            for case in cases:
                cid = case["id"]
                loaded = load_configuration(
                    bundle,
                    select_configuration(
                        config, case["policy_id"], case.get("also_policy_ids", [])
                    ),
                )
                evidence = source_evidence_for(case, catalog)
                caller = RecordedBackend(
                    metered,
                    output / "provider-exchanges.jsonl",
                    f"{rep}/{cid}/primary",
                    ledger,
                    ceiling,
                )
                first = await evaluate(case, bundle, loaded, caller, contexts[cid], evidence)
                save(case, first, rep, "primary", {})
                if metered.fatal:
                    return
                arms = list(ARMS)
                rng.shuffle(arms)
                for arm in arms:
                    notes = {"eligible": [], "accepted": [], "rejected": {}, "calls": 0}
                    result = copy.deepcopy(first)
                    if eligible_policies(first):
                        if len(caller.records) != 1:
                            raise ValueError("Expected one primary batch in this frozen pack")
                        branch = RecordedBackend(
                            metered,
                            output / "provider-exchanges.jsonl",
                            f"{rep}/{cid}/{arm}",
                            ledger,
                            ceiling,
                        )
                        start = time.monotonic()
                        merged, notes = await refine(
                            caller.records[0],
                            first,
                            arm,
                            branch,
                            config["outcome_thresholds"],
                            config["evaluation"]["timeout_ms"],
                        )
                        stored = StoredBackend(metered, caller.records[0]["payload"], merged)
                        result = await evaluate(
                            case, bundle, loaded, stored, contexts[cid], evidence
                        )
                        result["duration_ms"] = (
                            first["duration_ms"] + (time.monotonic() - start) * 1000
                        )
                        notes["usage_note"] = (
                            "Result batch usage is shared primary only; "
                            "physical exchanges meter all follow-ups."
                        )
                    save(case, result, rep, arm, notes)
                    if metered.fatal:
                        return
                print(
                    json.dumps(
                        {
                            "repeat": rep,
                            "case": cid,
                            "completed_rows": len(rows),
                            "primary": first["decision"],
                        }
                    ),
                    flush=True,
                )
    finally:
        write_json(
            output / "summary.json",
            {
                "complete": len(rows) == len(cases) * frozen["repeats"] * 3,
                "rows": len(rows),
                "results": {
                    cohort: summarize([r for r in rows if r["cohort"] == cohort], frozen["repeats"])
                    for cohort in ("reviewed", "fresh_provisional")
                },
                "provider_calls": metered.calls,
                "accounted_before_usd": before,
                "accounted_after_usd": ledger_total(ledger),
                "new_accounted_usd": ledger_total(ledger) - before,
                "known_total_usd": ledger.data["prior_smoke_usd"]
                + sum(c["cost_usd"] or 0 for c in ledger.data["calls"]),
                "unknown_charges": sum(c["cost_usd"] is None for c in ledger.data["calls"]),
                "followup_events_by_branch": dict(
                    Counter(r["arm"] for r in rows if r["followup"].get("calls"))
                ),
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--keychain-helper", type=Path)
    args = parser.parse_args()
    frozen, cases, *_ = validate_experiment()
    if args.validate_only:
        print(
            json.dumps(
                {"cases": len(cases), "repeats": frozen["repeats"], "arms": ARMS, "api_calls": 0}
            )
        )
        return
    if args.output is None or args.output.exists() or not args.allow_external:
        parser.error("Fresh output directory and explicit synthetic egress required")
    if subprocess.check_output(["git", "status", "--porcelain"]):
        parser.error("Commit frozen protocol before live execution")
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
