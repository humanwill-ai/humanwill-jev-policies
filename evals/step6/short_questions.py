"""Ten brief scope templates; frozen policies/events/context and fresh long control."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
import random
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from humanwill_policies import load_configuration
from humanwill_policies.errors import PolicyError
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import JevBackend
from humanwill_policies.runtime import EgressPermit
from humanwill_policies.serialization import canonical, digest

from .effect_question import context_for
from .effect_question import transform as long_question
from .effect_question_restart import validate_experiment as validate_previous
from .live_support import Ledger, credential, ledger_total
from .question_context import ContextBackend, sha256
from .restart_accounting import RestartMeteredBackend
from .reviewed_live import ROOT, observed_policy
from .run import select_configuration, write_json
from .source_approval import source_evidence_for
from .threshold_replay import validate_rows

DIRECTORY = ROOT / "evals/step6/short-questions-v1"
VARIANTS = DIRECTORY / "variants.json"
PROTOCOL = DIRECTORY / "protocol.json"


def transform(payload, variant_id):
    if variant_id == "control":
        return long_question(payload)
    spec = json.loads(VARIANTS.read_text())
    variant = next((v for v in spec["variants"] if v["id"] == variant_id), None)
    if variant is None:
        raise ValueError("Unknown short-question variant")
    result = copy.deepcopy(payload)
    for q in result["questions"].values():
        if set(q["criteria"]) != set(variant["criteria"]):
            raise PolicyError("unsupported_experiment", "Only scoped predicates supported")
        q["instructions"]["task"] = variant["task"]
        q["instructions"]["boundary"] = spec["boundary"]
        q["instructions"]["trusted_conditions"]["meaning"] = spec["trusted_conditions_meaning"]
        q["criteria"] = copy.deepcopy(variant["criteria"])
    if len(canonical(result).encode()) > 24000:
        raise PolicyError("batch_limit", "Short-question payload exceeds limit")
    return result


class VariantBackend:
    def __init__(self, delegate, variant_id, run_id, exchanges=None):
        self.delegate, self.variant_id = delegate, variant_id
        self.run_id, self.exchanges = run_id, exchanges
        self.transport, self.model = delegate.transport, delegate.model
        self.accepted_models = delegate.accepted_models

    async def evaluate(self, payload, **kwargs):
        request = transform(payload, self.variant_id)
        exchange = {"run_id": self.run_id, "variant": self.variant_id, "payload": request}
        try:
            response = await self.delegate.evaluate(request, **kwargs)
            exchange["raw_response"] = response
            return response
        except PolicyError as exc:
            exchange["error"] = exc.code
            raise
        except asyncio.CancelledError:
            exchange["error"] = "cancelled_before_response"
            raise
        finally:
            if self.exchanges is not None:
                with self.exchanges.open("a") as stream:
                    stream.write(json.dumps(exchange) + "\n")


def validate_experiment():
    frozen = json.loads(PROTOCOL.read_text())
    for path, expected in frozen["sha256"].items():
        if sha256(ROOT / path) != expected:
            raise ValueError(f"Frozen short-question input changed: {path}")
    _, validated, contexts, _ = validate_previous(
        ROOT / "artifacts/quality/direct-policy-live-v1",
        ROOT / "artifacts/quality/focused-policy-live-v1",
    )
    cases, bundle, config, catalog = validated
    contexts = {c["id"]: context_for(c, contexts[c["id"]], "question_and_context") for c in cases}
    previous = [
        json.loads(line) for line in (ROOT / frozen["recorded_results"]).read_text().splitlines()
    ]
    validate_rows(cases, previous, contexts)
    failing = [r["id"] for r in previous if r["result"]["decision"] != r["expected_composed"]]
    if failing != frozen["failing_ids"]:
        raise ValueError("Failing case selection changed")
    chosen = frozen["failing_ids"] + frozen["control_ids"]
    if len(chosen) != len(set(chosen)):
        raise ValueError("Duplicate selected case")
    by_id = {c["id"]: c for c in cases}
    conditions = ["control"] + [v["id"] for v in json.loads(VARIANTS.read_text())["variants"]]
    if len(conditions) != 11 or len(set(conditions)) != 11:
        raise ValueError("Expected ten variants plus the long control")
    schedule = [
        (v, cid, repeat)
        for v in conditions
        for cid in chosen
        for repeat in range(frozen["repeats"])
    ]
    random.Random(frozen["seed"]).shuffle(schedule)
    if digest(schedule) != frozen["schedule_sha256"]:
        raise ValueError("Frozen schedule changed")
    return frozen, [by_id[cid] for cid in chosen], bundle, config, catalog, contexts, schedule


def summarize(rows, frozen):
    result = {}
    for variant in sorted({r["variant"] for r in rows}):
        selected = [r for r in rows if r["variant"] == variant]
        stats = {}
        for group, ids in {
            "all": None,
            "failing": frozen["failing_ids"],
            "focus_five": frozen["focus_ids"],
            "controls": frozen["control_ids"],
        }.items():
            subset = [r for r in selected if ids is None or r["id"] in ids]
            stats[group] = {
                "attempts": len(subset),
                "exact": sum(r["result"]["decision"] == r["expected"] for r in subset),
                "false_blocks": sum(
                    r["expected"] == "allow" and r["result"]["decision"] != "allow" for r in subset
                ),
                "missed_violations": sum(
                    r["expected"] == "block" and r["result"]["decision"] == "allow" for r in subset
                ),
                "unknown_allowed": sum(
                    r["expected"] == "evaluation_error" and r["result"]["decision"] == "allow"
                    for r in subset
                ),
            }
        pairs = [[r for r in selected if r["id"] == cid] for cid in {r["id"] for r in selected}]
        stats["both_repeats_exact"] = sum(
            len(pair) == frozen["repeats"]
            and all(r["result"]["decision"] == r["expected"] for r in pair)
            for pair in pairs
        )
        stats["decision_disagreements"] = sum(
            len({r["result"]["decision"] for r in pair}) > 1 for pair in pairs
        )
        stats["errors"] = dict(Counter(e["code"] for r in selected for e in r["result"]["errors"]))
        stats["policy_missed_violations"] = sum(
            r["expected_by_policy"][p["policy_id"]] == "block" and observed_policy(p) == "allow"
            for r in selected
            for p in r["result"]["policies"]
            if p["policy_id"] in r["expected_by_policy"]
        )
        stats["policy_unknown_allowed"] = sum(
            r["expected_by_policy"][p["policy_id"]] == "evaluation_error"
            and observed_policy(p) == "allow"
            for r in selected
            for p in r["result"]["policies"]
            if p["policy_id"] in r["expected_by_policy"]
        )
        result[variant] = stats
    return result


async def measure(output, ledger):
    frozen, cases, bundle, config, catalog, contexts, schedule = validate_experiment()
    by_id = {c["id"]: c for c in cases}
    output.mkdir(parents=True, exist_ok=False)
    before = ledger_total(ledger)
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
            "schedule": schedule,
            "retries": 0,
        },
    )
    rows = []
    try:
        for variant, cid, repeat in schedule:
            case = by_id[cid]
            run_id = f"{variant}/{cid}/{repeat}"
            backend = ContextBackend(
                VariantBackend(metered, variant, run_id, output / "provider-exchanges.jsonl"),
                case["request"],
                contexts[cid],
                allow_context_egress=True,
            )
            selected = select_configuration(
                config, case["policy_id"], case.get("also_policy_ids", [])
            )
            result = await Evaluator(
                bundle, load_configuration(bundle, selected), backend
            ).evaluate(
                case["request"],
                evidence=source_evidence_for(case, catalog),
                egress=EgressPermit(digest(case["request"]), bundle.sha256, backend.transport),
            )
            row = {
                "run_id": run_id,
                "id": cid,
                "variant": variant,
                "repeat": repeat,
                "expected": case["expected_composed"],
                "expected_by_policy": case["expected_by_policy"],
                "scope_by_policy": case["scope_by_policy"],
                "result": result,
            }
            rows.append(row)
            with (output / "results.jsonl").open("a") as stream:
                stream.write(json.dumps(row) + "\n")
            print(
                json.dumps(
                    {"completed": len(rows), "run_id": run_id, "decision": result["decision"]}
                ),
                flush=True,
            )
            if metered.fatal:
                break
    finally:
        write_json(
            output / "summary.json",
            {
                "complete": len(rows) == len(schedule),
                "completed": len(rows),
                "planned": len(schedule),
                "variants": summarize(rows, frozen),
                "accounted_before_usd": before,
                "accounted_after_usd": ledger_total(ledger),
                "new_accounted_usd": ledger_total(ledger) - before,
                "known_total_usd": ledger.data["prior_smoke_usd"]
                + sum(c["cost_usd"] or 0 for c in ledger.data["calls"]),
                "unknown_charges": sum(c["cost_usd"] is None for c in ledger.data["calls"]),
                "provider_calls": metered.calls,
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--keychain-helper", type=Path)
    args = parser.parse_args()
    frozen, cases, *_, schedule = validate_experiment()
    if args.validate_only:
        print(json.dumps({"cases": len(cases), "planned_calls": len(schedule), "api_calls": 0}))
        return
    if args.output is None or args.output.exists():
        parser.error("New output directory required")
    if subprocess.check_output(["git", "status", "--porcelain"]):
        parser.error("Commit frozen experiment before live execution")
    if not args.allow_external:
        parser.error("Explicit synthetic event/context egress flag required")
    credential(args.keychain_helper)
    path = ROOT / "artifacts/quality/spending.json"
    try:
        with path.with_suffix(".lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if sha256(path) != frozen["starting_ledger_sha256"]:
                raise ValueError("Ledger changed since experiment freeze")
            asyncio.run(measure(args.output, Ledger(path)))
    finally:
        os.environ.pop("OPENROUTER_API_KEY", None)


if __name__ == "__main__":
    main()
