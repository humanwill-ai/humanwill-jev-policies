"""Offline counterfactual decisions from saved Jev answers; never calls a provider."""

import argparse
import asyncio
import copy
import json
from collections import Counter
from pathlib import Path

import yaml

from humanwill_policies import load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import MockBackend
from humanwill_policies.serialization import digest

from .question_context import ContextBackend, sha256
from .reviewed_live import BASE, CATALOG, CONFIG, DATASET, POLICIES, ROOT, observed_policy
from .run import load_case_bundle, select_configuration, write_json
from .source_approval import load_catalog, source_evidence_for

PROTOCOL = BASE / "threshold-replay-v1/protocol.json"
BASELINE = {"applicable": 0.8, "not_applicable": 0.8, "insufficient_evidence": 0.8}
CANDIDATE = {**BASELINE, "not_applicable": 0.7}


def configuration_v4(config, thresholds):
    result = copy.deepcopy(config)
    result["format"] = "humanwill.config/4"
    result["outcome_thresholds"] = dict(thresholds)
    for binding in result["policies"].values():
        binding.pop("monitor_min_confidence", None)
        binding.get("evaluation_profile", {}).pop("min_confidence", None)
    return result


def decision_view(result):
    """Ignore only execution bookkeeping; retain every policy's evidence and errors."""
    excluded = {"duration_ms", "evaluation", "simulated", "configuration_sha256"}
    return {k: v for k, v in result.items() if k not in excluded}


class RecordedBackend(MockBackend):
    def __init__(self, result):
        self.answers = {
            p["policy_id"]: {
                "type": "choice",
                **{k: p["evidence"][k] for k in ("choice", "confidence", "probabilities")},
            }
            for p in result["policies"]
            if "choice" in p["evidence"]
        }
        super().__init__(self.answers)
        self.payloads = []

    async def evaluate(self, payload, **kwargs):
        self.payloads.append(copy.deepcopy(payload))
        return await super().evaluate(payload, **kwargs)

    def validate_consumed(self):
        ids = [key for payload in self.payloads for key in payload["questions"]]
        if len(ids) != len(set(ids)) or set(ids) != set(self.answers):
            raise ValueError("Replay did not consume each recorded answer exactly once")


def validate_rows(cases, rows, contexts):
    if [r["id"] for r in rows] != [c["id"] for c in cases]:
        raise ValueError("Recorded rows must cover the full ordered accepted case set")
    for case, row in zip(cases, rows, strict=True):
        for key in ("expected_by_policy", "scope_by_policy", "expected_composed"):
            if row[key] != case[key]:
                raise ValueError("Recorded labels differ from accepted cases")
        if row["result"]["request_sha256"] != digest(case["request"]) or row[
            "context_sha256"
        ] != digest(contexts[case["id"]]["context"]):
            raise ValueError("Recorded result does not match its exact event/context")


def load_inputs(source):
    protocol = json.loads(PROTOCOL.read_text())
    for path, expected in protocol["sha256"].items():
        if sha256(ROOT / path) != expected:
            raise ValueError(f"Frozen replay input/source changed: {path}")
    for name, expected in protocol["recorded_artifacts_sha256"].items():
        if sha256(source / name) != expected:
            raise ValueError(f"Recorded artifact changed: {name}")
    cases = json.loads(DATASET.read_text())["cases"]
    review = json.loads((BASE / "release/owner-review-v1.json").read_text())
    if [c["id"] for c in cases] != review["approved_case_ids"] or len(cases) != 175:
        raise ValueError("Accepted case set changed")
    contexts = {
        c["id"]: c for c in json.loads((BASE / "context-v1/contexts.json").read_text())["cases"]
    }
    rows = [json.loads(line) for line in (source / "results.jsonl").read_text().splitlines()]
    validate_rows(cases, rows, contexts)
    bundle = load_case_bundle(cases, POLICIES)
    if bundle.sha256 != protocol["bundle_sha256"]:
        raise ValueError("Policy bundle changed")
    scope = json.loads((BASE / "release-scope-v1/manifest.json").read_text())
    suites = {c["id"]: c["suite"] for c in scope["cases"]}
    if set(suites) != {c["id"] for c in cases}:
        raise ValueError("Scope manifest does not cover all accepted cases")
    return protocol, cases, rows, contexts, bundle, yaml.safe_load(CONFIG.read_text()), suites


