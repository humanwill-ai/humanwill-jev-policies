"""Full reviewed pack: stage-routed tool wording versus bounded Q04."""

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
from humanwill_policies.providers import JevBackend

from .live_support import Ledger, credential, ledger_total
from .policy_isolation import RecordedBackend, StoredBackend, eligible_policies, evaluate
from .q05_full_pack import abstention_summary
from .question_context import sha256
from .restart_accounting import RestartMeteredBackend
from .reviewed_live import ROOT, observed_policy
from .run import select_configuration, write_json
from .source_approval import source_evidence_for
from .tool_probe import refine

PROTOCOL = ROOT / "evals/step6/stage-tool-v1/protocol.json"
ARMS = ("q04", "stage_tool")


def load_inputs():
    import yaml

    from .effect_question import context_for
    from .run import load_case_bundle
    from .source_approval import load_catalog

    cases = json.loads((ROOT / "evals/step6/release/reviewed-v1.json").read_text())["cases"]
    bundle = load_case_bundle(cases, ROOT / "evals/step6/policies-sources-v1")
    config = yaml.safe_load((ROOT / "evals/step6/direct-policy-v2/config.yaml").read_text())
    original = {
        c["id"]: c
        for c in json.loads((ROOT / "evals/step6/context-v1/contexts.json").read_text())["cases"]
    }
    contexts = {c["id"]: context_for(c, original[c["id"]], "question_and_context") for c in cases}
    catalog = load_catalog(ROOT / "evals/step6/sources-v1/approved-sources.yaml")
    return cases, bundle, config, catalog, contexts


def routed_arm(stage, arm):
    if arm not in ARMS:
        raise ValueError("Unknown arm")
    return "tool_wording" if arm == "stage_tool" and stage == "tool_action" else "q04"


def validate_experiment():
    frozen = json.loads(PROTOCOL.read_text())
    for path, expected in frozen["sha256"].items():
        if sha256(ROOT / path) != expected:
            raise ValueError(f"Frozen stage-tool input changed: {path}")
    inputs = load_inputs()
    if [c["id"] for c in inputs[0]] != frozen["case_ids"]:
        raise ValueError("Case ordering changed")
    return frozen, *inputs


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
            "comparison": "Shared fresh primary and shared non-tool follow-ups.",
        },
    )
    rows = []
    rng = random.Random(frozen["seed"])

    def save(case, result, rep, arm, notes):
        row = {
            k: copy.deepcopy(case[k])
            for k in ("id", "expected_composed", "expected_by_policy", "scope_by_policy")
        }
        row.update(result=result, repeat=rep, arm=arm, followup=notes)
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
                shared = None
                for arm in arms:
                    notes = {"eligible": [], "accepted": [], "rejected": {}, "calls": 0}
                    result = copy.deepcopy(first)
                    if shared is not None:
                        result, notes = copy.deepcopy(shared)
                        notes["shared_non_tool_followup"] = True
                    elif eligible_policies(first):
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
                            routed_arm(case["request"]["stage"], arm),
                            {},
                            branch,
                            config,
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
                    if case["request"]["stage"] != "tool_action":
                        shared = (result, notes)
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
                "results": summarize(rows, frozen["repeats"]),
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
