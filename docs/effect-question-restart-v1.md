# Owner-requested restart — 2026-09-29

The owner requested restarting the interrupted test after the timeout and unknown
charge were reported. Run the same two conditions from the beginning: 175 events
per condition, 296 planned provider calls, no within-run retries. Preserve the
original partial run and compare separately; do not replace its failures.

All questions, policies, contexts, labels, thresholds, provider, 15-second evaluation
deadline and case/condition order are unchanged. The prior early regressions remain
evidence against promoting this experimental wording. This restart measures the
full comparison; it does not deploy the candidate or close a release gate.

The new instruction authorizes proceeding with the exact old unresolved ledger
entry1830 fully reserved at $0.01. Its `cost_usd` remains null in memory and on disk.
This is explicitly a carried reservation, not a reconciled or zero-cost call.
Starting known cumulative spend is $0.110940572; accounted amount including the
reservation is $0.120940572, leaving $4.879059428 unreserved under the $5 cap.

`restart_accounting.py` is an opt-in research subclass of the existing meter. It
accepts only explicitly listed, digest-bound old entries and retains the parent's
full-reservation budget accounting. Default metering is unchanged; any new unknown
charge or changed entry stops execution. Both conditions share the locked existing
ledger. Five offline accounting tests cover preservation, exact-entry binding,
budget depletion, default rejection and stopping after a new failure. All three
existing effect-question payload/composition tests also pass.

`effect-question-restart-v1/protocol.json` freezes the original protocol, restart
code, old artifact hashes and exact starting ledger. The original nested protocol
guards still check all inputs/evaluator sources. New output:
`artifacts/quality/effect-question-restart-v1/`. No credentials or raw artifacts
are committed; no GitHub push/Actions run is needed.

## Result

Pending the fresh run. The protocol above remains a premeasurement record.
