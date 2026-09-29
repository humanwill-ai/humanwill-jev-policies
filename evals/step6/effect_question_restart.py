"""Owner-authorized fresh restart; unchanged experiment and explicit carried reservation."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from humanwill_policies import load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import JevBackend
from humanwill_policies.runtime import EgressPermit
from humanwill_policies.serialization import digest

from .context_live import compare
from .effect_question import EffectBackend, context_for
from .effect_question_live import validate_experiment as validate_previous
from .live_support import Ledger, credential, ledger_total
from .question_context import ContextBackend, sha256
from .restart_accounting import RestartMeteredBackend
from .reviewed_live import ROOT, build_report
from .run import select_configuration, write_json
from .source_approval import source_evidence_for

PROTOCOL = ROOT / "evals/step6/effect-question-restart-v1/protocol.json"
CONDITIONS = ("question_only", "question_and_context")


def validate_experiment(original, baseline):
    frozen = json.loads(PROTOCOL.read_text())
    for path, expected in frozen["sha256"].items():
        if sha256(ROOT / path) != expected:
            raise ValueError(f"Frozen restart input changed: {path}")
    _, validated, contexts, rows = validate_previous(original, baseline)
    return frozen, validated, contexts, rows


async def measure(output, original, baseline, ledger):
    frozen, validated, contexts, previous = validate_experiment(original, baseline)
    cases, bundle, config, catalog = validated
    output.mkdir(parents=True, exist_ok=False)
    before = ledger_total(ledger)
    backends = {
        condition: RestartMeteredBackend(
            JevBackend(config["provider"]),
            ledger,
            {int(k): v for k, v in frozen["carried_reservations"].items()},
        )
        for condition in CONDITIONS
    }
    rows = {condition: [] for condition in CONDITIONS}
    for condition in CONDITIONS:
        (output / condition).mkdir()
    write_json(
        output / "manifest.json",
        {
            "format": "humanwill.effect-question-restart/1",
            "protocol": frozen,
            "started_at": datetime.now(UTC).isoformat(),
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "accounted_before_usd": before,
            "restart_of": "artifacts/quality/effect-question-live-v1",
            "retries": 0,
            "order": "Case order retained; condition order alternates by case index.",
        },
    )
    try:
        for index, case in enumerate(cases):
            order = CONDITIONS if index % 2 == 0 else CONDITIONS[::-1]
            for condition in order:
                metered = backends[condition]
                record = context_for(case, contexts[case["id"]], condition)
                backend = ContextBackend(
                    EffectBackend(
                        metered, case["id"], output / condition / "provider-exchanges.jsonl"
                    ),
                    case["request"],
                    record,
                    allow_context_egress=True,
                )
                selected = select_configuration(
                    config, case["policy_id"], case.get("also_policy_ids", [])
                )
                result = await Evaluator(
                    bundle,
                    load_configuration(bundle, selected),
                    backend,
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
                    context_sha256=digest(record["context"]),
                )
                rows[condition].append(row)
                with (output / condition / "results.jsonl").open("a") as stream:
                    stream.write(json.dumps(row) + "\n")
                print(
                    json.dumps(
                        {"case": case["id"], "condition": condition, "observed": result["decision"]}
                    ),
                    flush=True,
                )
                if metered.fatal:
                    return
    finally:
        for condition in CONDITIONS:
            backend = backends[condition]
            cost = sum(c.get("usage", {}).get("cost", 0) or 0 for c in backend.calls)
            write_json(
                output / condition / "summary.json",
                build_report(rows[condition], cases, backend, 0, cost),
            )
            write_json(output / condition / "comparison.json", compare(previous, rows[condition]))
        if all(len(rows[c]) == len(cases) for c in CONDITIONS):
            write_json(
                output / "between-conditions.json",
                compare(rows[CONDITIONS[0]], rows[CONDITIONS[1]]),
            )
        write_json(
            output / "accounting.json",
            {
                "accounted_before_usd": before,
                "accounted_after_usd": ledger_total(ledger),
                "new_accounted_usd": ledger_total(ledger) - before,
                "known_spend_usd": ledger.data["prior_smoke_usd"]
                + sum(c["cost_usd"] or 0 for c in ledger.data["calls"]),
                "unresolved_reservations_usd": sum(
                    c["reserved_usd"] for c in ledger.data["calls"] if c["cost_usd"] is None
                ),
                "calls": sum(len(b.calls) for b in backends.values()),
                "unknown_charges": sum(c["cost_usd"] is None for c in ledger.data["calls"]),
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--keychain-helper", type=Path)
    args = parser.parse_args()
    _, validated, _, _ = validate_experiment(args.original, args.baseline)
    if args.validate_only:
        print(
            json.dumps(
                {"valid_cases": len(validated[0]), "conditions": CONDITIONS, "provider_calls": 0}
            )
        )
        return
    if args.output is None or args.output.exists():
        parser.error("New output directory required")
    if subprocess.check_output(["git", "status", "--porcelain"]):
        parser.error("Commit the frozen experiment before live execution")
    if not args.allow_external:
        parser.error("Explicit synthetic event/context egress flag required")
    credential(args.keychain_helper)
    path = ROOT / "artifacts/quality/spending.json"
    try:
        with path.with_suffix(".lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            frozen = json.loads(PROTOCOL.read_text())
            if sha256(path) != frozen["starting_ledger_sha256"]:
                raise ValueError("Starting ledger changed; freeze a new restart protocol")
            asyncio.run(measure(args.output, args.original, args.baseline, Ledger(path)))
    finally:
        os.environ.pop("OPENROUTER_API_KEY", None)


if __name__ == "__main__":
    main()
