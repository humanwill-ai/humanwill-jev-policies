"""Full-pack focused-question experiment; authored policies and runtime defaults unchanged."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import yaml

from humanwill_policies import load_configuration
from humanwill_policies.errors import PolicyError
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import JevBackend
from humanwill_policies.runtime import EgressPermit
from humanwill_policies.serialization import digest

from .context_live import compare
from .gates import evaluator_sources
from .live_support import ConcurrentMeteredBackend, Ledger, credential, ledger_total
from .patch_diagnostics import CRITERIA, TASK
from .question_context import ContextBackend, build_pack, sha256
from .reviewed_live import BASE, CATALOG, DATASET, POLICIES, REVIEW, ROOT, build_report
from .run import load_case_bundle, select_configuration, write_json
from .source_approval import load_catalog, source_evidence_for
from .threshold_replay import RecordedBackend, decision_view, validate_rows

PROTOCOL = BASE / "focused-policy-v1/protocol.json"
CONFIG = BASE / "direct-policy-v2/config.yaml"


def source_hashes():
    result = evaluator_sources()
    for name in [
        "source_approval.py",
        "live_support.py",
        "reviewed_live.py",
        "context_live.py",
        "question_context.py",
        "threshold_replay.py",
        "direct_policy_live.py",
        "focused_policy_live.py",
        "patch_diagnostics.py",
        "gates.py",
    ]:
        path = BASE / name
        result[str(path.relative_to(ROOT))] = sha256(path)
    return result


def validate_experiment(baseline):
    frozen = json.loads(PROTOCOL.read_text())
    for path, expected in frozen["sha256"].items():
        if sha256(ROOT / path) != expected:
            raise ValueError(f"Frozen direct-policy input changed: {path}")
    if source_hashes() != frozen["source_sha256"]:
        raise ValueError("Frozen direct-policy evaluator/runner changed")
    for name, expected in frozen["baseline_artifacts_sha256"].items():
        if sha256(baseline / name) != expected:
            raise ValueError(f"Context baseline artifact changed: {name}")
    data, review = json.loads(DATASET.read_text()), json.loads(REVIEW.read_text())
    cases = data["cases"]
    ids = [c["id"] for c in cases]
    if (
        data["synthetic"] is not True
        or review["status"] != "owner_labels_accepted"
        or ids != review["approved_case_ids"]
        or len(ids) != len(set(ids))
        or len(ids) != frozen["case_count"]
        or set(ids) & {r["id"] for r in review["removed"]}
    ):
        raise ValueError("Accepted synthetic case set changed")
    bundle = load_case_bundle(cases, POLICIES)
    if bundle.sha256 != frozen["bundle_sha256"]:
        raise ValueError("Frozen policy text changed")
    config = yaml.safe_load(CONFIG.read_text())
    pack = json.loads((BASE / "context-v1/contexts.json").read_text())
    observations = json.loads((BASE / "context-v1/observations.json").read_text())["cases"]
    if pack != build_pack(cases, observations):
        raise ValueError("Context differs from frozen event observations")
    contexts = {c["id"]: c for c in pack["cases"]}
    catalog = load_catalog(CATALOG)
    for case in cases:
        selected = select_configuration(config, case["policy_id"], case.get("also_policy_ids", []))
        load_configuration(bundle, selected)
        source_evidence_for(case, catalog)
    rows = [json.loads(line) for line in (baseline / "results.jsonl").read_text().splitlines()]
    validate_rows(cases, rows, contexts)
    return frozen, (cases, bundle, config, catalog), contexts, rows


class FocusedBackend:
    """Research-only task replacement after the unchanged event/context wrapper."""

    def __init__(self, delegate, request_id, exchanges=None):
        self.delegate, self.request_id, self.exchanges = delegate, request_id, exchanges
        self.transport, self.model = delegate.transport, delegate.model
        self.accepted_models = delegate.accepted_models

    async def evaluate(self, payload, **kwargs):
        request = copy.deepcopy(payload)
        for q in request["questions"].values():
            if set(q["criteria"]) != set(CRITERIA):
                raise PolicyError("unsupported_experiment", "Only scoped predicates in this run")
            q["instructions"]["task"] = TASK
            q["criteria"] = copy.deepcopy(CRITERIA)
        note = json.loads(PROTOCOL.read_text())["short_context"].get(self.request_id)
        if note:
            request["state"]["assessment_context"]["operation_semantics"] = note
        from humanwill_policies.serialization import canonical

        if len(canonical(request).encode()) > 24000:
            raise PolicyError("batch_limit", "Focused payload exceeds provider limit")
        exchange = {"request_id": self.request_id, "payload": request}
        try:
            response = await self.delegate.evaluate(request, **kwargs)
            exchange["raw_response"] = response
            return response
        except PolicyError as exc:
            exchange["error"] = exc.code
            raise
        finally:
            if self.exchanges is not None:
                with self.exchanges.open("a") as stream:
                    stream.write(json.dumps(exchange) + "\n")


class ReplayBackend(RecordedBackend):
    """Preserve the one recorded malformed answer; do not invent its discarded response."""

    def __init__(self, result):
        super().__init__(result)
        self.malformed = any(e["code"] == "malformed_response" for e in result["errors"])

    async def evaluate(self, payload, **kwargs):
        if self.malformed:
            self.payloads.append(copy.deepcopy(payload))
            raise PolicyError("malformed_response", "Recorded invalid answer remains an error")
        return await super().evaluate(payload, **kwargs)


async def aligned_control(cases, old_rows, contexts, bundle, config, catalog):
    rows = []
    for case, old in zip(cases, old_rows, strict=True):
        # First reproduce the actual old0.80 decision; then change only not_applicable to0.70.
        for gate in (0.8, 0.7):
            document = copy.deepcopy(config)
            document["outcome_thresholds"]["not_applicable"] = gate
            selected = select_configuration(
                document, case["policy_id"], case.get("also_policy_ids", [])
            )
            backend = ReplayBackend(old["result"])
            result = await Evaluator(
                bundle,
                load_configuration(bundle, selected),
                ContextBackend(backend, case["request"], contexts[case["id"]]),
            ).evaluate(case["request"], evidence=source_evidence_for(case, catalog))
            if not backend.malformed:
                backend.validate_consumed()
            if gate == 0.8:
                if decision_view(result) != decision_view(old["result"]):
                    raise ValueError(f"Recorded decisions not reproduced: {case['id']}")
                if result["configuration_sha256"] != old["result"]["configuration_sha256"]:
                    raise ValueError("Original configuration not reproduced")
        row = copy.deepcopy(old)
        row["result"] = result
        rows.append(row)
    return rows


async def measure(output, baseline, ledger):
    frozen, validated, contexts, old_rows = validate_experiment(baseline)
    cases, bundle, config, catalog = validated
    control = await aligned_control(cases, old_rows, contexts, bundle, config, catalog)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "threshold-aligned-control.json", control)
    before = ledger_total(ledger)
    metered = ConcurrentMeteredBackend(JevBackend(config["provider"]), ledger)
    write_json(
        output / "manifest.json",
        {
            "format": "humanwill.focused-policy-run/1",
            "protocol": frozen,
            "started_at": datetime.now(UTC).isoformat(),
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"])),
            "backend": "jev",
            "retries": 0,
            "case_count": len(cases),
            "counts_by_packet": dict(Counter(c["review_packet"] for c in cases)),
            "cost_before_usd": before,
        },
    )
    rows = []
    try:
        for case in cases:
            selected = select_configuration(
                config, case["policy_id"], case.get("also_policy_ids", [])
            )
            backend = ContextBackend(
                FocusedBackend(metered, case["id"], output / "provider-exchanges.jsonl"),
                case["request"],
                contexts[case["id"]],
                allow_context_egress=True,
            )
            engine = Evaluator(bundle, load_configuration(bundle, selected), backend)
            result = await engine.evaluate(
                case["request"],
                evidence=source_evidence_for(case, catalog),
                egress=EgressPermit(digest(case["request"]), bundle.sha256, backend.transport),
            )
            row = {
                k: copy.deepcopy(case[k])
                for k in (
                    "id",
                    "policy_id",
                    "family",
                    "language",
                    "tags",
                    "review_packet",
                    "expected_by_policy",
                    "scope_by_policy",
                    "expected_composed",
                )
            }
            row.update(
                stage=case["request"]["stage"],
                result=result,
                context_sha256=digest(
                    {
                        **contexts[case["id"]]["context"],
                        **(
                            {"operation_semantics": frozen["short_context"][case["id"]]}
                            if case["id"] in frozen["short_context"]
                            else {}
                        ),
                    }
                ),
            )
            rows.append(row)
            with (output / "results.jsonl").open("a") as stream:
                stream.write(json.dumps(row) + "\n")
            print(json.dumps({"case": case["id"], "observed": result["decision"]}), flush=True)
            if metered.fatal:
                break
    finally:
        write_json(
            output / "summary.json",
            build_report(rows, cases, metered, before, ledger_total(ledger)),
        )
        comparison = compare(control, rows)
        comparison["focused_model_scope"] = comparison.pop("context_model_scope")
        comparison["baseline_kind"] = (
            "Recorded full-policy answers replayed at0.80/0.70/0.80; not a fresh control"
        )
        write_json(output / "comparison.json", comparison)
        write_json(output / "original-live-comparison.json", compare(old_rows, rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--keychain-helper", type=Path)
    args = parser.parse_args()
    _, validated, _, _ = validate_experiment(args.baseline)
    if args.validate_only:
        print(json.dumps({"valid_cases": len(validated[0]), "provider_calls": 0}))
        return
    if args.output is None:
        parser.error("New output directory required")
    if subprocess.check_output(["git", "status", "--porcelain"]):
        parser.error("Commit the frozen experiment before live execution")
    if not args.allow_external:
        parser.error("Explicit synthetic event and context egress flag required")
    credential(args.keychain_helper)
    path = ROOT / "artifacts/quality/spending.json"
    try:
        with path.with_suffix(".lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            asyncio.run(measure(args.output, args.baseline, Ledger(path)))
    finally:
        os.environ.pop("OPENROUTER_API_KEY", None)


if __name__ == "__main__":
    main()
