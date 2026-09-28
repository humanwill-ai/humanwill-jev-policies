"""First-pass live Jev assessment of the owner-reviewed packets; no retries or tuning."""

import argparse
import asyncio
import copy
import fcntl
import hashlib
import json
import os
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import yaml

from humanwill_policies import load_configuration
from humanwill_policies.contracts import validate_contract
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import JevBackend
from humanwill_policies.runtime import EgressPermit
from humanwill_policies.serialization import digest

from .gates import evaluator_sources
from .live_support import ConcurrentMeteredBackend, Ledger, credential, ledger_total
from .metrics import summarize
from .run import load_case_bundle, select_configuration, write_json
from .source_approval import load_catalog, source_evidence_for

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evals/step6"
PROTOCOL = BASE / "release/reviewed-live-v1-protocol.json"
DATASET = BASE / "release/reviewed-v1.json"
REVIEW = BASE / "release/owner-review-v1.json"
CONFIG = BASE / "config-sources-v1.yaml"
POLICIES = BASE / "policies-sources-v1"
CATALOG = BASE / "sources-v1/approved-sources.yaml"
LIMIT = "not_assessable: owner-reviewed targeted/regression cases, not independent traffic sampling"


def source_hashes():
    result = evaluator_sources()
    for name in ["source_approval.py", "live_support.py", "review_import.py", "reviewed_live.py"]:
        p = BASE / name
        result[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def validate_protocol():
    protocol = json.loads(PROTOCOL.read_text())
    for path, expected in protocol["sha256"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Frozen review/configuration changed: {path}")
    if protocol["source_sha256"] != source_hashes():
        raise ValueError("Frozen evaluator/runner changed")
    review = json.loads(REVIEW.read_text())
    data = json.loads(DATASET.read_text())
    if (
        protocol["status"] != "owner_labels_accepted"
        or review["status"] != "owner_labels_accepted"
        or data["format"] != "humanwill.reviewed-dataset/1"
        or data["synthetic"] is not True
    ):
        raise ValueError("Missing accepted synthetic review")
    cases = data["cases"]
    ids = [c["id"] for c in cases]
    if (
        len(ids) != len(set(ids))
        or ids != review["approved_case_ids"]
        or len(ids) != protocol["case_count"]
    ):
        raise ValueError("Accepted case set changed")
    if set(ids) & {r["id"] for r in review["removed"]}:
        raise ValueError("Removed case reintroduced")
    bundle = load_case_bundle(cases, POLICIES)
    if bundle.sha256 != protocol["bundle_sha256"]:
        raise ValueError("Frozen policies changed")
    config = yaml.safe_load(CONFIG.read_text())
    catalog = load_catalog(CATALOG)
    for case in cases:
        validate_contract("request", case["request"])
        active = {case["policy_id"], *case.get("also_policy_ids", [])}
        if active != set(case["expected_by_policy"]) or active != set(case["scope_by_policy"]):
            raise ValueError("Expected judgments do not match active policies")
        selected = select_configuration(config, case["policy_id"], case.get("also_policy_ids", []))
        load_configuration(bundle, selected)
        source_evidence_for(case, catalog)
    return protocol, cases, bundle, config, catalog


def observed_policy(row):
    if row["judgment"] == "violation":
        return "block"
    return "evaluation_error" if row["status"] == "error" else "allow"


def metrics(rows):
    result = summarize(rows)
    result["release_gate"] = LIMIT
    result["interval_limit"] = (
        "Nominal Wilson bounds only; selected, related scenarios "
        "are not random independent observations."
    )
    return result


def build_report(rows, cases, backend, before, after):
    # Each event/cost appears exactly once here. Per-policy summaries below do not
    # attribute shared API cost/latency to individual policies.
    event_rows, policy_rows = [], []
    for row in rows:
        event_rows.append(
            {
                **row,
                "expected": row["expected_composed"],
                "expected_scope": None,
                "observed_scope": None,
            }
        )
        for pid, expected in row["expected_by_policy"].items():
            policy = next(p for p in row["result"]["policies"] if p["policy_id"] == pid)
            view = copy.deepcopy(row["result"])
            view.update(decision=observed_policy(policy), evaluation={"batches": []})
            policy_rows.append(
                {
                    **row,
                    "policy_id": pid,
                    "expected": expected,
                    "expected_scope": row["scope_by_policy"][pid],
                    "observed_scope": policy["evidence"].get("choice"),
                    "result": view,
                }
            )
    per_policy = {}
    for pid in sorted({r["policy_id"] for r in policy_rows}):
        values = metrics([r for r in policy_rows if r["policy_id"] == pid])
        for key in [
            "latency_ms",
            "calls",
            "known_api_cost_usd",
            "unknown_cost_calls",
            "api_cost_per_1000_cases",
            "returned_models",
        ]:
            values.pop(key)
        per_policy[pid] = values
    return {
        "complete": len(rows) == len(cases),
        "events": metrics(event_rows),
        "by_policy": per_policy,
        "by_packet": {
            p: metrics([r for r in event_rows if r["review_packet"] == p])
            for p in sorted({c["review_packet"] for c in cases})
        },
        "exact_event_matches": sum(r["result"]["decision"] == r["expected_composed"] for r in rows),
        "cost_before_usd": before,
        "cost_after_usd": after,
        "new_cost_usd": after - before,
        "accounting_stopped": backend.fatal,
        "provider_calls": backend.calls,
        "event_mismatches": [
            {"id": r["id"], "expected": r["expected_composed"], "observed": r["result"]["decision"]}
            for r in rows
            if r["result"]["decision"] != r["expected_composed"]
        ],
        "policy_mismatches": [
            {
                "id": r["id"],
                "policy_id": r["policy_id"],
                "expected": r["expected"],
                "observed": r["result"]["decision"],
            }
            for r in policy_rows
            if r["result"]["decision"] != r["expected"]
        ],
        "limits": LIMIT,
    }


async def measure(output, ledger):
    protocol, cases, bundle, config, catalog = validate_protocol()
    output.mkdir(parents=True, exist_ok=False)
    before = ledger_total(ledger)
    backend = ConcurrentMeteredBackend(JevBackend(config["provider"]), ledger)
    manifest = {
        "format": "humanwill.reviewed-run/1",
        "protocol": protocol,
        "started_at": datetime.now(UTC).isoformat(),
        "backend": "jev",
        "retries": 0,
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"])),
        "case_count": len(cases),
        "counts_by_packet": dict(Counter(c["review_packet"] for c in cases)),
        "cost_before_usd": before,
        "limits": LIMIT,
    }
    write_json(output / "manifest.json", manifest)
    rows = []
    try:
        for case in cases:
            selected = select_configuration(
                config, case["policy_id"], case.get("also_policy_ids", [])
            )
            engine = Evaluator(bundle, load_configuration(bundle, selected), backend)
            result = await engine.evaluate(
                case["request"],
                evidence=source_evidence_for(case, catalog),
                egress=EgressPermit(digest(case["request"]), bundle.sha256, backend.transport),
            )
            row = {
                k: copy.deepcopy(case[k])
                for k in [
                    "id",
                    "policy_id",
                    "family",
                    "language",
                    "tags",
                    "review_packet",
                    "expected_by_policy",
                    "scope_by_policy",
                    "expected_composed",
                ]
            }
            row.update(stage=case["request"]["stage"], result=result)
            rows.append(row)
            with (output / "results.jsonl").open("a") as stream:
                stream.write(json.dumps(row) + "\n")
            print(
                json.dumps(
                    {
                        "case": case["id"],
                        "expected": case["expected_composed"],
                        "observed": result["decision"],
                    }
                ),
                flush=True,
            )
            if backend.fatal:
                break
    finally:
        write_json(
            output / "summary.json",
            build_report(rows, cases, backend, before, ledger_total(ledger)),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--keychain-helper", type=Path)
    args = parser.parse_args()
    validate_protocol()
    if not args.allow_external:
        parser.error("Explicit synthetic egress flag required")
    credential(args.keychain_helper)
    path = ROOT / "artifacts/quality/spending.json"
    try:
        with path.with_suffix(".lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            asyncio.run(measure(args.output, Ledger(path)))
    finally:
        os.environ.pop("OPENROUTER_API_KEY", None)


if __name__ == "__main__":
    main()
