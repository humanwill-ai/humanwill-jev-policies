"""Small frozen Jev tool-classification probe; no runtime behavior changes."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
import random
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import yaml

from humanwill_policies import load_configuration
from humanwill_policies.errors import PolicyError
from humanwill_policies.providers import JevBackend, validate_response
from humanwill_policies.serialization import canonical

from .live_support import Ledger, credential, ledger_total
from .policy_isolation import (
    RecordedBackend,
    StoredBackend,
    eligible_policies,
    evaluate,
    merge_answers,
)
from .q05_full_pack import abstention_summary
from .question_context import sha256
from .restart_accounting import RestartMeteredBackend
from .reviewed_live import ROOT, observed_policy
from .run import load_case_bundle, select_configuration, write_json
from .short_questions import transform
from .source_approval import load_catalog, source_evidence_for

BASE = ROOT / "evals/step6/tool-probe-v1"
ARMS = ("q04", "tool_wording", "classified_tool")


def validate_experiment():
    frozen = json.loads((BASE / "protocol.json").read_text())
    for path, expected in frozen["sha256"].items():
        if sha256(ROOT / path) != expected:
            raise ValueError(f"Frozen tool probe changed: {path}")
    cases = json.loads((BASE / "cases.json").read_text())["cases"]
    if [c["id"] for c in cases] != frozen["case_ids"]:
        raise ValueError("Case selection changed")
    bundle = load_case_bundle(cases, ROOT / "evals/step6/policies-sources-v1")
    config = yaml.safe_load((ROOT / "evals/step6/direct-policy-v2/config.yaml").read_text())
    catalog = load_catalog(ROOT / "evals/step6/sources-v1/approved-sources.yaml")
    contexts = {c["id"]: c for c in json.loads((BASE / "contexts.json").read_text())["cases"]}
    return frozen, cases, bundle, config, catalog, contexts


def classifier_payload(primary):
    spec = json.loads((BASE / "questions.json").read_text())
    return {
        "model": primary["model"],
        "state": copy.deepcopy(primary["state"]),
        "questions": spec["classifier_questions"],
    }


def qualified(answer):
    probabilities = answer["probabilities"]
    return (
        answer["confidence"] >= 0.7
        and sum(v == max(probabilities.values()) for v in probabilities.values()) == 1
    )


def followup_payload(primary, arm, classification):
    """Only runtime answers select wording; labels and policy-ID heuristics are absent."""
    if arm not in ARMS:
        raise ValueError("Unknown arm")
    spec = json.loads((BASE / "questions.json").read_text())
    result = transform(primary, "q04")
    guided = arm == "classified_tool"
    answers = classification.get("answers", {})
    if arm == "q04" or (
        guided
        and (
            "tool_use" not in answers
            or not qualified(answers["tool_use"])
            or answers["tool_use"]["choice"] != "proposed_execution"
        )
    ):
        return result
    for question in result["questions"].values():
        question["instructions"]["task"] = spec["tool_task"]
        question["criteria"] = copy.deepcopy(spec["tool_criteria"])
    if (
        guided
        and qualified(answers["operation"])
        and answers["operation"]["choice"] not in ("unknown", "no_execution")
    ):
        result["state"]["model_operation_hypothesis"] = {
            "source": "unverified_model_classification",
            "operation": answers["operation"]["choice"],
            "confidence": answers["operation"]["confidence"],
        }
        for question in result["questions"].values():
            question["instructions"]["hypothesis_boundary"] = spec["hypothesis_boundary"]
    return result


async def classify(primary, caller, remaining):
    start = time.monotonic()
    result = {"answers": {}, "error": None}
    try:
        if remaining <= 0:
            raise TimeoutError
        payload = classifier_payload(primary)
        if len(canonical(payload).encode()) > 24000:
            raise PolicyError("batch_limit", "Classifier exceeds batch limit")
        async with asyncio.timeout(remaining):
            response = await caller.evaluate(payload, timeout=remaining, max_bytes=262144)
        result["answers"], _ = validate_response(
            response, payload["questions"], caller.accepted_models
        )
    except TimeoutError:
        result["error"] = "evaluation_timeout"
    except PolicyError as exc:
        result["error"] = exc.code
    result["duration_ms"] = (time.monotonic() - start) * 1000
    return result


async def refine(record, first, arm, classification, caller, config):
    ids = eligible_policies(first)
    response = copy.deepcopy(record["raw_response"])
    notes = {"eligible": ids, "accepted": [], "rejected": {}, "calls": 0}
    if not ids:
        return response, notes
    overhead = classification["duration_ms"] if arm == "classified_tool" else 0
    remaining = (config["evaluation"]["timeout_ms"] - first["duration_ms"] - overhead) / 1000
    if remaining <= 0:
        notes["error"] = "evaluation_timeout"
        return response, notes
    payload = followup_payload(record["payload"], arm, classification)
    if len(canonical(payload).encode()) > 24000:
        notes["error"] = "batch_limit"
        return response, notes
    notes["classifier_used"] = "model_operation_hypothesis" in payload["state"]
    try:
        notes["calls"] = 1
        async with asyncio.timeout(remaining):
            second = await caller.evaluate(payload, timeout=remaining, max_bytes=262144)
        answers, _ = validate_response(second, payload["questions"], caller.accepted_models)
        response, notes["accepted"], notes["rejected"] = merge_answers(
            response, answers, ids, config["outcome_thresholds"]
        )
    except TimeoutError:
        notes["error"] = "evaluation_timeout"
    except PolicyError as exc:
        notes["error"] = exc.code
    return response, notes


def summarize(rows):
    results = {}
    for arm in ("primary", *ARMS):
        selected = [r for r in rows if r["arm"] == arm]
        stats = abstention_summary(selected)
        stats["wrong_definitive"] = [
            [r["repeat"], r["id"]]
            for r in selected
            if r["result"]["decision"] not in ("evaluation_error", r["expected_composed"])
        ]
        stats["policy_wrong_definitive"] = [
            [r["repeat"], r["id"], p["policy_id"]]
            for r in selected
            for p in r["result"]["policies"]
            if p["policy_id"] in r["expected_by_policy"]
            and observed_policy(p)
            not in ("evaluation_error", r["expected_by_policy"][p["policy_id"]])
        ]
        results[arm] = stats
    return results


async def measure(output, ledger):
    frozen, cases, bundle, config, catalog, contexts = validate_experiment()
    output.mkdir(parents=True, exist_ok=False)
    before = ledger_total(ledger)
    ceiling = min(ledger.data["cap_usd"], before + frozen["additional_cap_usd"])
    metered = RestartMeteredBackend(
        JevBackend(config["provider"]),
        ledger,
        {int(k): v for k, v in frozen["carried_reservations"].items()},
    )
    write_json(
        output / "manifest.json",
        {
            "protocol": frozen,
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "started_at": datetime.now(UTC).isoformat(),
            "accounted_before_usd": before,
        },
    )
    rng = random.Random(frozen["seed"])
    rows, classifications = [], []

    def caller(run_id):
        return RecordedBackend(
            metered, output / "provider-exchanges.jsonl", run_id, ledger, ceiling
        )

    def save(case, rep, arm, result, notes):
        row = {
            k: copy.deepcopy(case[k])
            for k in ("id", "expected_composed", "expected_by_policy", "scope_by_policy")
        }
        row.update(repeat=rep, arm=arm, result=result, followup=notes)
        rows.append(row)
        with (output / "results.jsonl").open("a") as stream:
            stream.write(json.dumps(row) + "\n")

    try:
        for rep in range(frozen["repeats"]):
            for case in cases:
                cid = case["id"]
                loaded = load_configuration(
                    bundle,
                    select_configuration(
                        config, case["policy_id"], case.get("also_policy_ids", [])
                    ),
                )
                evidence = source_evidence_for(case, catalog)
                first_caller = caller(f"{rep}/{cid}/primary")
                first = await evaluate(case, bundle, loaded, first_caller, contexts[cid], evidence)
                save(case, rep, "primary", first, {})
                if metered.fatal:
                    return
                if len(first_caller.records) != 1:
                    raise ValueError("This frozen probe expects one primary batch")
                record = first_caller.records[0]
                # Classification is also measured on settled controls, solely for diagnostics.
                # A hypothetical cascade would call it only for eligible abstentions.
                classification = await classify(
                    record["payload"],
                    caller(f"{rep}/{cid}/classifier"),
                    (config["evaluation"]["timeout_ms"] - first["duration_ms"]) / 1000,
                )
                classifications.append({"id": cid, "repeat": rep, **classification})
                write_json(output / "classifications.json", classifications)
                if metered.fatal:
                    return
                arms = list(ARMS)
                rng.shuffle(arms)
                for arm in arms:
                    result, notes = copy.deepcopy(first), {}
                    if eligible_policies(first):
                        start = time.monotonic()
                        merged, notes = await refine(
                            record, first, arm, classification, caller(f"{rep}/{cid}/{arm}"), config
                        )
                        result = await evaluate(
                            case,
                            bundle,
                            loaded,
                            StoredBackend(metered, record["payload"], merged),
                            contexts[cid],
                            evidence,
                        )
                        result["duration_ms"] = (
                            first["duration_ms"] + (time.monotonic() - start) * 1000
                        )
                        if arm == "classified_tool":
                            result["duration_ms"] += classification["duration_ms"]
                        notes["usage_note"] = (
                            "Primary only in result; meter physical exchanges separately."
                        )
                    save(case, rep, arm, result, notes)
                    if metered.fatal:
                        return
                print(json.dumps({"repeat": rep, "case": cid, "rows": len(rows)}), flush=True)
    finally:
        write_json(
            output / "summary.json",
            {
                "complete": len(rows) == len(cases) * frozen["repeats"] * 4,
                "rows": len(rows),
                "results": summarize(rows),
                "provider_calls": metered.calls,
                "accounted_before_usd": before,
                "accounted_after_usd": ledger_total(ledger),
                "new_accounted_usd": ledger_total(ledger) - before,
                "unknown_charges": sum(c["cost_usd"] is None for c in ledger.data["calls"]),
                "physical_by_arm": dict(
                    Counter(
                        c["run_id"].split("/")[-1]
                        for c in [
                            json.loads(l)
                            for l in (output / "provider-exchanges.jsonl").read_text().splitlines()
                        ]
                    )
                ),
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--keychain-helper", type=Path)
    args = parser.parse_args()
    frozen, cases, *_ = validate_experiment()
    if args.validate_only:
        print(
            json.dumps(
                {"cases": len(cases), "repeats": frozen["repeats"], "arms": ARMS, "api_calls": 0}
            )
        )
        return
    if args.output is None or args.output.exists() or not args.allow_external:
        parser.error("Fresh output and explicit synthetic egress required")
    if subprocess.check_output(["git", "status", "--porcelain"]):
        parser.error("Commit frozen experiment before live calls")
    path = ROOT / "artifacts/quality/spending.json"
    try:
        with path.with_suffix(".lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if sha256(path) != frozen["starting_ledger_sha256"]:
                raise ValueError("Starting ledger changed")
            credential(args.keychain_helper)
            asyncio.run(measure(args.output, Ledger(path)))
    finally:
        os.environ.pop("OPENROUTER_API_KEY", None)


if __name__ == "__main__":
    main()
