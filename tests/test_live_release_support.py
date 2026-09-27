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
