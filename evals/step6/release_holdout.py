"""Measure one frozen, owner-reviewed synthetic tranche without tuning or retries."""

import argparse
import asyncio
import copy
import fcntl
import hashlib
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

from .gates import evaluator_sources
from .live_support import ConcurrentMeteredBackend, Ledger, credential, ledger_total
from .metrics import summarize
from .run import evidence_for, load_case_bundle, load_cases, select_configuration, write_json

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "evals/step6/release/holdout-v1.json"
PROTOCOL = ROOT / "evals/step6/release/holdout-v1-protocol.json"
CONFIG = ROOT / "evals/step6/config-disclosure-v2.yaml"
POLICIES = ROOT / "evals/step6/policies-v2"


def validate_protocol(require_review=True):
    protocol = json.loads(PROTOCOL.read_text())
    cases = load_cases(DATASET, allowed_splits={"holdout_pending_review"})
    bundle = load_case_bundle(cases, POLICIES)
    config = yaml.safe_load(CONFIG.read_text())
    if (
        hashlib.sha256(DATASET.read_bytes()).hexdigest() != protocol["dataset_sha256"]
        or hashlib.sha256(CONFIG.read_bytes()).hexdigest() != protocol["config_sha256"]
        or bundle.sha256 != protocol["bundle_sha256"]
        or evaluator_sources() != protocol["source_sha256"]
    ):
        raise ValueError("Frozen data/configuration/evaluator changed; do not evaluate")
    if require_review and (
        protocol["status"] != "owner_labels_accepted" or not protocol.get("review_record")
    ):
        raise ValueError(
            "New labels await owner review; previous 36-case approval does not cover them"
        )
    for case in cases:
        load_configuration(bundle, select_configuration(config, case["policy_id"]))
    return protocol, cases, bundle, config


async def measure(output, ledger):
    protocol, cases, bundle, config = validate_protocol()
    output.mkdir(parents=True, exist_ok=False)
    before = ledger_total(ledger)
    backend = ConcurrentMeteredBackend(JevBackend(config["provider"]), ledger)
    manifest = {
        "format": "humanwill.frozen-tranche/1",
        "protocol": protocol,
        "started_at": datetime.now(UTC).isoformat(),
        "backend": "jev",
        "retries": 0,
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"])),
        "case_count": len(cases),
        "cost_before_usd": before,
        "runner_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__), ROOT / "evals/step6/live_support.py"]
        },
        "release_gate": "not_assessable: targeted small sample; no independent population sampling",
    }
    write_json(output / "manifest.json", manifest)
    rows = []
    try:
        for case in cases:
            selected = select_configuration(config, case["policy_id"])
            evaluator = Evaluator(bundle, load_configuration(bundle, selected), backend)
            result = await evaluator.evaluate(
                case["request"],
                evidence=evidence_for(case),
                egress=EgressPermit(digest(case["request"]), bundle.sha256, backend.transport),
            )
            policy = next(p for p in result["policies"] if p["policy_id"] == case["policy_id"])
            row = {
                key: copy.deepcopy(case[key])
                for key in [
                    "id",
                    "policy_id",
                    "family",
                    "language",
                    "tags",
                    "expected",
                    "expected_scope",
                    "rationale",
                ]
            }
            row.update(
                repeat=0,
                stage=case["request"]["stage"],
                result=result,
                observed_scope=policy["evidence"].get("choice"),
            )
            rows.append(row)
            with (output / "results.jsonl").open("a") as file:
                file.write(json.dumps(row) + "\n")
            print(
                json.dumps(
                    {
                        "case": case["id"],
                        "expected": case["expected"],
                        "observed": result["decision"],
                    }
                ),
                flush=True,
            )
            if backend.fatal:
                break
    finally:
        report = {
            "complete": len(rows) == len(cases),
            "by_policy": {},
            "cost_before_usd": before,
            "cost_after_usd": ledger_total(ledger),
            "new_cost_usd": ledger_total(ledger) - before,
            "accounting_stopped": backend.fatal,
            "limits": manifest["release_gate"],
            "provider_calls": backend.calls,
        }
        for pid in sorted({c["policy_id"] for c in cases}):
            report["by_policy"][pid] = summarize([r for r in rows if r["policy_id"] == pid])
            # Shared summarize() labels all legacy input as development. Override only
            # provenance text, never numeric targets or release suitability.
            report["by_policy"][pid]["release_gate"] = manifest["release_gate"]
            report["by_policy"][pid]["interval_limit"] = (
                "Nominal Wilson bounds; targeted command families are not random traffic samples."
            )
        write_json(output / "summary.json", report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--keychain-helper", type=Path)
    parser.add_argument("--allow-external", action="store_true")
    args = parser.parse_args()
    validate_protocol()
    if not args.allow_external:
        parser.error("Explicit synthetic egress authorization required")
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
