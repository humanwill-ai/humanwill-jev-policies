"""Paired private-workflow grouping experiment; no shipped-runtime changes."""

import argparse
import asyncio
import fcntl
import json
import os
import random
import subprocess
from collections import Counter
from pathlib import Path

from evals.step6.conversation_live import statistics
from evals.step6.conversation_structure import VariantBackend
from evals.step6.conversation_structure import assess as assess_control
from evals.step6.conversation_structure import load_inputs as load_controls
from evals.step6.live_support import Ledger, credential, ledger_total
from evals.step6.metrics import percentile
from evals.step6.policy_isolation import RecordedBackend
from evals.step6.restart_accounting import RestartMeteredBackend
from humanwill_policies.providers import JevBackend
from humanwill_policies.runtime import utc_now

from .evaluate import CARRIED, assess, load_profile, verify_receipt
from .pilot import ROOT, fingerprint, save

ARMS = ("flat", "structured")


def control_signature(cases, bundle, config):
    return fingerprint({"cases": cases, "bundle": bundle.sha256, "config": config.sha256})


def validate(directory, receipt):
    original = json.loads((directory / "history/packet.json").read_text())
    reviewed = json.loads((directory / "history/provisional-review.json").read_text())
    scope = json.loads((directory / "operator-scope.json").read_text())
    bundle, config = load_profile()
    cases = verify_receipt(original, reviewed, receipt, scope, bundle, config)
    controls, cb, cc = load_controls()
    if receipt.get("controls_sha256") != control_signature(controls, cb, cc):
        raise ValueError("Safety controls or their configuration changed")
    if (
        receipt.get("experiment") != "grouping_only_v1"
        or receipt.get("repeats") != 2
        or receipt.get("seed") != 20261003
        or receipt.get("max_physical_calls") != 640
        or receipt.get("additional_cap_usd") != 0.10
        or len(cases) != 50
        or len(controls) != 30
    ):
        raise ValueError("Frozen comparison dimensions changed")
    if config.to_dict()["provider"] != cc.to_dict()["provider"]:
        raise ValueError("Provider differs across cohorts")
    return cases, bundle, config, controls, cb, cc


async def assess_arm(case, bundle, config, backend, cohort, arm):
    if cohort == "workflow":
        return await assess(case, bundle, config, VariantBackend(backend, arm))
    if cohort == "controls":
        return await assess_control(case, bundle, config, backend, arm)
    raise ValueError("Unknown cohort")


def summarize(rows):
    summary = {}
    for arm in ARMS:
        selected = [r for r in rows if r["arm"] == arm]
        workflow = [r for r in selected if r["cohort"] == "workflow"]
        controls = [r for r in selected if r["cohort"] == "controls"]
        summary[arm] = {
            "workflow": {
                "observations": len(workflow),
                "decisions": dict(Counter(r["result"]["decision"] for r in workflow)),
                "per_repeat": {
                    str(rep): dict(
                        Counter(r["result"]["decision"] for r in workflow if r["repeat"] == rep)
                    )
                    for rep in range(2)
                },
                "latency_ms": {
                    "median": percentile([r["result"]["duration_ms"] for r in workflow], 0.5),
                    "p95": percentile([r["result"]["duration_ms"] for r in workflow], 0.95),
                },
                "event_error_reasons": dict(
                    Counter(
                        reason
                        for r in workflow
                        for reason in {
                            code
                            for p in r["result"]["policies"]
                            if p["status"] == "error"
                            for code in p["reasons"]
                        }
                    )
                ),
            },
            "controls": statistics(controls),
            "physical_calls": sum(r["physical_calls"] for r in selected),
            "cost_usd": sum(r["metered_cost_usd"] for r in selected),
        }
    return summary


