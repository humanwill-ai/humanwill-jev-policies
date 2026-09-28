"""Offline release-scope selection, independent of model answers and expected labels.

This partitions these fixed fixtures; it is not a shell parser or runtime allowlist.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from .question_context import sha256
from .reviewed_live import validate_protocol

BASE = Path(__file__).parent
MANIFEST = BASE / "release-scope-v1/manifest.json"
REASONS = {
    "raw_production_effects": (
        "Production impact must be inferred from raw shell/SQL syntax, rather than a "
        "verified structured operation. Keep as advanced command diagnostics."
    ),
    "shell_composition": (
        "Execution depends on shell composition, redirection, substitution or printed "
        "command text. Keep as advanced command diagnostics."
    ),
    "program_behavior": (
        "Execution depends on interpreter code, a project task or a referenced script. "
        "Keep as advanced command diagnostics."
    ),
    "policy_application": (
        "Natural-language intent, structured business tools, deterministic facts, or a "
        "straightforward single-command fixture; retain in the generic policy suite. "
        "A retained CLI example does not promise general shell interpretation."
    ),
}


def classify(case):
    """Use input form and the tested capability, never outcomes, scores or gold labels."""
    policies = {case["policy_id"], *case.get("also_policy_ids", [])}
    items = [x for x in case["request"]["content"] if x["kind"] == "tool_action"]
    if "EVAL-PROD-001" in policies and any(x["name"] in {"shell", "sql"} for x in items):
        return "advanced_commands", "raw_production_effects"
    for item in items:
        if item["name"] != "shell":
            continue
        command = item["arguments"].get("command", "")
        if (
            any(c in command for c in "|;&<>`\n")
            or "$(" in command
            or re.match(r"\s*(printf|echo)\b", command)
        ):
            return "advanced_commands", "shell_composition"
        if re.match(r"\s*(\./|npm\s+run\b|node\s+-e\b|python[0-9.]*\s+(?!-m\b))", command):
            return "advanced_commands", "program_behavior"
    return "generic_policy", "policy_application"


def build_manifest(cases):
    assignments = []
    for case in cases:
        suite, reason = classify(case)
        assignments.append({"id": case["id"], "suite": suite, "reason": reason})
    return {
        "format": "humanwill.release-scope/1",
        "version": "1",
        "date": "2026-09-28",
        "status": "owner_authorized_scope_narrowing_after_measurement",
        "dataset": "evals/step6/release/reviewed-v1.json",
        "dataset_sha256": sha256(BASE / "release/reviewed-v1.json"),
        "selector_sha256": sha256(Path(__file__)),
        "unchanged": "All original cases, labels, approvals, model settings and results retained.",
        "limits": (
            "Retrospective scope selection, not new accuracy evidence or an independent holdout. "
            "No runtime bypass: advanced events still use configured failure/enforcement behavior."
        ),
        "reason_definitions": REASONS,
        "counts": dict(Counter(x["suite"] for x in assignments)),
        "cases": assignments,
    }


def load_suite(name):
    if name not in {"generic_policy", "advanced_commands"}:
        raise ValueError("Unknown suite")
    _, cases, *_ = validate_protocol()
    manifest = json.loads(MANIFEST.read_text())
    if manifest != build_manifest(cases):
        raise ValueError("Release scope changed; preserve v1 and create a new version")
    ids = {r["id"] for r in manifest["cases"] if r["suite"] == name}
    return [c for c in cases if c["id"] in ids]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["generic_policy", "advanced_commands"])
    args = parser.parse_args()
    suites = [args.suite] if args.suite else ["generic_policy", "advanced_commands"]
    print(json.dumps({name: [c["id"] for c in load_suite(name)] for name in suites}, indent=2))


if __name__ == "__main__":
    main()
