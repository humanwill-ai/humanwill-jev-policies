"""Research comparison: explicit policy targets with one lossless conversation view."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
import subprocess
from pathlib import Path

from evals.step6.conversation_live import assess as assess_control
from evals.step6.conversation_structure import flatten, partition
from evals.step6.conversation_views import SUBJECTS, load_subjects
from evals.step6.conversation_views import load_inputs as load_controls
from evals.step6.conversation_views import transform as previous_transform
from evals.step6.live_support import Ledger, credential
from humanwill_policies.errors import PolicyError
from humanwill_policies.serialization import canonical

from .evaluate import assess, load_profile, verify_receipt
from .grouping import control_signature, measure
from .pilot import ROOT, fingerprint, save

ARMS = ("structured", "policy_views", "compact_views")


def transform(payload, arm, subjects=None):
    if arm in ("structured", "policy_views"):
        return previous_transform(payload, arm, subjects)
    if arm != "compact_views" or payload["state"]["stage"] != "model_request":
        raise ValueError("Unexpected compact comparison arm or stage")
    subjects = load_subjects() if subjects is None else subjects
    if not set(payload["questions"]) <= set(subjects) or any(
        value not in SUBJECTS for value in subjects.values()
    ):
        raise ValueError("Every question needs an explicit supported subject")
    result = copy.deepcopy(payload)
    grouped = partition(result["state"]["content"])
    if "latest_user_message" in grouped:
        if flatten(grouped) != result["state"]["content"]:
            raise ValueError("Conversation content changed")
        result["state"]["content"] = grouped
        for pid, question in result["questions"].items():
            subject = copy.deepcopy(SUBJECTS[subjects[pid]])
            subject["view"] = "state.content"
            question["instructions"]["assessment_subject"] = subject
    # Preserve the previous candidate's flat no-role fallback; no new classifier.
    if len(canonical(result).encode()) > 24000:
        raise PolicyError("batch_limit", "Compact policy view exceeds the payload limit")
    return result


class VariantBackend:
    def __init__(self, backend, arm):
        self.backend, self.arm = backend, arm
        self.transport, self.model = backend.transport, backend.model
        self.accepted_models = backend.accepted_models

    async def evaluate(self, payload, **kwargs):
        return await self.backend.evaluate(transform(payload, self.arm), **kwargs)


def validate(directory, receipt):
    original = json.loads((directory / "history/packet.json").read_text())
    reviewed = json.loads((directory / "history/provisional-review.json").read_text())
    scope = json.loads((directory / "operator-scope.json").read_text())
    bundle, config = load_profile()
    cases = verify_receipt(original, reviewed, receipt, scope, bundle, config)
    controls, cb, cc = load_controls()
    if receipt.get("controls_sha256") != control_signature(controls, cb, cc):
        raise ValueError("Safety controls changed")
    if receipt.get("subjects_sha256") != fingerprint(load_subjects()):
        raise ValueError("Operator-owned experimental policy targets changed")
    if (
        receipt.get("experiment") != "compact_views_v1"
        or receipt.get("arms") != list(ARMS)
        or receipt.get("repeats") != 2
        or receipt.get("seed") != 20261005
        or receipt.get("max_physical_calls") != 960
        or receipt.get("additional_cap_usd") != 0.15
        or len(cases) != 50
        or len(controls) != 30
        or config.to_dict()["provider"] != cc.to_dict()["provider"]
    ):
        raise ValueError("Frozen comparison dimensions changed")
    return cases, bundle, config, controls, cb, cc


async def assess_arm(case, bundle, config, backend, cohort, arm):
    if cohort == "workflow":
        return await assess(case, bundle, config, VariantBackend(backend, arm))
    if cohort == "controls":
        return await assess_control(case, bundle, config, VariantBackend(backend, arm), "clarified")
    raise ValueError("Unknown cohort")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("directory", "receipt", "output", "keychain-helper"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text())
    inputs = validate(args.directory, receipt)
    if args.validate_only:
        print(json.dumps({"workflow_cases": 50, "controls": 30, "assessments": 480, "calls": 0}))
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
