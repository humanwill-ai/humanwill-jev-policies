"""Frozen live-run guards reject changed inputs/source/artifacts before provider use."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evals.step6 import direct_policy_live as run


class DirectPolicyLiveTests(unittest.TestCase):
    def test_changed_input_rejected_before_baseline_or_network(self):
        frozen = json.loads(run.PROTOCOL.read_text())
        frozen["sha256"][next(iter(frozen["sha256"]))] = "0" * 64
        with tempfile.TemporaryDirectory() as tmp:
            protocol = Path(tmp) / "protocol.json"
            protocol.write_text(json.dumps(frozen))
            with patch.object(run, "PROTOCOL", protocol):
                with self.assertRaisesRegex(ValueError, "input changed"):
                    run.validate_experiment(Path(tmp))

    def test_changed_core_rejected_before_baseline_or_network(self):
        with patch.object(run, "source_hashes", return_value={}):
            with self.assertRaisesRegex(ValueError, "evaluator/runner changed"):
                run.validate_experiment(Path("unused"))

    def test_changed_baseline_rejected_without_refreshing_historical_hashes(self):
        frozen = json.loads(run.PROTOCOL.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp)
            (baseline / "manifest.json").write_text("{}")
            with patch.object(run, "source_hashes", return_value=frozen["source_sha256"]):
                with self.assertRaisesRegex(ValueError, "baseline artifact changed"):
                    run.validate_experiment(baseline)
