"""Explicit owner-authorized carry of a frozen unresolved reservation; no cost invention."""

from humanwill_policies.serialization import digest

from .live_support import ConcurrentMeteredBackend


class RestartMeteredBackend(ConcurrentMeteredBackend):
    """Charge exact authorized old reservations in full while preserving cost_usd=None.

    The inherited pending set exempts these entries from the unknown-charge stop,
    but its accounting still debits their full reservation. They are not in-flight
    HTTP calls. No new unknown charge is exempt; the parent still stops on failure.
    This opt-in research class does not change the default metering guard.
    """

    def __init__(self, backend, ledger, carried_reservations):
        super().__init__(backend, ledger)
        for index, expected_digest in carried_reservations.items():
            if type(index) is not int or index < 0 or index >= len(ledger.data["calls"]):
                raise ValueError("Unknown carried ledger entry")
            call = ledger.data["calls"][index]
            if (
                digest(call) != expected_digest
                or call["cost_usd"] is not None
                or type(call["reserved_usd"]) not in (int, float)
                or not 0 < call["reserved_usd"] <= ledger.data["cap_usd"]
            ):
                raise ValueError("Carried reservation changed or is not unresolved")
            self.pending.add(index)
