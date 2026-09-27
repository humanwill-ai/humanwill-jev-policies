# Live gateway and hook latency — 2026-09-27

**The measured workloads meet the p95 added-latency target of two seconds.**
This is synthetic performance evidence for a real LiteLLM process and actual
hook executables on this Mac, not a production-capacity guarantee or measurement
inside the VS Code UI. The separate accuracy holdout remains pending new labels.

Protocol: [frozen workload](release-latency-protocol.md). Source commit
`5372229`, clean at run start, unchanged policy bundle/configuration, Jev
`typesafe/jev-1.13` through OpenRouter, accepted return
`typesafe/jev-1.13-20260917`. Raw private artifacts:
`artifacts/quality/release-latency-live-v1/report.json` and gateway logs.

## Observations

| Surface | Concurrency | Samples | Total p50 | Total p95 | Total p99 | Paired added p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LiteLLM without policy checks | 1 | 24 | 10.68 ms | 12.81 ms | 17.72 ms | — |
| LiteLLM without policy checks | 4 | 48 | 31.96 ms | 36.08 ms | 37.05 ms | — |
| LiteLLM with request/response checks | 1 | 24 | 364.36 ms | 460.17 ms | 516.35 ms | **450.12 ms** |
| LiteLLM with request/response checks | 4 | 48 | 389.53 ms | 522.54 ms | 1774.89 ms | **492.63 ms** |
| Local prompt hook executable | 1 | 24 | 771.16 ms | **850.54 ms** | 873.76 ms | entire hook duration |
| Local prompt hook executable | 4 | 24 | 829.33 ms | **913.60 ms** | 1032.42 ms | entire hook duration |
| CLI pre-tool hook executable | 1 | 24 | 776.51 ms | **864.88 ms** | 890.68 ms | entire hook duration |
| CLI pre-tool hook executable | 4 | 24 | 821.87 ms | **927.37 ms** | 1038.04 ms | entire hook duration |

Added gateway duration is the difference between matching input-index request
durations in the adjacent baseline and guarded arm, then the percentile of those
differences. It is not subtraction of percentiles. Arms ran sequentially; network
and process variability limit causal precision. The controlled downstream model
returns locally without an external generation call.

First requests were kept separate: baseline 1038.95 ms, guarded 1463.86 ms,
difference 424.91 ms. There is only one cold observation per arm, not a cold-start
latency distribution. Every hook invocation starts a fresh Python process.

Inputs cycled through 128, 4,096 and 12,000 characters. Guarded per-size p95s:

| Surface / concurrency | 128 chars | 4,096 chars | 12,000 chars |
| --- | ---: | ---: | ---: |
| LiteLLM / 1 | 460.17 ms | 516.35 ms | 410.10 ms |
| LiteLLM / 4 | 565.96 ms | 522.54 ms | 1774.89 ms |
| Local hook / 1 | 873.76 ms | 850.54 ms | 811.38 ms |
| Local hook / 4 | 894.59 ms | 1032.42 ms | 913.60 ms |
| CLI hook / 1 | 821.83 ms | 864.88 ms | 890.68 ms |
| CLI hook / 4 | 836.63 ms | 1038.04 ms | 927.37 ms |

Per-size samples are small (8 at serial/hook workloads, 16 at concurrent gateway
workload); the nearest-rank p95 can equal the maximum. Retain the 1774.89 ms tail
rather than smoothing it away.

## Errors, coverage and cost

- All 146 gateway requests returned HTTP 200 (73 baseline, 73 guarded); all 96
  hook processes exited zero and emitted the ordinary allow object `{}`.
- The service recorded 242 actual assessments: 146 gateway input/output events
  plus 96 hook events. All allowed, with no evaluation errors or overloads. This
  workload tests the approved coding-assistance path; it is not an accuracy test.
- There were 169 live Jev calls, with observed provider concurrency reaching four.
  All returned the accepted model and reported reconciled charges. There were no
  retries, fallbacks, caching, unknown charges or abandoned reservations.
- API spend: **$0.012446784** for this run. Cumulative ledger total:
  **$0.065024282 / $5**, leaving **$4.934975718**. At 169 guarded workflows, this
  workload's evaluator cost is about **$0.07365 per 1,000 workflows**. It excludes
  host operations, infrastructure and metadata-provider costs.
- All three policy bindings stayed in monitor mode. Verified approved response
  delivery short-circuited software response evaluation; the document policy used
  public classification. Hook tool actions included the production-action scope
  check. Metadata was supplied by the synthetic trusted resolver, not the caller.

## Limits and remaining work

The hook numbers include interpreter startup, HTTP, service and live evaluator,
but not IDE scheduling or a full Copilot CLI chat session. Agentgateway's live
latency and actual VS Code scheduling were not measured here; existing pinned-host
enforcement evidence remains separate. The measurement deadlines exceeded the
shipped hook deadline to expose long responses; see the protocol. No timeout
bypass is concealed by this successful latency run.

Inputs are padded synthetic coding context, not a representative customer traffic
sample. Response approval avoids a second semantic call on the gateway path;
other company policies and metadata services may add calls and latency. Capacity
beyond concurrency four, geographically remote deployment and sustained load need
separate validation. Controlled overload, timeout and restart behavior is covered
by the [offline service operation checks](service-operation-gates.md), not by
intentionally creating unpriced live failures.

For this declared preview workload, the latency target is met. The overall
semantic release gate is still open. The [new 100-case label packet](holdout-v1-label-review.md)
is ready; its new labels require review before measurement. The prior 36-case
owner approval remains complete and unchanged. Even a perfect result in this
initial targeted tranche cannot establish the approved 5% error upper bounds;
a larger independent sample is required for that claim.
