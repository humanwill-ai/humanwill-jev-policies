"""Offline exact-payload replay and summary of the frozen preview campaign."""

import argparse
import asyncio
import copy
import json
from collections import Counter, defaultdict
from pathlib import Path

from evals.step6.metrics import percentile, rate
from evals.step6.preview_full_pack import evaluate, summarize, validate_experiment
from evals.step6.reviewed_live import observed_policy


class Replay:
    transport = "openrouter"
    model = "typesafe/jev-1.13"
    accepted_models = ("typesafe/jev-1.13-20260917",)

    def __init__(self, records):
        self.records = list(records)
        self.index = 0

    async def evaluate(self, payload, **kwargs):
        record = self.records[self.index]
        self.index += 1
        if payload != record["payload"]:
            raise ValueError("Recorded provider payload differs")
        return copy.deepcopy(record["raw_response"])


async def audit(directory):
    protocol, cases, bundle, config, contexts, catalog = validate_experiment()
    cases = {c["id"]: c for c in cases}
    rows = [json.loads(x) for x in (directory / "results.jsonl").read_text().splitlines()]
    exchanges = defaultdict(list)
    for line in (directory / "provider-exchanges.jsonl").read_text().splitlines():
        record = json.loads(line)
        exchanges[record["run_id"]].append(record)
    expected_keys = {(rep, cid) for rep in range(protocol["repeats"]) for cid in cases}
    actual_keys = [(r["repeat"], r["id"]) for r in rows]
    assert len(actual_keys) == len(expected_keys) and set(actual_keys) == expected_keys
    count = 0
    for row in rows:
        replay = Replay(exchanges.pop(f"{row['repeat']}/{row['id']}", []))
        result = await evaluate(cases[row["id"]], bundle, config, replay, contexts, catalog)
        actual = copy.deepcopy(row["result"])
        result.pop("duration_ms")
        actual.pop("duration_ms")
        assert result == actual, (row["repeat"], row["id"])
        assert replay.index == len(replay.records)
        count += replay.index
    assert not exchanges
    failures = [
        {
            "repeat": r["repeat"],
            "id": r["id"],
            "expected": r["expected_composed"],
            "observed": r["result"]["decision"],
            "policies": [
                {"id": p["policy_id"], "reasons": p["reasons"]}
                for p in r["result"]["policies"]
                if p["status"] == "error"
            ],
        }
        for r in rows
        if r["result"]["decision"] != r["expected_composed"]
    ]
    per_policy = {}
    for pid in sorted(config["policies"]):
        passes = []
        for rep in range(protocol["repeats"]):
            pairs = [
                (r["expected_by_policy"][pid], observed_policy(p))
                for r in rows
                if r["repeat"] == rep and pid in r["expected_by_policy"]
                for p in r["result"]["policies"]
                if p["policy_id"] == pid
            ]
            allow = [v for e, v in pairs if e == "allow"]
            block = [v for e, v in pairs if e == "block"]
            passes.append(
                {
                    "cases": len(pairs),
                    "false_block_fail_closed": rate(sum(v != "allow" for v in allow), len(allow)),
                    "missed_violation_fail_open": rate(
                        sum(v != "block" for v in block), len(block)
                    ),
                    "unexpected_errors": sum(
                        e != "evaluation_error" and v == "evaluation_error" for e, v in pairs
                    ),
                    "wrong_definitive": sum(v != "evaluation_error" and e != v for e, v in pairs),
                }
            )
        per_policy[pid] = passes

    def timing(values):
        return {f"p{p}_ms": percentile(values, p / 100) for p in (50, 95, 99)}

    report = {
        "offline_exact_replay": {"event_views": len(rows), "provider_payloads": count},
        "summary": summarize(rows),
        "passes": [
            summarize([r for r in rows if r["repeat"] == rep]) for rep in range(protocol["repeats"])
        ],
        "per_policy": per_policy,
        "failures": failures,
        "followup_status": dict(
            Counter(r["result"].get("policy_assessment", {}).get("status") for r in rows)
        ),
        "latency_all": timing([r["result"]["duration_ms"] for r in rows]),
        "latency_with_api": timing(
            [
                r["result"]["duration_ms"]
                for r in rows
                if (r["result"].get("evaluation") or {}).get("batches")
            ]
        ),
    }
    (directory / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "per_policy"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    asyncio.run(audit(parser.parse_args().directory))
