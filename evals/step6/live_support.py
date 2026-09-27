"""Research-only live accounting; caller holds the existing process-wide ledger lock."""

import asyncio
import copy
import importlib.util
import os
import time
from pathlib import Path

from humanwill_policies.errors import PolicyError

from .backends import RESERVE, Ledger


class ConcurrentMeteredBackend:
    """Permit only this process's known in-flight reservations, never old unknown charges."""

    def __init__(self, backend, ledger):
        self.backend, self.ledger = backend, ledger
        self.transport, self.model = backend.transport, backend.model
        self.accepted_models = backend.accepted_models
        self.pending = set()
        self.fatal = False
        self.calls = []
        self.active = 0
        self.peak_active = 0
        self.lock = asyncio.Lock()

    async def evaluate(self, payload, **kwargs):
        async with self.lock:
            if self.fatal:
                raise PolicyError("run_stopped", "Reconcile failed calls before continuing")
            accounted = self.ledger.data["prior_smoke_usd"]
            for index, call in enumerate(self.ledger.data["calls"]):
                cost = call["cost_usd"]
                if cost is None and index not in self.pending:
                    self.fatal = True
                    raise PolicyError("unreconciled_cost", "Existing unknown charge")
                if cost is not None and cost > call["reserved_usd"]:
                    self.fatal = True
                    raise PolicyError("reservation_exceeded", "Existing charge exceeds reserve")
                accounted += call["reserved_usd"] if cost is None else cost
            if accounted + RESERVE > self.ledger.data["cap_usd"]:
                raise PolicyError("budget_exhausted", "Insufficient remaining authorized budget")
            index = len(self.ledger.data["calls"])
            self.ledger.data["calls"].append(
                {
                    "model": self.model,
                    "started_unix": time.time(),
                    "reserved_usd": RESERVE,
                    "cost_usd": None,
                }
            )
            self.pending.add(index)
            self.ledger.save()
            self.active += 1
            self.peak_active = max(self.peak_active, self.active)
        start = time.perf_counter()
        record = {"ledger_index": index, "questions": sorted(payload["questions"])}
        try:
            response = await self.backend.evaluate(payload, **kwargs)
            async with self.lock:
                self.ledger.settle(index, response.get("usage", {}).get("cost"))
            record.update(model=response.get("model"), usage=copy.deepcopy(response.get("usage")))
            return response
        except BaseException:
            self.fatal = True
            record["failed"] = True
            raise
        finally:
            record["duration_ms"] = (time.perf_counter() - start) * 1000
            self.calls.append(record)
            self.pending.discard(index)
            self.active -= 1


def credential(helper=None):
    if os.environ.get("OPENROUTER_API_KEY"):
        return
    if helper is None:
        raise ValueError("Set OPENROUTER_API_KEY locally or provide the existing Keychain helper")
    spec = importlib.util.spec_from_file_location("humanwill_local_keychain", Path(helper))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    key = module.MacOSKeychain("openrouter").read()
    if not key:
        raise ValueError("Configured Keychain credential unavailable")
    os.environ["OPENROUTER_API_KEY"] = key


def ledger_total(ledger):
    return ledger.data["prior_smoke_usd"] + sum(
        c["cost_usd"] if c["cost_usd"] is not None else c["reserved_usd"]
        for c in ledger.data["calls"]
    )


__all__ = ["ConcurrentMeteredBackend", "Ledger", "credential", "ledger_total"]