async def replay_case(case, recorded, context, bundle, config, catalog):
    results, payloads = {}, []
    selected = select_configuration(config, case["policy_id"], case.get("also_policy_ids", []))
    for name, document in [
        ("legacy", selected),
        ("baseline", configuration_v4(selected, BASELINE)),
        ("candidate", configuration_v4(selected, CANDIDATE)),
    ]:
        backend = RecordedBackend(recorded["result"])
        engine = Evaluator(
            bundle,
            load_configuration(bundle, document),
            ContextBackend(backend, case["request"], context),
        )
        results[name] = await engine.evaluate(
            case["request"], evidence=source_evidence_for(case, catalog)
        )
        backend.validate_consumed()
        payloads.append(backend.payloads)
    if decision_view(results["legacy"]) != decision_view(recorded["result"]):
        raise ValueError(f"Original decisions/evidence not reproduced: {case['id']}")
    if results["legacy"]["configuration_sha256"] != recorded["result"]["configuration_sha256"]:
        raise ValueError("Original configuration digest not reproduced")
    if decision_view(results["baseline"]) != decision_view(results["legacy"]):
        raise ValueError("Symmetric config/4 changed baseline decisions")
    if not payloads[0] == payloads[1] == payloads[2]:
        raise ValueError("Threshold change altered questions or supplied context")
    return {"id": case["id"], **results}


def counts(pairs):
    labels = Counter(expected for expected, _ in pairs)
    return {
        "cases": len(pairs),
        "expected": dict(labels),
        "outcomes": dict(Counter(observed for _, observed in pairs)),
        "exact_matches": sum(a == b for a, b in pairs),
        "false_blocks_if_fail_closed": sum(a == "allow" and b != "allow" for a, b in pairs),
        "explicit_false_violations": sum(a == "allow" and b == "block" for a, b in pairs),
        "missed_violations_if_fail_closed": sum(a == "block" and b == "allow" for a, b in pairs),
        "specified_errors": sum(
            a != "evaluation_error" and b == "evaluation_error" for a, b in pairs
        ),
        "unknown_correctly_indeterminate": sum(a == b == "evaluation_error" for a, b in pairs),
        "unknown_incorrectly_allowed": sum(
            a == "evaluation_error" and b == "allow" for a, b in pairs
        ),
    }


def report(cases, replayed, suites):
    if [r["id"] for r in replayed] != [c["id"] for c in cases]:
        raise ValueError("Report requires every accepted case exactly once in order")
    by_id = {r["id"]: r for r in replayed}
    summary = {}
    changes = []
    for suite in ("all", "generic_policy", "advanced_commands"):
        selected = [c for c in cases if suite == "all" or suites[c["id"]] == suite]
        summary[suite] = {}
        for variant in ("baseline", "candidate"):
            pairs, policy_pairs = [], {}
            for c in selected:
                result = by_id[c["id"]][variant]
                pairs.append((c["expected_composed"], result["decision"]))
                for p in result["policies"]:
                    pid = p["policy_id"]
                    if pid in c["expected_by_policy"]:
                        policy_pairs.setdefault(pid, []).append(
                            (c["expected_by_policy"][pid], observed_policy(p))
                        )
            summary[suite][variant] = {
                "events": counts(pairs),
                "policy_judgments": counts(
                    [pair for pairs in policy_pairs.values() for pair in pairs]
                ),
                "by_policy": {pid: counts(pairs) for pid, pairs in sorted(policy_pairs.items())},
            }
    for c in cases:
        row = by_id[c["id"]]
        changed = []
        for before, after in zip(
            row["baseline"]["policies"], row["candidate"]["policies"], strict=True
        ):
            if before != after:
                if before["evidence"] != after["evidence"]:
                    raise ValueError("A replay changed model evidence")
                pid = before["policy_id"]
                changed.append(
                    {
                        "policy_id": pid,
                        "expected": c["expected_by_policy"][pid],
                        "before": observed_policy(before),
                        "after": observed_policy(after),
                        "choice": before["evidence"].get("choice"),
                        "confidence": before["evidence"].get("confidence"),
                    }
                )
        if changed:
            changes.append(
                {
                    "id": c["id"],
                    "suite": suites[c["id"]],
                    "expected": c["expected_composed"],
                    "before": row["baseline"]["decision"],
                    "after": row["candidate"]["decision"],
                    "policies": changed,
                }
            )
    return {
        "format": "humanwill.threshold-replay/1",
        "api_calls": 0,
        "new_cost_usd": 0,
        "thresholds": {"baseline": BASELINE, "candidate": CANDIDATE},
        "baseline_reproduced": len(replayed),
        "summary": summary,
        "changes": changes,
        "limits": (
            "Counterfactual decisions on reused answers, not new model accuracy, stability, "
            "latency or independent qualification. All assessments remain monitor; "
            "fail-closed metrics are hypothetical."
        ),
    }


async def replay(source, output):
    protocol, cases, rows, contexts, bundle, config, suites = load_inputs(source)
    catalog = load_catalog(CATALOG)
    replayed = []
    for case, recorded in zip(cases, rows, strict=True):
        replayed.append(
            await replay_case(case, recorded, contexts[case["id"]], bundle, config, catalog)
        )
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "protocol.json", protocol)
    write_json(output / "summary.json", report(cases, replayed, suites))
    with (output / "results.jsonl").open("w") as stream:
        for row in replayed:
            stream.write(json.dumps(row) + "\n")
    return report(cases, replayed, suites)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "artifacts/quality/context-live-v1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(replay(args.source, args.output))
    print(json.dumps({"summary": result["summary"], "changes": result["changes"]}, indent=2))


if __name__ == "__main__":
    main()
