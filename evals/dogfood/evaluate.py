"""Evaluate an explicitly reviewed local packet. No implicit real-data egress."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
from collections import Counter
from pathlib import Path

import yaml

from evals.step6.live_support import Ledger, credential, ledger_total
from evals.step6.metrics import percentile
from evals.step6.policy_isolation import RecordedBackend
from evals.step6.restart_accounting import RestartMeteredBackend
from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import JevBackend
from humanwill_policies.runtime import EgressPermit, EvidenceContext, utc_now
from humanwill_policies.serialization import digest

from .pilot import ROOT, fingerprint, save

BASE = Path(__file__).parent
CARRIED = {1830: "36cda369bd8be95da0e983ede63b1021782df56cae3398ce31fbf47a1479165c"}
FACT_FIELDS = {"destination.onward_approved", "authorization.software_sources_approved"}


def source_fingerprint():
    # Freeze executable research/runtime code independently of evolving project docs.
    paths = sorted(
        set((ROOT / "src/humanwill_policies").rglob("*.py"))
        | set((ROOT / "src/humanwill_policies/schemas").glob("*.json"))
        | set((ROOT / "evals/step6").glob("*.py"))
        | set(BASE.glob("*.py"))
    )
    return fingerprint({str(p.relative_to(ROOT)): fingerprint(p.read_text()) for p in paths})


def load_profile():
    bundle = load_bundle(BASE / "policies")
    config = load_configuration(bundle, yaml.safe_load((BASE / "config.yaml").read_text()))
    if any(b["mode"] != "monitor" for b in config.to_dict()["policies"].values()):
        raise ValueError("Pilot is monitoring only")
    return bundle, config


def review_packet(original, reviewed):
    if original.get("format") != "humanwill.dogfood-packet/1":
        raise ValueError("Invalid packet format")
    if len(original["cases"]) != original["count"] or original["count"] > 100:
        raise ValueError("Invalid packet count")
    if len({c["id"] for c in original["cases"]}) != original["count"]:
        raise ValueError("Duplicate case")
    base = copy.deepcopy(original)
    submitted = copy.deepcopy(reviewed)
    if [c["id"] for c in submitted["cases"]] != [c["id"] for c in base["cases"]]:
        raise ValueError("Case list changed")
    selected = []
    for a, b in zip(base["cases"], submitted["cases"], strict=True):
        r = b.pop("review")
        a.pop("review")
        if a != b or fingerprint(a["request"]) != a["request_sha256"]:
            raise ValueError("Original request, context or provenance changed")
        if r.get("status") not in ("approved", "exclude"):
            raise ValueError("Finish every review or explicitly exclude the case")
        if r["status"] == "exclude":
            continue
        if r.get("expected_decision") not in ("allow", "block", "evaluation_error"):
            raise ValueError("Missing expected outcome")
        if set(r.get("facts", {})) != FACT_FIELDS:
            raise ValueError("Unexpected trusted fields")
        if any(v is not None and type(v) is not bool for v in r["facts"].values()):
            raise ValueError("Facts must be boolean or unknown")
        if any(v is not None for v in r["facts"].values()) and not r.get("reason", "").strip():
            raise ValueError("Known facts need an operator evidence note")
        selected.append({**a, "review": r})
    if base != submitted:
        raise ValueError("Packet metadata changed")
    if not selected:
        raise ValueError("No reviewed cases selected")
    return selected


def verify_receipt(original, reviewed, receipt, scope, bundle, config):
    expected = {
        "packet_sha256": fingerprint(original),
        "review_sha256": fingerprint(reviewed),
        "operator_scope_sha256": fingerprint(scope),
        "bundle_sha256": bundle.sha256,
        "configuration_sha256": config.sha256,
        "source_sha256": source_fingerprint(),
    }
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise ValueError("Approval does not bind this exact packet, review and configuration")
    if receipt.get("allow_external_evaluation") is not True or not receipt.get(
        "owner_authorization"
    ):
        raise ValueError("Explicit owner authorization for real-data egress is required")
    if scope.get("coding_route_approved") is not True:
        raise ValueError("Pilot coding route must be approved by operator")
    if not 0 < receipt.get("additional_cap_usd", 0) <= 0.20:
        raise ValueError("Invalid pilot spending ceiling")
    return review_packet(original, reviewed)


async def assess(case, bundle, config, backend):
    # Human-reviewed operation facts, bound to this exact event. Never model-inferred.
    request = case["request"]
    values = {"destination.coding_route_approved": True, **case["review"]["facts"]}
    facts = [
        {
            "field": field,
            "source": "humanwill-pilot-review",
            "subject_ref": case["request_sha256"],
            "complete": True,
            "observed_at": utc_now().isoformat(),
            "value": value,
        }
        for field, value in values.items()
        if value is not None
    ]
    return await Evaluator(bundle, config, backend).evaluate(
        request,
        evidence=EvidenceContext.from_verified(request, facts),
        egress=EgressPermit(digest(request), bundle.sha256, backend.transport),
    )


async def measure(cases, bundle, config, ledger, receipt, output):
    before = ledger_total(ledger)
    ceiling = min(ledger.data["cap_usd"], before + receipt["additional_cap_usd"])
    backend = RestartMeteredBackend(JevBackend(config.to_dict()["provider"]), ledger, CARRIED)
    results = []
    save(
        output / "manifest.json",
        {"approval": receipt, "started_at": utc_now().isoformat(), "accounted_before_usd": before},
    )
    try:
        for case in cases:
            caller = RecordedBackend(
                backend, output / "provider-exchanges.jsonl", case["id"], ledger, ceiling
            )
            start = len(ledger.data["calls"])
            result = await assess(case, bundle, config, caller)
            row = {
                "id": case["id"],
                "expected_decision": case["review"]["expected_decision"],
                "request_sha256": case["request_sha256"],
                "result": result,
                "ledger_indices": list(range(start, len(ledger.data["calls"]))),
            }
            results.append(row)
            save(output / (case["id"] + ".json"), row)
            if backend.fatal:
                break
    finally:
        save(
            output / "summary.json",
            {
                "complete": len(results) == len(cases),
                "assessments": len(results),
                "known_matches": sum(
                    x["result"]["decision"] == x["expected_decision"] for x in results
                ),
                "calls": len(backend.calls),
                "confusion": {
                    label: dict(
                        Counter(
                            r["result"]["decision"]
                            for r in results
                            if r["expected_decision"] == label
                        )
                    )
                    for label in ("allow", "block", "evaluation_error")
                },
                "policy_error_reasons": dict(
                    Counter(
                        reason
                        for r in results
                        for p in r["result"]["policies"]
                        if p["status"] == "error"
                        for reason in p["reasons"]
                    )
                ),
                "latency_ms": {
                    "median": percentile([r["result"]["duration_ms"] for r in results], 0.5),
                    "p95": percentile([r["result"]["duration_ms"] for r in results], 0.95),
                },
                "accounted_before_usd": before,
                "accounted_after_usd": ledger_total(ledger),
                "new_cost_usd": ledger_total(ledger) - before,
                "enforcement": "none; retrospective monitoring only",
                "limitations": (
                    "Reviewed, selected real workflow; incomplete context; not independent holdout."
                ),
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["packet", "reviewed", "receipt", "scope", "output", "keychain-helper"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    original = json.loads(args.packet.read_text())
    reviewed = json.loads(args.reviewed.read_text())
    receipt = json.loads(args.receipt.read_text())
    scope = json.loads(args.scope.read_text())
    bundle, config = load_profile()
    cases = verify_receipt(original, reviewed, receipt, scope, bundle, config)
    if args.validate_only:
        print(json.dumps({"reviewed_cases": len(cases), "calls": 0}))
        return
    if args.output.exists():
        parser.error("Fresh output required; no implicit retry or duplicate run")
    path = ROOT / "artifacts/quality/spending.json"
    try:
        with path.with_suffix(".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            used_path = ROOT / "artifacts/dogfood-v1/used-approvals.json"
            used = json.loads(used_path.read_text()) if used_path.exists() else []
            receipt_id = fingerprint(receipt)
            if receipt_id in used:
                raise ValueError("This one-run approval has already been consumed")
            credential(args.keychain_helper)
            save(used_path, [*used, receipt_id])
            args.output.mkdir(parents=True, mode=0o700)
            os.umask(0o077)
            asyncio.run(measure(cases, bundle, config, Ledger(path), receipt, args.output))
    finally:
        os.environ.pop("OPENROUTER_API_KEY", None)


if __name__ == "__main__":
    main()
