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
        config = yaml.safe_load((ROOT / "config-integrity-ab.yaml").read_text())
        before = copy.deepcopy(config)
        for extra, expected in [
            ([], {"EVAL-SW-001"}),
            (["EVAL-INJ-001"], {"EVAL-SW-001", "EVAL-INJ-001"}),
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
                choice = "compliant" if key == "EVAL-INJ-001" else "not_applicable"
                return {
                    "model": "test",
                    "answers": {key: choice_answer(choice, question["criteria"])},
                    "usage": {"cost": 0},
                }

        self_test = self
        with TemporaryDirectory() as directory:
            args = Namespace(
                output=Path(directory) / "result",
                limit=1,
                repeats=1,
                dataset=ROOT / "development-v2.json",
                policies=ROOT / "policies-v3",
                config=ROOT / "config-integrity-ab.yaml",
                backend="keyword",
                also_policy=["EVAL-INJ-001"],
            )
            with patch("evals.step6.run.KeywordBackend", FakeBackend), patch("builtins.print"):
                asyncio.run(run(args))
            self.assertEqual(set(seen), {"EVAL-INJ-001", "EVAL-SW-001"})
            manifest = json.loads((args.output / "manifest.json").read_text())
            self.assertEqual(manifest["also_policies"], ["EVAL-INJ-001"])
            row = json.loads((args.output / "results.jsonl").read_text())
            self.assertEqual(row["result"]["decision"], "allow")
            self.assertEqual(len(row["result"]["evaluation"]["batches"]), 2)

    def test_combined_runs_cannot_silently_enter_isolated_calibration(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "manifest.json").write_text(json.dumps({"also_policies": ["EVAL-INJ-001"]}))
            with self.assertRaisesRegex(ValueError, "Combined-policy"):
                load_recordings([path])
