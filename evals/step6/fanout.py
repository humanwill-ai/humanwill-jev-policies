"""Research-only multi-question fan-out; the shipped evaluator is unchanged."""

import argparse
import asyncio
import copy
import fcntl
import json
import os
import random
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from humanwill_policies.errors import PolicyError
from humanwill_policies.providers import JevBackend, validate_response
from humanwill_policies.questions import scoped_variant
from humanwill_policies.serialization import canonical

from .live_support import Ledger, credential, ledger_total
from .policy_isolation import RecordedBackend
from .preview_full_pack import evaluate, summarize
from .preview_full_pack import load_inputs as preview_inputs
from .question_context import sha256
from .restart_accounting import RestartMeteredBackend
from .reviewed_live import ROOT
from .run import write_json

BASE = ROOT / "evals/step6/fanout-v1"
SCOPE = {"applicable", "not_applicable", "insufficient_evidence"}


def expand(payload):
    result = copy.deepcopy(payload)
    questions, mapping = {}, {}
    for pid, question in payload["questions"].items():
        variants = ["q05"]
        if set(question["criteria"]) == SCOPE:
            variants += ["q04"]
            if payload["state"]["stage"] == "tool_action":
                variants += ["tool_action"]
        mapping[pid] = {}
        for variant in variants:
            key = f"{variant}__{pid}"
            mapping[pid][variant] = key
            questions[key] = scoped_variant(question, variant)
    result["questions"] = questions
    if len(questions) > 16 or len(canonical(result).encode()) > 24000:
        raise PolicyError("batch_limit", "Expanded questions exceed unchanged batch limits")
    return result, mapping


def qualified(answer, thresholds):
    probs = answer["probabilities"]
    maximum = max(probs.values())
    return (
        answer["confidence"] >= thresholds[answer["choice"]]
        and sum(p == maximum for p in probs.values()) == 1
    )


class FanoutBackend:
    """One physical request; expose cached views to the existing bounded evaluator.

    Its ordinary eligibility, primary preservation, confidence, agreement and
    trusted-predicate logic still apply. Cached continuation is not a paid call.
    """

    def __init__(self, backend, thresholds):
        self.backend, self.thresholds = backend, thresholds
        self.transport, self.model = backend.transport, backend.model
        self.accepted_models = backend.accepted_models
        self.original = self.raw = self.mapping = None
        self.virtual_calls = 0
        self.notes = {}

    async def evaluate(self, payload, **kwargs):
        self.virtual_calls += 1
        if self.virtual_calls == 1:
            expanded, self.mapping = expand(payload)
            self.original = copy.deepcopy(payload)
            self.raw = await self.backend.evaluate(expanded, **kwargs)
            validate_response(self.raw, expanded["questions"], self.accepted_models)
            response = copy.deepcopy(self.raw)
            response["answers"] = {
                pid: copy.deepcopy(self.raw["answers"][variants["q05"]])
                for pid, variants in self.mapping.items()
            }
            return response
        if self.virtual_calls != 2 or self.raw is None:
            raise PolicyError("experiment_shape", "Only one original batch and cached continuation")
        variant = "tool_action" if payload["state"]["stage"] == "tool_action" else "q04"
        expected = copy.deepcopy(self.original)
        expected["questions"] = {
            pid: scoped_variant(q, variant) for pid, q in self.original["questions"].items()
        }
        if payload != expected:
            raise PolicyError("experiment_shape", "Unexpected continuation payload")
        response = {
            "model": self.raw["model"],
            "usage": {"input_tokens": 0, "output_tokens": 0, "cost": 0},
            "answers": {},
        }
        for pid, variants in self.mapping.items():
            primary = self.raw["answers"][variants["q05"]]
            candidates = {v: self.raw["answers"][key] for v, key in variants.items() if v != "q05"}
            passing = {v: a for v, a in candidates.items() if qualified(a, self.thresholds)}
            # A qualified alternative contradicting Q05 (including qualified IE)
            # vetoes replacement; keep the primary low-confidence error.
            if any(a["choice"] != primary["choice"] for a in passing.values()):
                selected = primary
                note = "qualified_disagreement"
            elif passing:
                selected_variant = variant if variant in passing else "q04"
                selected = passing[selected_variant]
                note = selected_variant
            else:
                selected = primary
                note = "no_qualifying_alternative"
            response["answers"][pid] = copy.deepcopy(selected)
            self.notes[pid] = note
        return response


