"""Frozen Q05 full reviewed-pack measurement; one pass, no retries or tuning."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from humanwill_policies import load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import JevBackend
from humanwill_policies.runtime import EgressPermit
from humanwill_policies.serialization import digest

from .effect_question import context_for
from .live_support import Ledger, credential, ledger_total
from .question_context import ContextBackend, sha256
from .restart_accounting import RestartMeteredBackend
from .reviewed_live import ROOT, build_report
from .run import select_configuration, write_json
from .short_questions import VariantBackend, validate_previous
from .short_questions import validate_experiment as validate_short
from .source_approval import source_evidence_for

PROTOCOL = ROOT / "evals/step6/q05-full-pack-v1/protocol.json"


def validate_experiment():
    frozen = json.loads(PROTOCOL.read_text())
    for path, expected in frozen["sha256"].items():
        if sha256(ROOT / path) != expected:
            raise ValueError(f"Frozen Q05 input changed: {path}")
    validate_short()
    _, validated, contexts, _ = validate_previous(
        ROOT / "artifacts/quality/direct-policy-live-v1",
        ROOT / "artifacts/quality/focused-policy-live-v1",
    )
    cases, bundle, config, catalog = validated
    if [c["id"] for c in cases] != frozen["case_ids"]:
        raise ValueError("Full reviewed case set or order changed")
    contexts = {c["id"]: context_for(c, contexts[c["id"]], "question_and_context") for c in cases}
    return frozen, cases, bundle, config, catalog, contexts


def abstention_summary(rows):
    groups = {}
    for expected in ("allow", "block", "evaluation_error"):
        selected = [r for r in rows if r["expected_composed"] == expected]
        groups[expected] = {
            "cases": len(selected),
            "observed": dict(Counter(r["result"]["decision"] for r in selected)),
        }
    errors = [r for r in rows if r["result"]["decision"] == "evaluation_error"]
    return {
        "total": len(rows),
        "conclusive": len(rows) - len(errors),
        "abstentions": len(errors),
        "expected_abstentions": sum(r["expected_composed"] == "evaluation_error" for r in errors),
        "unexpected_abstentions": sum(r["expected_composed"] != "evaluation_error" for r in errors),
        "by_expected": groups,
        "abstention_reason_sets": dict(
            Counter(
                ",".join(
                    sorted(
                        {
                            reason
                            for p in r["result"]["policies"]
                            if p["status"] == "error"
                            for reason in p["reasons"]
                        }
                    )
                )
                for r in errors
            )
        ),
    }


async def measure(output, ledger):
    frozen, cases, bundle, config, catalog, contexts = validate_experiment()
    output.mkdir(parents=True, exist_ok=False)
    before = ledger_total(ledger)
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
            "retries": 0,
        },
    )
    rows = []
    try:
        for case in cases:
            cid = case["id"]
            wrapped = ContextBackend(
                VariantBackend(backend, "q05", cid, output / "provider-exchanges.jsonl"),
                case["request"],
                contexts[cid],
                allow_context_egress=True,
            )
            selected = select_configuration(
                config, case["policy_id"], case.get("also_policy_ids", [])
            )
            result = await Evaluator(
                bundle, load_configuration(bundle, selected), wrapped
            ).evaluate(
                case["request"],
                evidence=source_evidence_for(case, catalog),
                egress=EgressPermit(digest(case["request"]), bundle.sha256, backend.transport),
            )
            row = {
                k: copy.deepcopy(case[k])
                for k in (
                    "id",
                    "policy_id",
                    "family",
                    "language",
                    "tags",
                    "review_packet",
                    "expected_by_policy",
                    "scope_by_policy",
                    "expected_composed",
                )
            }
            row.update(
                stage=case["request"]["stage"],
                result=result,
                context_sha256=digest(contexts[cid]["context"]),
            )
            rows.append(row)
            with (output / "results.jsonl").open("a") as stream:
                stream.write(json.dumps(row) + "\n")
            print(
                json.dumps({"completed": len(rows), "case": cid, "decision": result["decision"]}),
                flush=True,
            )
            if backend.fatal:
                break
    finally:
        after = ledger_total(ledger)
        report = build_report(rows, cases, backend, before, after)
        report["abstention"] = abstention_summary(rows)
        report["accounting"] = {
            "known_total_usd": ledger.data["prior_smoke_usd"]
            + sum(c["cost_usd"] or 0 for c in ledger.data["calls"]),
            "unknown_charges": sum(c["cost_usd"] is None for c in ledger.data["calls"]),
            "accounted_total_usd": after,
            "remaining_unreserved_usd": ledger.data["cap_usd"] - after,
        }
        write_json(output / "summary.json", report)


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
                {"cases": len(cases), "planned_calls": frozen["planned_calls"], "api_calls": 0}
            )
        )
        return
    if args.output is None or args.output.exists():
        parser.error("New output directory required")
    if subprocess.check_output(["git", "status", "--porcelain"]):
        parser.error("Commit frozen experiment before live execution")
    if not args.allow_external:
        parser.error("Explicit synthetic event/context egress flag required")
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
