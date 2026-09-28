"""One frozen full-policy Jev pass against all accepted cases; no retries or tuning."""

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

import yaml

from humanwill_policies import load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import JevBackend
from humanwill_policies.runtime import EgressPermit
from humanwill_policies.serialization import digest

from .context_live import compare
from .gates import evaluator_sources
from .live_support import ConcurrentMeteredBackend, Ledger, credential, ledger_total
from .question_context import ContextBackend, build_pack, sha256
from .reviewed_live import BASE, CATALOG, DATASET, POLICIES, REVIEW, ROOT, build_report
from .run import load_case_bundle, select_configuration, write_json
from .source_approval import load_catalog, source_evidence_for
from .threshold_replay import validate_rows

PROTOCOL = BASE / "direct-policy-v1/live-protocol.json"
CONFIG = BASE / "direct-policy-v1/config.yaml"


def source_hashes():
    result = evaluator_sources()
    for name in [
        "source_approval.py",
        "live_support.py",
        "reviewed_live.py",
        "context_live.py",
        "question_context.py",
        "threshold_replay.py",
        "direct_policy_live.py",
        "gates.py",
    ]:
        path = BASE / name
        result[str(path.relative_to(ROOT))] = sha256(path)
    return result


def validate_experiment(baseline):
    frozen = json.loads(PROTOCOL.read_text())
    for path, expected in frozen["sha256"].items():
        if sha256(ROOT / path) != expected:
            raise ValueError(f"Frozen direct-policy input changed: {path}")
    if source_hashes() != frozen["source_sha256"]:
        raise ValueError("Frozen direct-policy evaluator/runner changed")
    for name, expected in frozen["baseline_artifacts_sha256"].items():
        if sha256(baseline / name) != expected:
            raise ValueError(f"Context baseline artifact changed: {name}")
    data, review = json.loads(DATASET.read_text()), json.loads(REVIEW.read_text())
    cases = data["cases"]
    ids = [c["id"] for c in cases]
    if (
        data["synthetic"] is not True
        or review["status"] != "owner_labels_accepted"
        or ids != review["approved_case_ids"]
        or len(ids) != len(set(ids))
        or len(ids) != frozen["case_count"]
        or set(ids) & {r["id"] for r in review["removed"]}
    ):
        raise ValueError("Accepted synthetic case set changed")
    bundle = load_case_bundle(cases, POLICIES)
    if bundle.sha256 != frozen["bundle_sha256"]:
        raise ValueError("Frozen policy text changed")
    config = yaml.safe_load(CONFIG.read_text())
    pack = json.loads((BASE / "context-v1/contexts.json").read_text())
    observations = json.loads((BASE / "context-v1/observations.json").read_text())["cases"]
    if pack != build_pack(cases, observations):
        raise ValueError("Context differs from frozen event observations")
    contexts = {c["id"]: c for c in pack["cases"]}
    catalog = load_catalog(CATALOG)
    for case in cases:
        selected = select_configuration(config, case["policy_id"], case.get("also_policy_ids", []))
        load_configuration(bundle, selected)
        source_evidence_for(case, catalog)
    rows = [json.loads(line) for line in (baseline / "results.jsonl").read_text().splitlines()]
    validate_rows(cases, rows, contexts)
    return frozen, (cases, bundle, config, catalog), contexts, rows


async def measure(output, baseline, ledger):
    frozen, validated, contexts, old_rows = validate_experiment(baseline)
    cases, bundle, config, catalog = validated
    output.mkdir(parents=True, exist_ok=False)
    before = ledger_total(ledger)
    metered = ConcurrentMeteredBackend(JevBackend(config["provider"]), ledger)
    write_json(
        output / "manifest.json",
        {
            "format": "humanwill.direct-policy-run/1",
            "protocol": frozen,
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
        comparison = compare(old_rows, rows)
        comparison["direct_policy_model_scope"] = comparison.pop("context_model_scope")
        write_json(output / "comparison.json", comparison)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--keychain-helper", type=Path)
    args = parser.parse_args()
    _, validated, _, _ = validate_experiment(args.baseline)
    if args.validate_only:
        print(json.dumps({"valid_cases": len(validated[0]), "provider_calls": 0}))
        return
    if args.output is None:
        parser.error("New output directory required")
    if subprocess.check_output(["git", "status", "--porcelain"]):
        parser.error("Commit the frozen experiment before live execution")
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
