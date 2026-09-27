"""Run reviewed synthetic development inputs; do not use this as a production resolver.

python -m evals.step6.run --backend keyword --output artifacts/quality/keyword
Live runs additionally require --allow-external and a locally supplied API key.
No held-out claim is possible with the draft development dataset.
"""

import argparse
import asyncio
import copy
import fcntl
import hashlib
import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import yaml

from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.contracts import validate_contract
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import JevBackend
from humanwill_policies.runtime import EgressPermit, EvidenceContext
from humanwill_policies.serialization import digest

from .backends import CHAT_MODEL, ChatBackend, KeywordBackend, Ledger, MeteredBackend
from .metrics import summarize

ROOT = Path(__file__).parent


def load_cases(path):
    data = json.loads(path.read_text())
    if data.get("format") != "humanwill.eval-dataset/1" or data.get("synthetic") is not True:
        raise ValueError("Only the explicit synthetic dataset contract is accepted")
    ids, families, exact = set(), {}, {}
    for case in data["cases"]:
        if case["id"] in ids:
            raise ValueError("Duplicate case ID")
        ids.add(case["id"])
        if case["split"] != "development":
            raise ValueError("This runner cannot claim or evaluate an unreviewed holdout")
        if case["expected"] not in {"allow", "block", "evaluation_error"}:
            raise ValueError("Unknown label")
        if case["expected_scope"] not in {
            None,
            "applicable",
            "not_applicable",
            "insufficient_evidence",
        }:
            raise ValueError("Unknown scope label")
        if not case["rationale"] or not case["family"]:
            raise ValueError("Missing rationale/family")
        validate_contract("request", case["request"])
        if case["request"]["request_id"] != case["id"]:
            raise ValueError("Case/event ID mismatch")
        previous = families.setdefault(case["family"], case["split"])
        if previous != case["split"]:
            raise ValueError("Related family spans splits")
        request = copy.deepcopy(case["request"])
        request.pop("request_id")
        fingerprint = digest(
            {"policy": case["policy_id"], "request": request, "facts": case["trusted_facts"]}
        )
        if fingerprint in exact and exact[fingerprint] != case["expected"]:
            raise ValueError("Identical evidence has conflicting labels")
        exact[fingerprint] = case["expected"]
    return data["cases"]


def evidence_for(case):
    # These are operator-authored synthetic fixtures, never assertions from host input.
    values = dict(case["trusted_facts"])
    environment, approval = values.get("environment.kind"), values.get("authorization.approved")
    values.pop("authorization.destructive_permitted", None)
    if environment == "disposable_sandbox":
        values["authorization.destructive_permitted"] = True
    elif environment == "production" and type(approval) is bool:
        values["authorization.destructive_permitted"] = approval
    facts = [
        {
            "field": field,
            "value": value,
            "source": "synthetic-authority",
            "subject_ref": case["id"] + ":item",
            "complete": True,
            "observed_at": datetime.now(UTC).isoformat(),
        }
        for field, value in values.items()
    ]
    return EvidenceContext.from_verified(case["request"], facts)


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


