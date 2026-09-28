# Context-only live comparison: fixed protocol

2026-09-28 · frozen before measurement; owner authorized the complete rerun

Run all 175 accepted cases once, in the original order, using the exact context
records prepared at `28529c4`. Only `state.assessment_context` changes in the
provider payload. Keep policies, semantic questions, original event content,
labels, evidence predicates, model, 0.80 threshold and monitor mode unchanged.
The original clean `c69ca6f` first-pass results are the comparison baseline.
The seven excluded cases remain excluded. No new Gemini run or threshold tuning.

[Machine-readable protocol](../evals/step6/context-v1/live-protocol.json) pins the
new runner, context snapshot, preserved runner and original local artifact hashes.
Both the original evaluator protocol and context snapshot must still validate.
One sequential pass; no retries, fallback or selective reruns. A failed provider
call or unresolved charge stops the run while retaining partial artifacts.

Report combined event outcomes and all individual policy judgments. Separately
report raw scope choices, correct choices rejected for low confidence, wrong
choices, errors on specified cases, expected unknowns, and every regression or
improvement relative to the baseline. Do not credit another policy's block as a
correct judgment for a failing policy. Report timing and API cost once per event.

This compares one observation per condition, taken at different times. No repeated
control is being added. Differences are associated with the context run, but this
experiment cannot separate their cause from run-to-run model/service variability.
These cases have already been inspected for development and are not an independent
holdout. The source descriptors remain synthetic fixtures, not production resolver
or real host-enforcement evidence.

The existing shared $5 ledger has 1,264 settled step-6 calls and $0.071233898 total
spend before the run, leaving $4.928766102. The same process lock and per-call
reservation remain mandatory. Only synthetic events, questions and their prepared
context are disclosed; reviewer notes, identity and the raw export are excluded.

[OpenRouter endpoint metadata](https://openrouter.ai/api/v1/models/typesafe/jev-1.13/endpoints)
was checked before the run: returned model `typesafe/jev-1.13-20260917`, input
$0.042 per million tokens, output free. Record provider-reported actual charges;
this is not an invoice reconciliation.
