# Live runtime latency protocol

Frozen before live calls, 2026-09-27. Jev through OpenRouter only, synthetic
content, existing cumulative $5 budget and ledger. Starting recorded spend:
$0.052577498. No policy, rubric, model allowlist or threshold changes.

Use all three current policy bindings in monitor mode. A synthetic deployment
resolver binds approved coding-route facts, public document classification,
and no destructive-action permission to each exact event. Responses return to
the approved coding session, so software response predicates can short-circuit.
No request metadata or user claim establishes these facts. This authority models
a deployment integration; it does not implement a production directory/resolver.

## Workload fixed before measurement

- Real LiteLLM 1.102.1 process, first without guardrails, then with the shipped
  request and response adapters calling the real service and live Jev. Both use
  the same controlled local downstream chat server to isolate policy delay.
- Each arm: one first request, 24 warm serial requests, 48 requests at concurrency
  four. Input lengths cycle through 128, 4,096 and 12,000 characters. New gateway
  process per arm; retain first-request timings separately.
- Actual Python hook subprocesses for Local `UserPromptSubmit` and CLI
  `preToolUse`: 24 at concurrency one and 24 at concurrency four per profile.
  Include interpreter startup, HTTP, service and evaluator; exclude actual IDE
  scheduling and Copilot CLI session startup. Do not describe these as whole-IDE
  or whole-CLI chat timings.
- Hook HTTP deadline 20 seconds and service deadline 18 seconds, exceeding the
  unchanged evaluator's 15-second development deadline. These are measurement
  settings, not the shipped 15-second host hook profile. Report >2-second samples
  as latency failures; do not hide them through a shorter timeout.
- No decision cache, provider retry or fallback. The production transport opens
  a fresh provider connection per call. Record provider concurrency and every
  billed call, including errors; halt new calls on unknown billing.
- Separate errors/overload from valid assessments. Do not claim low latency from
  requests rejected before evaluation. Existing offline failure exercises cover
  controlled overload/timeouts; do not send intentionally failing paid requests
  with unreconcilable costs merely to duplicate those checks.

Report p50/p95/p99 by surface, concurrency and input size. For LiteLLM, compare
matched request durations with the adjacent unguarded baseline; report both
absolute guarded duration and the paired difference. No shared downstream model
latency is attributed to Jev. Include first requests and hook startup separately.
The approved target is p95 added latency <=2 seconds. Synthetic results describe
this host and workload only, not customer production capacity, all gateway
versions, or latency inside the VS Code UI.

Current endpoint metadata was checked before calls: Jev input $0.042 per million
tokens, output $0, returned model `typesafe/jev-1.13-20260917`.
[OpenRouter endpoint metadata](https://openrouter.ai/api/v1/models/typesafe/jev-1.13/endpoints).

The offline dress rehearsal completed 242 assessments, all allowed; no API calls
were made. It verifies the harness, not live latency. The concurrent-accounting
unit tests cover reservations, settlement, unknown charges, failure stop and cap
enforcement. Each process holds the original ledger lock for its entire run.
