"""Research-only comparison of bounded history with a longer original topic excerpt."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
import subprocess
from pathlib import Path

from evals.step6.conversation_views import load_inputs as load_controls
from evals.step6.conversation_views import load_subjects
from evals.step6.live_support import Ledger, credential

from .compact import assess_arm as assess_compact
from .evaluate import load_profile, verify_receipt
from .grouping import control_signature, measure
from .pilot import ROOT, fingerprint, save

ARMS = ("bounded", "extended")
CASE_IDS = tuple(f"dogfood-history-{n}" for n in ("005", "027", "029", "035", "041", "049"))


def extend_case(case, records, first_line, prefix_end_line=None):
    """Add original native-text history ending at the exact original user prompt.

    No summaries, new permission facts, tool records or future answers are added.
    Preserve existing part IDs so paired payload changes are limited to the prefix
    and its explicit coverage description. Oversized excerpts are not shortened.
    """
    original_lines = case["source_lines"]
    selected = [r for r in records if first_line <= r["line"] <= original_lines[-1]]
    if not selected or selected[0]["line"] != first_line:
        raise ValueError("Excerpt must begin at a native message")
    if [r["line"] for r in selected[-len(original_lines) :]] != original_lines:
        raise ValueError("Original suffix missing or noncontiguous")
    suffix = selected[-len(original_lines) :]
    parts = case["request"]["content"]
    if any(
        (r["role"], r["text"]) != (p["role"], p["text"]) for r, p in zip(suffix, parts, strict=True)
    ):
        raise ValueError("Transcript differs from original packet")
    if selected[-1]["role"] != "user" or any(r["timestamp"] > case["timestamp"] for r in selected):
        raise ValueError("Future or non-user target content")
    prefix = selected[: -len(original_lines)]
    if prefix_end_line is not None:
        if prefix_end_line not in {r["line"] for r in prefix}:
            raise ValueError("Earlier topic excerpt must end before the original suffix")
        prefix = [r for r in prefix if r["line"] <= prefix_end_line]
    if not prefix:
        raise ValueError("Extended arm needs preceding messages")
    result = copy.deepcopy(case)
    result["source_lines"] = [r["line"] for r in prefix + suffix]
    request = result["request"]
    request["content"] = [
        {"id": f"history-{r['line']}", "kind": "text", "role": r["role"], "text": r["text"]}
        for r in prefix
    ] + request["content"]
    request["coverage"]["inspected"] = [p["id"] for p in request["content"]]
    request["coverage"]["omitted"][-1] = (
        "Earlier conversation before this selected original topic excerpt"
    )
    if prefix_end_line is not None:
        request["coverage"]["omitted"].append(
            "Intervening visible messages between the earlier topic excerpt and recent window"
        )
    result["request_sha256"] = fingerprint(request)
    return result


def validate(directory, receipt):
    original = json.loads((directory / "history/packet.json").read_text())
    reviewed = json.loads((directory / "history/provisional-review.json").read_text())
    scope = json.loads((directory / "operator-scope.json").read_text())
    bundle, config = load_profile()
    approved = {
        c["id"]: c for c in verify_receipt(original, reviewed, receipt, scope, bundle, config)
    }
    packet = json.loads((directory / "context-v1/packet.json").read_text())
    if receipt.get("context_packet_sha256") != fingerprint(packet):
        raise ValueError("Extended context or premeasurement expectations changed")
    if tuple(c["id"] for c in packet["cases"]) != CASE_IDS:
        raise ValueError("Frozen selection changed")
    cases = []
    for pair in packet["cases"]:
        base, extended = pair["bounded"], pair["extended"]
        if base != approved[pair["id"]]:
            raise ValueError("Bounded control changed")
        a, b = base["request"], extended["request"]
        if (
            extended["review"] != base["review"]
            or extended["request_sha256"] != fingerprint(b)
            or len(b["content"]) <= len(a["content"])
            or b["content"][-len(a["content"]) :] != a["content"]
            or b["coverage"]["complete"] is not False
            or {k: v for k, v in a.items() if k not in ("content", "coverage")}
            != {k: v for k, v in b.items() if k not in ("content", "coverage")}
        ):
            raise ValueError("Context pair changes target, facts or original messages")
        cases.append({**base, "extended": extended})
    controls, cb, cc = load_controls()
    if (
        receipt.get("controls_sha256") != control_signature(controls, cb, cc)
        or receipt.get("subjects_sha256") != fingerprint(load_subjects())
        or receipt.get("experiment") != "context_length_v1"
        or receipt.get("arms") != list(ARMS)
        or receipt.get("repeats") != 2
        or receipt.get("seed") != 20261004
        or receipt.get("max_physical_calls") != 288
        or receipt.get("additional_cap_usd") != 0.10
        or len(controls) != 30
        or config.to_dict()["provider"] != cc.to_dict()["provider"]
    ):
        raise ValueError("Frozen comparison dimensions changed")
    return cases, bundle, config, controls, cb, cc


async def assess_arm(case, bundle, config, backend, cohort, arm):
    if arm not in ARMS:
        raise ValueError("Unexpected context arm")
    if cohort == "workflow" and arm == "extended":
        case = case["extended"]
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
        print(json.dumps({"workflow_cases": 6, "controls": 30, "assessments": 144, "calls": 0}))
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
