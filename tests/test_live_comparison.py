"""Live comparison activation/accounting contracts without network calls."""

import asyncio
import copy
import json
import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

from evals.step6.backends import choice_answer
from evals.step6.calibrate import load_recordings
from evals.step6.run import ROOT, run, select_configuration


class ComparisonTests(unittest.TestCase):
    def test_activation_is_explicit_and_does_not_mutate_configuration(self):
        config = yaml.safe_load((ROOT / "config-disclosure-v2.yaml").read_text())
        before = copy.deepcopy(config)
        for extra, expected in [
            ([], {"EVAL-SW-001"}),
            (["EVAL-PROD-001"], {"EVAL-SW-001", "EVAL-PROD-001"}),
        ]:
            selected = select_configuration(config, "EVAL-SW-001", extra)
            self.assertEqual({k for k, v in selected["policies"].items() if v["enabled"]}, expected)
            self.assertEqual(config, before)
        with self.assertRaisesRegex(ValueError, "Unknown additional"):
            select_configuration(config, "EVAL-SW-001", ["TYPO"])

    def test_both_policies_are_evaluated_and_activation_is_recorded(self):
        seen = []

        class FakeBackend:
            transport, model, accepted_models = "mock", "test", ("test",)

            async def evaluate(self, payload, **kwargs):
                self_test.assertEqual(len(payload["questions"]), 1)
                key, question = next(iter(payload["questions"].items()))
                seen.append(key)
                choice = "not_applicable"
                return {
                    "model": "test",
                    "answers": {key: choice_answer(choice, question["criteria"])},
                    "usage": {"cost": 0},
                }

        self_test = self
        with TemporaryDirectory() as directory:
            temp = Path(directory)
            config = yaml.safe_load((ROOT / "config-disclosure-v2.yaml").read_text())
            config["evaluation"]["questions_per_batch"] = 1
            (temp / "config.yaml").write_text(yaml.safe_dump(config))
            data = json.loads((ROOT / "development-v2.json").read_text())
            # Both existing scoped policies apply at the tool-action stage.
            data["cases"] = [
                c for c in data["cases"] if c["id"] == "eval-sw-v2-local-edit-tool_action"
            ]
            (temp / "cases.json").write_text(json.dumps(data))
            args = Namespace(
                output=Path(directory) / "result",
                limit=1,
                repeats=1,
                dataset=temp / "cases.json",
                policies=ROOT / "policies-v2",
                config=temp / "config.yaml",
                backend="keyword",
                also_policy=["EVAL-PROD-001"],
            )
            with patch("evals.step6.run.KeywordBackend", FakeBackend), patch("builtins.print"):
                asyncio.run(run(args))
            self.assertEqual(set(seen), {"EVAL-PROD-001", "EVAL-SW-001"})
            manifest = json.loads((args.output / "manifest.json").read_text())
            self.assertEqual(manifest["also_policies"], ["EVAL-PROD-001"])
            row = json.loads((args.output / "results.jsonl").read_text())
            self.assertEqual(row["result"]["decision"], "allow")
            self.assertEqual(len(row["result"]["evaluation"]["batches"]), 2)

    def test_combined_runs_cannot_silently_enter_isolated_calibration(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "manifest.json").write_text(json.dumps({"also_policies": ["EVAL-PROD-001"]}))
            with self.assertRaisesRegex(ValueError, "Combined-policy"):
                load_recordings([path])