async def measure(output, ledger, receipt, inputs):
    cases, bundle, config, controls, cb, cc = inputs
    before = ledger_total(ledger)
    ceiling = min(ledger.data["cap_usd"], before + receipt["additional_cap_usd"])
    backend = RestartMeteredBackend(JevBackend(config.to_dict()["provider"]), ledger, CARRIED)
    save(
        output / "manifest.json",
        {
            "approval": receipt,
            "started_at": utc_now().isoformat(),
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "accounted_before_usd": before,
        },
    )
    rows = []
    rng = random.Random(receipt["seed"])
    try:
        for rep in range(receipt["repeats"]):
            order = [("workflow", c) for c in cases] + [("controls", c) for c in controls]
            rng.shuffle(order)
            for cohort, case in order:
                arms = list(ARMS)
                rng.shuffle(arms)
                for arm in arms:
                    if len(backend.calls) >= receipt["max_physical_calls"]:
                        raise ValueError("Physical call ceiling reached")
                    run_id = f"{rep}/{cohort}/{case['id']}/{arm}"
                    caller = RecordedBackend(
                        backend, output / "provider-exchanges.jsonl", run_id, ledger, ceiling
                    )
                    start = len(ledger.data["calls"])
                    b, c = (bundle, config) if cohort == "workflow" else (cb, cc)
                    result = await assess_arm(case, b, c, caller, cohort, arm)
                    row = {
                        "id": case["id"],
                        "run_id": run_id,
                        "repeat": rep,
                        "arm": arm,
                        "cohort": cohort,
                        "result": result,
                        "physical_calls": len(caller.records),
                        "ledger_indices": list(range(start, len(ledger.data["calls"]))),
                        "metered_cost_usd": sum(
                            x["cost_usd"] if x["cost_usd"] is not None else x["reserved_usd"]
                            for x in ledger.data["calls"][start:]
                        ),
                    }
                    if cohort == "controls":
                        row.update(
                            {
                                k: case[k]
                                for k in (
                                    "expected_composed",
                                    "expected_by_policy",
                                    "expected_choices",
                                )
                            }
                        )
                    else:
                        row.update(
                            expected_composed=case["review"]["expected_decision"],
                            label_status=case["review"]["status"],
                        )
                    rows.append(row)
                    with (output / "results.jsonl").open("a") as stream:
                        stream.write(json.dumps(row) + "\n")
                    if len(rows) % 20 == 0:
                        print(
                            json.dumps({"completed": len(rows), "calls": len(backend.calls)}),
                            flush=True,
                        )
                    if backend.fatal:
                        return
    finally:
        save(
            output / "summary.json",
            {
                "complete": len(rows) == 320,
                "observations": len(rows),
                "arms": summarize(rows),
                "physical_calls": len(backend.calls),
                "accounted_before_usd": before,
                "accounted_after_usd": ledger_total(ledger),
                "new_cost_usd": ledger_total(ledger) - before,
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--keychain-helper", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text())
    inputs = validate(args.directory, receipt)
    if args.validate_only:
        print(json.dumps({"workflow_cases": 50, "controls": 30, "assessments": 320, "calls": 0}))
        return
    if args.output.exists() or subprocess.check_output(["git", "status", "--porcelain"]):
        parser.error("Fresh output and clean frozen source required")
    path = ROOT / "artifacts/quality/spending.json"
    try:
        with path.with_suffix(".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            ledger = Ledger(path)
            if fingerprint(ledger.data) != receipt["starting_ledger_sha256"]:
                raise ValueError("Starting ledger changed")
            used_path = args.directory / "used-approvals.json"
            used = json.loads(used_path.read_text()) if used_path.exists() else []
            if fingerprint(receipt) in used:
                raise ValueError("Comparison approval already consumed")
            credential(args.keychain_helper)
            save(used_path, [*used, fingerprint(receipt)])
            os.umask(0o077)
            args.output.mkdir(mode=0o700)
            asyncio.run(measure(args.output, ledger, receipt, inputs))
    finally:
        os.environ.pop("OPENROUTER_API_KEY", None)


if __name__ == "__main__":
    main()