def load_inputs():
    _, cases, bundle, config, contexts, catalog = preview_inputs()
    fresh = json.loads((BASE / "fresh-cases.json").read_text())
    cases += fresh["cases"]
    contexts.update({c["id"]: c for c in fresh["contexts"]})
    return cases, bundle, config, contexts, catalog


def validate():
    frozen = json.loads((BASE / "protocol.json").read_text())
    for name, expected in frozen["sha256"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f"Frozen fan-out input changed: {name}")
    inputs = load_inputs()
    assert [c["id"] for c in inputs[0]] == frozen["case_ids"]
    return frozen, inputs


async def measure(output, ledger):
    frozen, (cases, bundle, config, contexts, catalog) = validate()
    output.mkdir(parents=True, exist_ok=False)
    before = ledger_total(ledger)
    ceiling = min(ledger.data["cap_usd"], before + frozen["additional_cap_usd"])
    backend = RestartMeteredBackend(
        JevBackend(config["provider"]),
        ledger,
        {int(k): v for k, v in frozen["carried_reservations"].items()},
    )
    original = backend.evaluate
    attempts = 0

    async def bounded(payload, **kwargs):
        nonlocal attempts
        if attempts >= frozen["max_physical_calls"]:
            backend.fatal = True
            raise PolicyError("experiment_limit", "Frozen physical-call ceiling reached")
        attempts += 1
        return await original(payload, **kwargs)

    backend.evaluate = bounded
    write_json(
        output / "manifest.json",
        {
            "protocol": frozen,
            "started_at": datetime.now(UTC).isoformat(),
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "accounted_before_usd": before,
            "ceiling_usd": ceiling,
        },
    )
    rng = random.Random(frozen["seed"])
    rows = []
    try:
        for rep in range(frozen["repeats"]):
            order = list(cases)
            rng.shuffle(order)
            for case in order:
                arms = ["sequential", "fanout"]
                rng.shuffle(arms)
                for arm in arms:
                    caller = RecordedBackend(
                        backend,
                        output / "exchanges.jsonl",
                        f"{rep}/{case['id']}/{arm}",
                        ledger,
                        ceiling,
                    )
                    wrapped = (
                        FanoutBackend(caller, config["outcome_thresholds"])
                        if arm == "fanout"
                        else caller
                    )
                    result = await evaluate(case, bundle, config, wrapped, contexts, catalog)
                    row = {
                        key: copy.deepcopy(case[key])
                        for key in (
                            "id",
                            "expected_composed",
                            "expected_by_policy",
                            "scope_by_policy",
                        )
                    }
                    row.update(
                        repeat=rep,
                        arm=arm,
                        cohort="fresh_provisional"
                        if case["id"].startswith("fanout-fresh-")
                        else "reviewed",
                        result=result,
                        physical_calls=len(caller.records),
                        physical_cost_usd=(
                            sum(x["raw_response"]["usage"]["cost"] for x in caller.records)
                            if all(
                                isinstance(
                                    x.get("raw_response", {}).get("usage", {}).get("cost"),
                                    (int, float),
                                )
                                for x in caller.records
                            )
                            else None
                        ),
                        notes=wrapped.notes if arm == "fanout" else {},
                    )
                    rows.append(row)
                    with (output / "results.jsonl").open("a") as stream:
                        stream.write(json.dumps(row) + "\n")
                    if backend.fatal:
                        return
                print(
                    json.dumps(
                        {
                            "repeat": rep,
                            "id": case["id"],
                            "rows": len(rows),
                            "calls": len(backend.calls),
                        }
                    ),
                    flush=True,
                )
    finally:
        write_json(
            output / "summary.json",
            {
                "complete": len(rows) == len(cases) * frozen["repeats"] * 2,
                "rows": len(rows),
                "accounted_before_usd": before,
                "accounted_after_usd": ledger_total(ledger),
                "new_accounted_usd": ledger_total(ledger) - before,
                "provider_calls": backend.calls,
                "results": {
                    cohort: {
                        arm: summarize(
                            [r for r in rows if r["cohort"] == cohort and r["arm"] == arm]
                        )
                        for arm in ["sequential", "fanout"]
                    }
                    for cohort in ["reviewed", "fresh_provisional"]
                },
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--keychain-helper", type=Path)
    args = parser.parse_args()
    frozen, inputs = validate()
    if args.validate_only:
        print(json.dumps({"cases": len(inputs[0]), "repeats": frozen["repeats"], "api_calls": 0}))
        return
    if args.output is None or args.output.exists() or not args.allow_external:
        parser.error("Fresh output and explicit egress required")
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
