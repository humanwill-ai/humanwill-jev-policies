"""Frozen v3/v4 publication-preparation comparison; no runtime policy replacement."""

import argparse
import asyncio
import fcntl
import json
import os
import subprocess
from functools import lru_cache
from pathlib import Path

import yaml

from evals.step6.conversation_views import load_inputs as load_controls
from evals.step6.conversation_views import load_subjects
from evals.step6.live_support import Ledger, credential
from humanwill_policies import load_bundle, load_configuration

from .compact import assess_arm as assess_compact
from .evaluate import BASE, load_profile, verify_receipt
from .grouping import control_signature, measure
from .pilot import ROOT, fingerprint, save

ARMS = ("v3", "v4")
REAL_IDS = tuple(
    f"dogfood-history-{i}" for i in ("005", "008", "026", "027", "029", "035", "041", "049")
)


@lru_cache
def profiles():
    b3, c3 = load_profile()
    controls, cb3, cc3 = load_controls()
    b4 = load_bundle(BASE / "policies-preparation-v1")
    c4 = load_configuration(b4, yaml.safe_load((BASE / "config.yaml").read_text()))
    cb4 = load_bundle(BASE / "preparation-v1/controls-policies")
    cc4 = load_configuration(cb4, cc3.to_dict())
    if c3.to_dict() != c4.to_dict() or cc3.to_dict() != cc4.to_dict():
        raise ValueError("Policy comparison changes evaluation settings")
    for name in ("software.md", "approved-sources.md"):
        if (BASE / "policies-preparation-v1" / name).read_bytes() != (
            BASE / "preparation-v1/controls-policies" / name
        ).read_bytes():
            raise ValueError("Workflow and control policy text differ")
    return {"v3": (b3, c3, cb3, cc3), "v4": (b4, c4, cb4, cc4)}, controls


def signatures():
    ps, controls = profiles()
    return {
        arm: {
            "workflow_bundle": b.sha256,
            "workflow_config": c.sha256,
            "controls": control_signature(controls, cb, cc),
        }
        for arm, (b, c, cb, cc) in ps.items()
    }


def validate(directory, receipt):
    original = json.loads((directory / "history/packet.json").read_text())
    review = json.loads((directory / "history/provisional-review.json").read_text())
    scope = json.loads((directory / "operator-scope.json").read_text())
    ps, controls = profiles()
    b, c, cb, cc = ps["v3"]
    approved = {x["id"]: x for x in verify_receipt(original, review, receipt, scope, b, c)}
    context = json.loads((directory / "context-v1/packet.json").read_text())
    extended = {p["id"]: p["extended"] for p in context["cases"]}
    packet = json.loads((directory / "preparation-v1/packet.json").read_text())
    synthetic = json.loads((BASE / "preparation-v1/cases.json").read_text())
    if (
        receipt.get("experiment") != "preparation_policy_v1"
        or receipt.get("comparison_sha256") != fingerprint(packet)
        or receipt.get("context_packet_sha256") != fingerprint(context)
        or receipt.get("synthetic_sha256") != fingerprint(synthetic)
        or receipt.get("profiles") != signatures()
        or receipt.get("subjects_sha256") != fingerprint(load_subjects())
        or receipt.get("arms") != list(ARMS)
        or receipt.get("repeats") != 2
        or receipt.get("seed") != 20261006
        or receipt.get("max_physical_calls") != 400
        or receipt.get("additional_cap_usd") != 0.10
        or len(controls) != 30
        or len(synthetic["cases"]) != 12
        or tuple(x["id"] for x in packet["cases"]) != REAL_IDS
    ):
        raise ValueError("Frozen policy comparison changed")
    cases = []
    for row in packet["cases"]:
        case = row["case"]
        original_case = extended.get(case["id"], approved[case["id"]])
        if case != original_case:
            raise ValueError("Original context, review or permission facts changed")
        # Measurement reference only; not sent to Jev or used to derive facts.
        cases.append(case)
    for case in synthetic["cases"]:
        if case["request_sha256"] != fingerprint(case["request"]):
            raise ValueError("Synthetic request changed")
        cases.append(case)
    return cases, b, c, controls, cb, cc


async def assess_arm(case, bundle, config, backend, cohort, arm):
    if arm not in ARMS:
        raise ValueError("Unexpected policy arm")
    b, c, cb, cc = profiles()[0][arm]
    bundle, config = (b, c) if cohort == "workflow" else (cb, cc)
    return await assess_compact(case, bundle, config, backend, cohort, "compact_views")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("directory", "receipt", "output", "keychain-helper"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text())
    inputs = validate(args.directory, receipt)
    if args.validate_only:
        print(
            json.dumps(
                {
                    "historical": 8,
                    "new_synthetic": 12,
                    "controls": 30,
                    "assessments": 200,
                    "calls": 0,
                }
            )
        )
        return
    if args.output.exists() or subprocess.check_output(["git", "status", "--porcelain"]):
        parser.error("Fresh output and clean frozen source required")
    path = ROOT / "artifacts/quality/spending.json"
    try:
        with path.with_suffix(".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            ledger = Ledger(path)
            if fingerprint(ledger.data) != receipt["starting_ledger_sha256"]:
                raise ValueError("Starting ledger changed")
            used_path = args.directory / "used-approvals.json"
            used = json.loads(used_path.read_text()) if used_path.exists() else []
            if fingerprint(receipt) in used:
                raise ValueError("Comparison approval already consumed")
            credential(args.keychain_helper)
            save(used_path, [*used, fingerprint(receipt)])
            os.umask(0o077)
            args.output.mkdir(mode=0o700)
            asyncio.run(
                measure(args.output, ledger, receipt, inputs, arms=ARMS, assessor=assess_arm)
            )
    finally:
        os.environ.pop("OPENROUTER_API_KEY", None)


if __name__ == "__main__":
    main()
