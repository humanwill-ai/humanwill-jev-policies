"""Separate per-model development diagnostics; never fit on or claim a holdout.

Usage: python -m evals.step6.calibrate --output artifacts/quality/calibration.json RUN_DIR ...
Run directories must share the exact provider/configuration/bundle. Models are
analyzed independently. Candidate thresholds are development suggestions only.
"""

import argparse
import asyncio
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import MockBackend
from humanwill_policies.serialization import digest

from .metrics import summarize
from .run import evidence_for, load_cases, write_json

THRESHOLDS = [0.0, 0.25, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]


def load_recordings(directories):
    rows, cases = [], {}
    first = None
    for directory in directories:
        manifest = json.loads((directory / "manifest.json").read_text())
        if manifest.get("also_policies"):
            raise ValueError(
                "Combined-policy runs need a separate comparison, not isolated calibration"
            )
        if manifest["backend"] not in ("jev", "chat"):
            raise ValueError("Calibrate live models independently of deterministic baselines")
        if digest(manifest["configuration"]) != manifest["config_sha256"]:
            raise ValueError("Configuration snapshot hash mismatch")
        identity = (manifest["backend"], manifest["config_sha256"], manifest["bundle_sha256"])
        if first and identity != first[0]:
            raise ValueError("Do not mix models, configurations or rubrics")
        if not first:
            first = (identity, manifest)
        path = Path(manifest["dataset_path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["dataset_sha256"]:
            raise ValueError("Dataset changed since recording")
        for case in load_cases(path):
            if case["id"] in cases:
                raise ValueError("Duplicate cases would inflate calibration sample size")
            cases[case["id"]] = case
        recorded = [
            json.loads(line) for line in (directory / "results.jsonl").read_text().splitlines()
        ]
        first_pass = [r for r in recorded if r["repeat"] == 0]
        if len(first_pass) != manifest["case_count"] or len({r["id"] for r in first_pass}) != len(
            first_pass
        ):
            raise ValueError("Cannot calibrate an incomplete or duplicated first pass")
        for row in first_pass:
            case = cases.get(row["id"])
            if case is None or any(
                row[key] != case[key]
                for key in ("policy_id", "expected", "expected_scope", "family")
            ):
                raise ValueError("Recorded labels do not match the hashed dataset")
            rows.append(row)
    if not first:
        raise ValueError("No recordings")
    manifest = first[1]
    bundle = load_bundle(Path(manifest["policy_path"]))
    if bundle.sha256 != manifest["bundle_sha256"]:
        raise ValueError("Policy bundle changed")
    return manifest, bundle, cases, rows


def confidence_bins(rows):
    bins = []
    for low, high in [(0, 0.5), (0.5, 0.8), (0.8, 0.9), (0.9, 1.01)]:
        selected = []
        for row in rows:
            policy = next(
                p for p in row["result"]["policies"] if p["policy_id"] == row["policy_id"]
            )
            ev = policy["evidence"]
            if (
                row["expected_scope"] is not None
                and "confidence" in ev
                and low <= ev["confidence"] < high
            ):
                selected.append(row)
        bins.append(
            {
                "confidence_lower": low,
                "confidence_upper_exclusive": high,
                "count": len(selected),
                "raw_scope_correct": sum(
                    r["observed_scope"] == r["expected_scope"] for r in selected
                ),
            }
        )
    return bins


def candidate(curves):
    # Empirical screen only. Confidence-interval/release gates remain unsatisfied.
    eligible = []
    for threshold, result in curves.items():
        if (
            result["false_blocks_if_fail_closed"]["rate"] is not None
            and result["missed_violations_if_fail_closed"]["rate"] is not None
            and result["false_blocks_if_fail_closed"]["rate"] <= 0.05
            and result["missed_violations_if_fail_closed"]["count"] == 0
            and result["specified_case_errors"]["rate"] <= 0.05
            and result["unknown_incorrectly_allowed"] == 0
        ):
            eligible.append(float(threshold))
    return max(eligible) if eligible else None


async def analyze(directories):
    manifest, bundle, cases, rows = load_recordings(directories)
    configuration = manifest["configuration"]
    curves = {
        key: {}
        for key, value in configuration["policies"].items()
        if value["strategy"] == "scoped_predicates"
    }
    for threshold in THRESHOLDS:
        replayed = []
        for row in rows:
            case = cases[row["id"]]
            selected = copy.deepcopy(configuration)
            for key, binding in selected["policies"].items():
                binding["enabled"] = key == case["policy_id"]
                if binding["strategy"] == "scoped_predicates":
                    if binding.get("mode") == "enforce":
                        raise ValueError("Calibration must not create enforcement profiles")
                    binding["monitor_min_confidence"] = threshold
            recorded = next(
                p for p in row["result"]["policies"] if p["policy_id"] == row["policy_id"]
            )
            ev = recorded["evidence"]
            if row["result"].get("evaluation") and "choice" not in ev:
                # Transport/response failures cannot be repaired by replaying fake answers.
                replayed.append(row)
                continue
            answers = {}
            if "choice" in ev:
                answers[case["policy_id"]] = {
                    "type": "choice",
                    **{k: ev[k] for k in ("choice", "confidence", "probabilities")},
                }
            engine = Evaluator(bundle, load_configuration(bundle, selected), MockBackend(answers))
            result = await engine.evaluate(case["request"], evidence=evidence_for(case))
            replayed.append({**row, "result": result})
        for policy, curve in curves.items():
            curve[str(threshold)] = summarize([r for r in replayed if r["policy_id"] == policy])
    return {
        "backend": manifest["backend"],
        "configuration_sha256": manifest["config_sha256"],
        "recorded_rows": len(rows),
        "family_count": len({r["family"] for r in rows}),
        "threshold_grid": THRESHOLDS,
        "per_policy": {
            policy: {
                "curves": curve,
                "development_candidate": candidate(curve),
                "raw_confidence_bins": confidence_bins(
                    [r for r in rows if r["policy_id"] == policy]
                ),
            }
            for policy, curve in curves.items()
        },
        "actual_enforcement": "none",
        "status": (
            "Development only; draft labels and reused families; no calibrated release profile"
        ),
        "selection": (
            "Highest threshold with empirical false-block <=5%, zero misses, "
            "specified errors <=5%, no unknown allows"
        ),
        "initial_outcomes": dict(Counter(r["result"]["decision"] for r in rows)),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_json(args.output, asyncio.run(analyze(args.directories)))
