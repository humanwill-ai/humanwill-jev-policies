"""Development-only threshold sensitivity from recorded answers; no provider calls.

This does not select a release threshold or turn reused examples into a holdout.
"""

import argparse
import asyncio
import copy
import json
from pathlib import Path

import yaml

from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import MockBackend

from .metrics import summarize
from .run import ROOT, evidence_for, load_cases, write_json


async def replay(directory):
    cases = {c["id"]: c for c in load_cases(ROOT / "development.json")}
    manifest = json.loads((directory / "manifest.json").read_text())
    from humanwill_policies.serialization import digest

    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    bundle = load_bundle(ROOT / "policies")
    if bundle.sha256 != manifest["bundle_sha256"]:
        raise ValueError("Policy bundle changed; replay would mix rubrics")
    from hashlib import sha256

    if sha256((ROOT / "development.json").read_bytes()).hexdigest() != manifest["dataset_sha256"]:
        raise ValueError("Dataset changed; replay would mix labels")
    if manifest["backend"] != "jev" or digest(config) != manifest["config_sha256"]:
        raise ValueError("Replay requires matching Jev configuration")
    rows = [json.loads(line) for line in (directory / "results.jsonl").read_text().splitlines()]
    rows = [r for r in rows if r["repeat"] == 0]
    sensitivity = {}
    for threshold in [0.0, 0.4, 0.6, 0.8, 0.9]:
        replayed = []
        for row in rows:
            case = cases[row["id"]]
            config_now = copy.deepcopy(config)
            for key, binding in config_now["policies"].items():
                binding["enabled"] = key == case["policy_id"]
                if binding["strategy"] == "scoped_predicates":
                    binding["monitor_min_confidence"] = threshold
            recorded = next(
                p for p in row["result"]["policies"] if p["policy_id"] == case["policy_id"]
            )
            answer = recorded["evidence"]
            answers = {}
            if "choice" in answer:
                answers[case["policy_id"]] = {
                    "type": "choice",
                    **{key: answer[key] for key in ("choice", "confidence", "probabilities")},
                }
            engine = Evaluator(bundle, load_configuration(bundle, config_now), MockBackend(answers))
            result = await engine.evaluate(case["request"], evidence=evidence_for(case))
            replayed.append({**row, "result": result})
        sensitivity[str(threshold)] = {
            key: summarize([r for r in replayed if r["policy_id"] == key])
            for key in config["policies"]
        }
    write_json(
        directory / "threshold-sensitivity.json",
        {
            "purpose": (
                "Development diagnostic only; replay latency/cost are not provider measurements"
            ),
            "thresholds": sensitivity,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    asyncio.run(replay(parser.parse_args().directory))
