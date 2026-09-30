# Final preview development-pack protocol

Frozen before measurement, 2026-09-30. This campaign measures the actual
`q05_stage_aware` runtime in candidate `0.1.0a1`, using all 170 cases selected by
`evals/step6/release/active-pack.json`, final `policies-sources-v4`, and the existing
0.80 / 0.70 / 0.80 outcome gates. Three complete serial passes; no tuning,
selective retries, case removal, or answer-driven question selection during the run.

The normal runtime may make its one bounded follow-up. Every physical exchange
and composed result is retained locally. Synthetic event-bound context and trusted
source fixtures are the same as earlier development campaigns; they are research
inputs, not a deployed context/provenance resolver. Case labels never select a
question or enter provider payloads. Each case selects its predefined policy
bindings; this is not a measurement with every company policy enabled on every event.

Report expected unknowns separately from unexpected errors, false blocks and
missed violations under each fallback, individual-policy errors even when masked
by another policy, three-pass variability, evaluator latency and actual API cost.
Repetitions measure stability, not independent sample size. This is a repeatedly
tuned development pack with known failures removed at the owner's request, not
independent holdout validation or enterprise enforcement qualification.

Maximum 1,020 physical calls; additional spending ceiling $0.50 inside the existing
$5 authorization. Retain only the already authorized historical $0.01 reservation
at ledger entry 1830; stop on any new unresolved charge. Freeze current runtime,
runner dependencies, policy/context/catalog inputs and starting ledger hash in
`evals/step6/preview-final-v1/protocol.json`; commit before live calls. Preserve all
previous protocols unchanged.
