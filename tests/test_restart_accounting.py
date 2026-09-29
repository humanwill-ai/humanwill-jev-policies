"""An explicit old reservation never becomes a fabricated settled cost or free budget."""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from evals.step6.backends import Ledger
from evals.step6.live_support import ConcurrentMeteredBackend, ledger_total
from evals.step6.restart_accounting import RestartMeteredBackend
from humanwill_policies.errors import PolicyError
from humanwill_policies.serialization import digest


class StubBackend:
    transport = "mock"
    model = "test"
    accepted_models = ("test",)

    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    async def evaluate(self, payload, **kwargs):
        self.calls += 1
        if self.fail:
            raise PolicyError("provider_timeout", "Synthetic timeout")
        return {"model": self.model, "usage": {"cost": 0.001}}


class RestartAccountingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.ledger = Ledger(Path(self.directory.name) / "ledger.json")
        self.old = {"model": "test", "started_unix": 1, "reserved_usd": 0.01, "cost_usd": None}
        self.ledger.data["calls"].append(self.old.copy())
        self.ledger.save()
        self.allowed = {0: digest(self.old)}

    def test_full_reservation_stays_unknown_in_memory_and_disk(self):
        backend = RestartMeteredBackend(StubBackend(), self.ledger, self.allowed)
        asyncio.run(backend.evaluate({"questions": {}}))
        self.assertEqual(self.ledger.data["calls"][0], self.old)
        self.assertEqual(json.loads(self.ledger.path.read_text())["calls"][0], self.old)
        self.assertAlmostEqual(ledger_total(self.ledger), 0.000024696 + 0.01 + 0.001)

    def test_default_guard_and_unlisted_unknown_still_stop(self):
        delegate = StubBackend()
        with self.assertRaises(PolicyError):
            asyncio.run(ConcurrentMeteredBackend(delegate, self.ledger).evaluate({"questions": {}}))
        self.ledger.data["calls"].append(self.old.copy())
        backend = RestartMeteredBackend(delegate, self.ledger, self.allowed)
        with self.assertRaises(PolicyError):
            asyncio.run(backend.evaluate({"questions": {}}))
        self.assertEqual(delegate.calls, 0)

    def test_changed_entry_is_rejected(self):
        self.ledger.data["calls"][0]["reserved_usd"] = 0.02
        with self.assertRaises(ValueError):
            RestartMeteredBackend(StubBackend(), self.ledger, self.allowed)

    def test_reservation_counts_toward_budget_before_call(self):
        self.ledger.data["prior_smoke_usd"] = 4.981
        delegate = StubBackend()
        backend = RestartMeteredBackend(delegate, self.ledger, self.allowed)
        with self.assertRaises(PolicyError) as exc:
            asyncio.run(backend.evaluate({"questions": {}}))
        self.assertEqual(exc.exception.code, "budget_exhausted")
        self.assertEqual(delegate.calls, 0)

    def test_new_failure_stops_both_same_and_new_meter(self):
        delegate = StubBackend(fail=True)
        backend = RestartMeteredBackend(delegate, self.ledger, self.allowed)
        with self.assertRaises(PolicyError):
            asyncio.run(backend.evaluate({"questions": {}}))
        self.assertTrue(backend.fatal)
        for meter in (backend, RestartMeteredBackend(delegate, self.ledger, self.allowed)):
            with self.assertRaises(PolicyError):
                asyncio.run(meter.evaluate({"questions": {}}))
        self.assertEqual(delegate.calls, 1)
        self.assertIsNone(self.ledger.data["calls"][1]["cost_usd"])
