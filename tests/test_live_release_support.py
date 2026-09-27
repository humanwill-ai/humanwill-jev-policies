"""Budget concurrency and conservative failure accounting, with no network calls."""

import asyncio
import tempfile
import unittest
from pathlib import Path

from evals.step6.live_support import ConcurrentMeteredBackend, Ledger, ledger_total
from humanwill_policies.errors import PolicyError


class Backend:
    transport = "openrouter"
    model = "synthetic"
    accepted_models = ("synthetic",)

    async def evaluate(self, payload, **kwargs):
        await asyncio.sleep(0.01)
        if payload.get("fail"):
            raise PolicyError("synthetic_failure", "Synthetic failure")
        return {"model": self.model, "usage": {"cost": 0.001}}


class LiveReleaseSupportTests(unittest.TestCase):
    def test_concurrent_calls_reserve_settle_and_count_every_charge(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.json")
            backend = ConcurrentMeteredBackend(Backend(), ledger)

            async def run():
                await asyncio.gather(*(backend.evaluate({"questions": {}}) for _ in range(4)))

            asyncio.run(run())
            self.assertEqual(backend.peak_active, 4)
            self.assertEqual(len(ledger.data["calls"]), 4)
            self.assertAlmostEqual(ledger_total(ledger), ledger.data["prior_smoke_usd"] + 0.004)
            self.assertFalse(backend.fatal)
            self.assertFalse(backend.pending)

    def test_unknown_prior_cost_blocks_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.json")
            ledger.reserve("previous")
            backend = ConcurrentMeteredBackend(Backend(), ledger)
            with self.assertRaisesRegex(PolicyError, "Existing unknown"):
                asyncio.run(backend.evaluate({"questions": {}}))
            self.assertEqual(len(ledger.data["calls"]), 1)

    def test_inflight_reservations_respect_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.json")
            ledger.data["prior_smoke_usd"] = 4.985
            backend = ConcurrentMeteredBackend(Backend(), ledger)

            async def run():
                return await asyncio.gather(
                    *(backend.evaluate({"questions": {}}) for _ in range(2)), return_exceptions=True
                )

            results = asyncio.run(run())
            self.assertEqual(sum(isinstance(r, PolicyError) for r in results), 1)
            self.assertEqual(len(ledger.data["calls"]), 1)
            self.assertLessEqual(ledger_total(ledger), 5)

    def test_error_retains_reservation_and_stops_new_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.json")
            backend = ConcurrentMeteredBackend(Backend(), ledger)

            async def run():
                with self.assertRaises(PolicyError):
                    await backend.evaluate({"questions": {}, "fail": True})
                with self.assertRaisesRegex(PolicyError, "Reconcile"):
                    await backend.evaluate({"questions": {}})

            asyncio.run(run())
            self.assertIsNone(ledger.data["calls"][0]["cost_usd"])
            self.assertEqual(len(ledger.data["calls"]), 1)


class FrozenTrancheTests(unittest.TestCase):
    def test_pending_review_is_not_implicitly_approved_by_old_packet(self):
        import json
        from unittest.mock import patch

        from evals.step6.release_holdout import PROTOCOL, validate_protocol

        data = json.loads(PROTOCOL.read_text())
        data["status"] = "pending_human_labels"
        data.pop("review_record", None)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protocol.json"
            path.write_text(json.dumps(data))
            with patch("evals.step6.release_holdout.PROTOCOL", path):
                with self.assertRaisesRegex(ValueError, "await owner review"):
                    validate_protocol()

    def test_frozen_cases_validate_and_labels_compose_without_model_measurement(self):
        from evals.step6.backends import choice_answer
        from evals.step6.release_holdout import validate_protocol
        from evals.step6.run import evidence_for, select_configuration
        from humanwill_policies import load_configuration
        from humanwill_policies.evaluation import Evaluator
        from humanwill_policies.providers import MockBackend

        _, cases, bundle, config = validate_protocol(require_review=False)
        self.assertEqual(len(cases), 100)
        for case in cases:
            with self.subTest(case=case["id"]):
                backend = MockBackend(
                    {
                        case["policy_id"]: choice_answer(
                            case["expected_scope"] or "insufficient_evidence",
                            ["applicable", "not_applicable", "insufficient_evidence"],
                        )
                    }
                )
                evaluator = Evaluator(
                    bundle,
                    load_configuration(bundle, select_configuration(config, case["policy_id"])),
                    backend,
                )
                result = asyncio.run(
                    evaluator.evaluate(case["request"], evidence=evidence_for(case))
                )
                self.assertEqual(result["decision"], case["expected"])

    def test_changed_frozen_dataset_is_rejected(self):
        from unittest.mock import patch

        from evals.step6.release_holdout import DATASET, validate_protocol

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.json"
            path.write_text(DATASET.read_text().replace("git fetch origin", "git fetch upstream"))
            with patch("evals.step6.release_holdout.DATASET", path):
                with self.assertRaisesRegex(ValueError, "Frozen data"):
                    validate_protocol(require_review=False)
