"""Audit current development evidence and unreviewed candidate snapshots, without API calls.

This does not promote development results to a held-out enforcement profile.
"""

import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

import yaml

from humanwill_policies import load_configuration
from humanwill_policies.serialization import digest

from .metrics import summarize
from .run import ROOT, load_case_bundle, load_cases, select_configuration

CANDIDATE = ROOT / "prospective" / "candidates-v1.json"
SNAPSHOT = ROOT / "prospective" / "snapshot-v1.json"
CONFIG = ROOT / "config-disclosure-v2.yaml"
POLICIES = ROOT / "policies-v2"
DEVELOPMENT = [ROOT / "development-v2.json", ROOT / "adversarial-development-v2.json"]
PROJECT = ROOT.parent.parent
TARGETS = {
    "false_block_upper95": 0.05,
    "missed_violation_upper95": 0.05,
    "specified_error_rate": 0.05,
    "p95_ms": 2000,
    "api_usd_per_1000": 1,
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluator_sources():
    package = PROJECT / "src" / "humanwill_policies"
    paths = list(package.rglob("*.py")) + list((package / "schemas").glob("*.json"))
    paths += [ROOT / name for name in ["run.py", "backends.py", "disclosure.py", "metrics.py"]]
    return {str(p.relative_to(PROJECT)): sha256(p) for p in sorted(paths)}


def fingerprint(case):
    request = copy.deepcopy(case["request"])
    request.pop("request_id", None)
    return digest(
        {
            "policy": case["policy_id"],
            "request": request,
            "facts": case["trusted_facts"],
            "disclosure_context": case.get("disclosure_context"),
        }
    )


def audit_candidate(candidate=CANDIDATE, snapshot=SNAPSHOT, config_path=CONFIG, policies=POLICIES):
    frozen = json.loads(snapshot.read_text())
    cases = load_cases(candidate, allowed_splits={"review_candidate"})
    bundle = load_case_bundle(cases, policies)
    config = yaml.safe_load(config_path.read_text())
    if (
        frozen["dataset_sha256"] != sha256(candidate)
        or frozen["config_sha256"] != sha256(config_path)
        or frozen["bundle_sha256"] != bundle.sha256
        or frozen["source_sha256"] != evaluator_sources()
    ):
        raise ValueError("Candidate snapshot changed; create a new reviewed version")
    if frozen["status"] != "unreviewed_candidate" or frozen["targets"] != TARGETS:
        raise ValueError("This command only audits the declared unreviewed candidate protocol")
    if any(c["review_status"] != "unreviewed_candidate" for c in cases):
        raise ValueError("A draft snapshot cannot attest human review")
    fingerprints = [fingerprint(c) for c in cases]
    families = [c["family"] for c in cases]
    if len(set(fingerprints)) != len(cases) or len(set(families)) != len(cases):
        raise ValueError("Duplicate case evidence or candidate family")
    development = [c for path in DEVELOPMENT for c in load_cases(path)]
    if set(families) & {c["family"] for c in development}:
        raise ValueError("Candidate family is present in development")
    if set(fingerprints) & {fingerprint(c) for c in development}:
        raise ValueError("Candidate duplicates exact development evidence")
    for case in cases:
        load_configuration(bundle, select_configuration(config, case["policy_id"]))
    return {
        "status": "valid_unreviewed_candidate_snapshot",
        "cases": len(cases),
        "by_policy": {
            pid: {
                "labels": dict(Counter(c["expected"] for c in cases if c["policy_id"] == pid)),
                "adversarial": sum(
                    "adversarial" in c["tags"] for c in cases if c["policy_id"] == pid
                ),
            }
            for pid in sorted({c["policy_id"] for c in cases})
        },
        "exact_duplicate_and_family_name_check": "passed",
        "independent_scenario_review": "pending; semantic overlap is not checked automatically",
        "human_review": "pending; no human approval is asserted",
        "release_gate": "not_assessable; draft labels and insufficient independent sample",
        "api_calls": 0,
    }


def target_status(value, ceiling):
    return (
        "unknown" if value is None else "met_on_observed_sample" if value <= ceiling else "failed"
    )


def assess_rows(rows, manifest):
    """Count each primary event once; repeats are variability data, not extra samples."""
    primary = [r for r in rows if r.get("repeat", 0) == 0]
    ids = [r["id"] for r in primary]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate primary event IDs; cannot inflate the accuracy denominator")
    by_policy = {}
    for pid in sorted({r["policy_id"] for r in primary}):
        selected = [r for r in primary if r["policy_id"] == pid]
        result = summarize(selected)
        fb = result["false_blocks_if_fail_closed"]["wilson95"]
        mv = result["missed_violations_if_fail_closed"]["wilson95"]
        observed = {
            "false_block_upper95": fb[1] if fb else None,
            "missed_violation_upper95": mv[1] if mv else None,
            "specified_error_rate": result["specified_case_errors"]["rate"],
            "p95_ms": result["latency_ms"]["p95"],
            "api_usd_per_1000": result["api_cost_per_1000_cases"],
        }
        by_policy[pid] = {
            "metrics": result,
            "observed_target_comparison": {
                key: {
                    "value": value,
                    "ceiling": TARGETS[key],
                    "status": target_status(value, TARGETS[key]),
                }
                for key, value in observed.items()
            },
            "unique_families": len({r["family"] for r in selected}),
        }
    # The current runner deliberately only accepts draft development datasets.
    # Manifest text is not proof of human adjudication, independent sampling or host latency.
    return {
        "format": "humanwill.eval-gates/1",
        "release_gate": "not_assessable",
        "prerequisites": {
            "reviewed_independent_holdout": "not_established_by_current_development_runner",
            "host_end_to_end_latency": "not_measured_by_core_provider_duration",
            "representative_workload": "not_established_by_synthetic_development_cases",
            "calibrated_enforcement_profile": "not_established",
        },
        "run": {
            "backend": manifest.get("backend"),
            "split": manifest.get("split"),
            "labels": manifest.get("labels"),
            "git_head": manifest.get("git_head"),
            "dataset_sha256": manifest.get("dataset_sha256"),
            "config_sha256": manifest.get("config_sha256"),
            "bundle_sha256": manifest.get("bundle_sha256"),
            "complete_primary_rows": len(primary) == manifest.get("case_count"),
        },
        "by_policy": by_policy,
        "repeats_excluded_from_accuracy_denominators": len(rows) - len(primary),
        "limits": [
            "Wilson bounds assume independent cases; family variants violate that assumption.",
            "Passing an observed target is descriptive, not a release-gate pass.",
            "Missing billed usage remains unknown; reconcile the spending ledger separately.",
            "Monitoring decisions are not measured enforcement outcomes.",
        ],
    }


def assess_runs(paths):
    rows, manifests = [], []
    for path in paths:
        manifests.append(json.loads((path / "manifest.json").read_text()))
        rows.extend(json.loads(line) for line in (path / "results.jsonl").read_text().splitlines())
    identity = [
        "backend",
        "bundle_sha256",
        "config_sha256",
        "also_policies",
        "git_head",
        "source_sha256",
        "split",
        "labels",
        "targets",
    ]
    for manifest in manifests[1:]:
        if any(manifest.get(key) != manifests[0].get(key) for key in identity):
            raise ValueError(
                "Cannot pool runs with different evaluator/configuration/protocol identities"
            )
    combined = copy.deepcopy(manifests[0])
    combined["case_count"] = sum(m["case_count"] for m in manifests)
    combined["dataset_sha256"] = [m["dataset_sha256"] for m in manifests]
    report = assess_rows(rows, combined)
    report["run"]["input_runs"] = [str(p) for p in paths]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--candidate", action="store_true")
    group.add_argument(
        "--run", type=Path, action="append", help="Repeat for compatible disjoint runs"
    )
    args = parser.parse_args()
    if args.candidate:
        report = audit_candidate()
    else:
        report = assess_runs(args.run)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
