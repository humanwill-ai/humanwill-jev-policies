"""One complete context-only Jev pass, compared with the preserved first-pass baseline."""

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

from .live_support import ConcurrentMeteredBackend, Ledger, credential, ledger_total
from .question_context import ContextBackend, load_contexts, sha256
from .reviewed_live import ROOT, build_report, observed_policy, validate_protocol
from .run import select_configuration, write_json
from .source_approval import source_evidence_for

PROTOCOL = Path(__file__).parent / "context-v1/live-protocol.json"


def validate_experiment(baseline):
    frozen = json.loads(PROTOCOL.read_text())
    for path, expected in frozen["sha256"].items():
        if sha256(ROOT / path) != expected:
            raise ValueError(f"Context live protocol changed: {path}")
    for name, expected in frozen["baseline_artifacts_sha256"].items():
        if sha256(baseline / name) != expected:
            raise ValueError(f"Original result artifact changed: {name}")
    validated = validate_protocol()
    contexts = load_contexts()
    rows = [json.loads(line) for line in (baseline / "results.jsonl").read_text().splitlines()]
    if [r["id"] for r in rows] != [c["id"] for c in validated[1]]:
        raise ValueError("Baseline does not cover the exact accepted cases in order")
    return frozen, validated, contexts, rows


def model_scope_metrics(rows):
    """Raw scope answers and adapter rejection are distinct, overlapping measurements."""
    answers = correct = rejected_correct = rejected_wrong = 0
    mismatches = []
    for row in rows:
        for policy in row["result"]["policies"]:
            pid = policy["policy_id"]
            choice = policy["evidence"].get("choice")
            expected = row["scope_by_policy"].get(pid)
            if choice is None or expected is None:
                continue
            answers += 1
            matches = choice == expected
            correct += matches
            low = "low_confidence" in policy["reasons"]
            rejected_correct += low and matches
            rejected_wrong += low and not matches
            if not matches:
                mismatches.append(
                    {
                        "id": row["id"],
                        "policy_id": pid,
                        "expected": expected,
                        "choice": choice,
                        "confidence": policy["evidence"].get("confidence"),
                        "adapter_outcome": observed_policy(policy),
                    }
                )
    return {
        "answers": answers,
        "correct_choices": correct,
        "wrong_choices": answers - correct,
        "correct_choices_rejected_low_confidence": rejected_correct,
        "wrong_choices_rejected_low_confidence": rejected_wrong,
        "mismatches": mismatches,
    }


def compare(baseline, current):
    old = {r["id"]: r for r in baseline}
    if len(old) != len(baseline) or len({r["id"] for r in current}) != len(current):
        raise ValueError("Duplicate comparison case")
    changes = []
    policy_changes = []
    for row in current:
        prior = old[row["id"]]
        for key in ("expected_composed", "expected_by_policy", "scope_by_policy"):
            if prior[key] != row[key]:
                raise ValueError("Labels changed between runs")
        before, after = prior["result"]["decision"], row["result"]["decision"]
        if before != after:
            changes.append(
                {
                    "id": row["id"],
                    "expected": row["expected_composed"],
                    "before": before,
                    "after": after,
                    "fixed": after == row["expected_composed"],
                    "regressed": before == row["expected_composed"],
                }
            )
        prior_policies = {p["policy_id"]: p for p in prior["result"]["policies"]}
        for p in row["result"]["policies"]:
            pid = p["policy_id"]
            if pid not in row["expected_by_policy"]:
                continue
            before_p, after_p = observed_policy(prior_policies[pid]), observed_policy(p)
            if before_p != after_p:
                expected = row["expected_by_policy"][pid]
                policy_changes.append(
                    {
                        "id": row["id"],
                        "policy_id": pid,
                        "expected": expected,
                        "before": before_p,
                        "after": after_p,
                        "fixed": after_p == expected,
                        "regressed": before_p == expected,
                    }
                )
    return {
        "paired_events": len(current),
        "complete": len(current) == len(baseline),
        "fixed_events": sum(c["fixed"] for c in changes),
        "regressed_events": sum(c["regressed"] for c in changes),
        "event_changes": changes,
        "fixed_policy_outcomes": sum(c["fixed"] for c in policy_changes),
        "regressed_policy_outcomes": sum(c["regressed"] for c in policy_changes),
        "policy_changes": policy_changes,
        "baseline_model_scope": model_scope_metrics(baseline),
        "context_model_scope": model_scope_metrics(current),
        "limits": (
            "One observation per case per condition, measured at different times. "
            "No repeated control or independent holdout; cannot isolate run-to-run variability."
        ),
    }


async def measure(output, baseline, ledger):
    frozen, validated, contexts, old_rows = validate_experiment(baseline)
    original_protocol, cases, bundle, config, catalog = validated
    output.mkdir(parents=True, exist_ok=False)
    before = ledger_total(ledger)
    metered = ConcurrentMeteredBackend(JevBackend(config["provider"]), ledger)
    write_json(
        output / "manifest.json",
        {
            "format": "humanwill.context-run/1",
            "protocol": frozen,
            "original_protocol": original_protocol,
            "started_at": datetime.now(UTC).isoformat(),
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"])),
            "backend": "jev",
            "retries": 0,
            "case_count": len(cases),
            "counts_by_packet": dict(Counter(c["review_packet"] for c in cases)),
            "cost_before_usd": before,
        },
    )
    rows = []
    try:
        for case in cases:
            selected = select_configuration(
                config, case["policy_id"], case.get("also_policy_ids", [])
            )
            backend = ContextBackend(
                metered, case["request"], contexts[case["id"]], allow_context_egress=True
            )
            engine = Evaluator(bundle, load_configuration(bundle, selected), backend)
            result = await engine.evaluate(
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
                context_sha256=digest(contexts[case["id"]]["context"]),
            )
            rows.append(row)
            with (output / "results.jsonl").open("a") as stream:
                stream.write(json.dumps(row) + "\n")
            print(json.dumps({"case": case["id"], "observed": result["decision"]}), flush=True)
            if metered.fatal:
                break
    finally:
        write_json(
            output / "summary.json",
            build_report(rows, cases, metered, before, ledger_total(ledger)),
        )
        write_json(output / "comparison.json", compare(old_rows, rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--keychain-helper", type=Path)
    args = parser.parse_args()
    validate_experiment(args.baseline)
    if not args.allow_external:
        parser.error("Explicit synthetic event and context egress flag required")
    credential(args.keychain_helper)
    path = ROOT / "artifacts/quality/spending.json"
    try:
        with path.with_suffix(".lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            asyncio.run(measure(args.output, args.baseline, Ledger(path)))
    finally:
        os.environ.pop("OPENROUTER_API_KEY", None)


if __name__ == "__main__":
    main()
