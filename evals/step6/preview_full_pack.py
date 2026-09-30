"""Frozen final 170-case developer-preview measurement."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import yaml

from humanwill_policies import load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import JevBackend
from humanwill_policies.runtime import EgressPermit
from humanwill_policies.serialization import digest

from .effect_question import context_for
from .live_support import Ledger, credential, ledger_total
from .policy_isolation import RecordedBackend
from .q05_full_pack import abstention_summary
from .question_context import ContextBackend, sha256
from .restart_accounting import RestartMeteredBackend
from .reviewed_live import ROOT, observed_policy
from .run import load_case_bundle, select_configuration, write_json
from .source_approval import load_catalog, source_evidence_for

BASE = ROOT / "evals/step6/preview-final-v1"


def load_inputs():
    active = json.loads((ROOT / "evals/step6/release/active-pack.json").read_text())
    frozen = json.loads((BASE / "protocol.json").read_text())
    available = {c["id"]: c for c in json.loads((ROOT / active["dataset"]).read_text())["cases"]}
    cases = [available[cid] for cid in frozen["case_ids"]]
    bundle = load_case_bundle(cases, ROOT / active["policy_directory"])
    config = yaml.safe_load((ROOT / "evals/step6/direct-policy-v2/config.yaml").read_text())
    config["policy_assessment"] = "q05_stage_aware"
    original = {
        c["id"]: c
        for c in json.loads((ROOT / "evals/step6/context-v1/contexts.json").read_text())["cases"]
    }
    contexts = {c["id"]: context_for(c, original[c["id"]], "question_and_context") for c in cases}
    catalog = load_catalog(ROOT / "evals/step6/sources-v1/approved-sources.yaml")
    return frozen, cases, bundle, config, contexts, catalog


def validate_experiment():
    frozen = json.loads((BASE / "protocol.json").read_text())
    for name, expected in frozen["sha256"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f"Frozen preview measurement changed: {name}")
    inputs = load_inputs()
    _, cases, bundle, config, _, _ = inputs
    for case in cases:
        load_configuration(
            bundle, select_configuration(config, case["policy_id"], case.get("also_policy_ids", []))
        )
    return inputs


def summarize(rows):
    stats = abstention_summary(rows)
    stats["wrong_definitive"] = [
        [r["repeat"], r["id"]]
        for r in rows
        if r["result"]["decision"] not in ("evaluation_error", r["expected_composed"])
    ]
    stats["wrong_policy"] = [
        [r["repeat"], r["id"], p["policy_id"]]
        for r in rows
        for p in r["result"]["policies"]
        if p["policy_id"] in r["expected_by_policy"]
        and observed_policy(p) not in ("evaluation_error", r["expected_by_policy"][p["policy_id"]])
    ]
    return stats


async def evaluate(case, bundle, config, backend, contexts, catalog):
    loaded = load_configuration(
        bundle, select_configuration(config, case["policy_id"], case.get("also_policy_ids", []))
    )
    wrapped = ContextBackend(
        backend, case["request"], contexts[case["id"]], allow_context_egress=True
    )
    return await Evaluator(bundle, loaded, wrapped).evaluate(
        case["request"],
        evidence=source_evidence_for(case, catalog),
        egress=EgressPermit(digest(case["request"]), bundle.sha256, backend.transport),
    )


async def measure(output, ledger):
    frozen, cases, bundle, config, contexts, catalog = validate_experiment()
    output.mkdir(parents=True, exist_ok=False)
    before = ledger_total(ledger)
    ceiling = min(ledger.data["cap_usd"], before + frozen["additional_cap_usd"])
    backend = RestartMeteredBackend(
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
            "ceiling_usd": ceiling,
            "profile": "q05_stage_aware",
            "bundle_sha256": bundle.sha256,
        },
    )
    rows = []
    try:
        for rep in range(frozen["repeats"]):
            for case in cases:
                caller = RecordedBackend(
                    backend,
                    output / "provider-exchanges.jsonl",
                    f"{rep}/{case['id']}",
                    ledger,
                    ceiling,
                )
                result = await evaluate(case, bundle, config, caller, contexts, catalog)
                row = {
                    key: copy.deepcopy(case[key])
                    for key in ("id", "expected_composed", "expected_by_policy", "scope_by_policy")
                }
                row.update(repeat=rep, result=result)
                rows.append(row)
                with (output / "results.jsonl").open("a") as stream:
                    stream.write(json.dumps(row) + "\n")
                print(
                    json.dumps(
                        {
                            "repeat": rep,
                            "id": case["id"],
                            "decision": result["decision"],
                            "calls": len(caller.records),
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
                "complete": len(rows) == len(cases) * frozen["repeats"],
                "rows": len(rows),
                "results": summarize(rows),
                "passes": {
                    str(rep): summarize([r for r in rows if r["repeat"] == rep])
                    for rep in range(frozen["repeats"])
                },
                "provider_calls": backend.calls,
                "accounted_before_usd": before,
                "accounted_after_usd": ledger_total(ledger),
                "new_accounted_usd": ledger_total(ledger) - before,
                "unknown_charges": sum(c["cost_usd"] is None for c in ledger.data["calls"]),
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
        print(json.dumps({"cases": len(cases), "repeats": frozen["repeats"], "api_calls": 0}))
        return
    if args.output is None or args.output.exists() or not args.allow_external:
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