async def run(args):
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    cases = load_cases(args.dataset)
    if args.limit:
        cases = cases[: args.limit]
    bundle = load_bundle(ROOT / "policies")
    config = yaml.safe_load(args.config.read_text())
    if args.backend == "keyword":
        backend = KeywordBackend()
        ledger = None
    else:
        if not args.allow_external:
            raise ValueError("Explicit --allow-external required for synthetic disclosure")
        ledger = Ledger(args.ledger)
        underlying = JevBackend(config["provider"]) if args.backend == "jev" else ChatBackend()
        if args.backend == "chat":
            config["provider"].update(model=CHAT_MODEL, accepted_models=[CHAT_MODEL])
        backend = MeteredBackend(underlying, ledger)
    manifest = {
        "format": "humanwill.eval-run/1",
        "started_at": datetime.now(UTC).isoformat(),
        "backend": args.backend,
        "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        "bundle_sha256": bundle.sha256,
        "config_sha256": digest(config),
        "configuration": config,
        "dataset_path": str(args.dataset.resolve()),
        "policy_path": str((ROOT / "policies").resolve()),
        "source_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob("*.py")
        },
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True)),
        "labels": "agent_draft; not independently reviewed",
        "split": "development",
        "case_count": len(cases),
        "repeats": args.repeats,
        "concurrency": 1,
        "retries": 0,
        "decision_cache": False,
        "thresholds": {
            key: binding.get("monitor_min_confidence")
            for key, binding in config["policies"].items()
        },
        "threshold_status": "uncalibrated pre-existing development default",
        "targets": {
            "false_block_upper95": 0.05,
            "missed_violation_upper95": 0.05,
            "specified_error_rate": 0.05,
            "p95_ms": 2000,
            "api_usd_per_1000": 1,
        },
        "cost_before": copy.deepcopy(ledger.data) if ledger else None,
    }
    write_json(output / "manifest.json", manifest)
    results = []
    stopped = False
    for repeat in range(args.repeats):
        for case in cases:
            selected = copy.deepcopy(config)
            for key, binding in selected["policies"].items():
                binding["enabled"] = key == case["policy_id"]
            if case["policy_id"] not in selected["policies"]:
                raise ValueError("Unknown policy in dataset")
            engine = Evaluator(bundle, load_configuration(bundle, selected), backend)
            permit = EgressPermit(digest(case["request"]), bundle.sha256, backend.transport)
            result = await engine.evaluate(
                case["request"], evidence=evidence_for(case), egress=permit
            )
            policy_result = next(
                p for p in result["policies"] if p["policy_id"] == case["policy_id"]
            )
            row = {
                key: case[key]
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
                repeat=repeat,
                stage=case["request"]["stage"],
                result=result,
                observed_scope=policy_result["evidence"].get("choice"),
            )
            results.append(row)
            with (output / "results.jsonl").open("a") as stream:
                stream.write(json.dumps(row) + "\n")
            print(
                json.dumps(
                    {
                        "backend": args.backend,
                        "case": case["id"],
                        "repeat": repeat,
                        "expected": case["expected"],
                        "observed": result["decision"],
                        "scope": row["observed_scope"],
                    }
                ),
                flush=True,
            )
            if isinstance(backend, MeteredBackend) and backend.fatal:
                stopped = True
                break
        if stopped:
            break
    first = [r for r in results if r["repeat"] == 0]
    report = {
        "complete": len(results) == len(cases) * args.repeats,
        "aggregate": summarize(first),
        "by_policy": {},
        "by_stage": {},
        "by_tag": {},
        "label_counts": dict(Counter(c["expected"] for c in cases)),
        "all_attempts_including_repeats": summarize(results),
    }
    for key, field in [("by_policy", "policy_id"), ("by_stage", "stage")]:
        for value in sorted({r[field] for r in first}):
            report[key][value] = summarize([r for r in first if r[field] == value])
    for tag in sorted({tag for r in first for tag in r["tags"]}):
        report["by_tag"][tag] = summarize([r for r in first if tag in r["tags"]])
    report["repeat_changed_cases"] = [
        cid
        for cid in {r["id"] for r in results}
        if len({r["result"]["decision"] for r in results if r["id"] == cid}) > 1
    ]
    write_json(output / "summary.json", report)
    if ledger:
        write_json(output / "cost-after.json", ledger.data)
    print(json.dumps({"complete": report["complete"], "rows": len(results)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["keyword", "jev", "chat"], required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT / "development.json")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--ledger", type=Path, default=Path("artifacts/quality/spending.json"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()
    if args.repeats < 1 or args.repeats > 5 or args.limit is not None and args.limit < 1:
        parser.error("Invalid repeat/limit count")
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    with args.ledger.with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        asyncio.run(run(args))


if __name__ == "__main__":
    main()
