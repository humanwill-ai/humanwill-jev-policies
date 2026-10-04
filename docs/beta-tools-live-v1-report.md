# Beta tool/MCP engineering measurement — 2026-10-04

At frozen source `81f0629`, actual LiteLLM **1.102.1** on macOS x86_64 used the
installed `0.2.0b1` wheel, the real policy service and Jev through OpenRouter.
All **48 guarded observations** behaved as expected: **24 allow, 24 block**, no
abstentions or wrong decisions. All 48 matching unguarded observations succeeded.
Denied MCP calls produced **no recorded tool execution**; allowed calls executed
with exactly the inspected arguments. Denied proposals were withheld from the
client. These are repeated engineering fixtures, not 48 independent accuracy cases.

See the [frozen protocol](../evals/step6/beta-tools-v1/protocol.json),
[synthetic workload](../evals/step6/beta-tools-v1/workload.json),
[policy](../evals/step6/beta-tools-v1/policies/upload.md),
[configuration](../evals/step6/beta-tools-v1/config.yaml) and
[sanitized results/hashes](evidence/beta-tools-live-v1.json).

## Timing

Serial requests, 12 repetitions per label/path/arm. First requests are retained.
The coding-model response is synthetic; the MCP tool records arguments locally
without uploading anything. One simple, content-only company policy applies at
`tool_action` only. Prompt/response normalization still runs but has no applicable
policy in this measurement. Adding policies at those stages can add evaluator calls.

| Inspected path | Outcome | Guarded median | Guarded p95 |
| --- | --- | ---: | ---: |
| Non-streaming tool proposal | Allow | 450 ms | 1,560 ms |
| Non-streaming tool proposal | Block | 458 ms | 476 ms |
| Actual MCP invocation | Allow | 507 ms | 578 ms |
| Actual MCP invocation | Block | 477 ms | 506 ms |

Unguarded medians were about 12 ms for proposals and 32 ms for MCP. Paired-by-input
added timings are retained in the JSON. Arms ran sequentially rather than being
randomized/interleaved. The first proposal took 992 ms unguarded and 1,560 ms
guarded; neither was discarded. With only 12 observations and this percentile
method, each p95 is the observed maximum. These are useful engineering measurements,
not stable production tail estimates or an SLA. Whole IDE/agent scheduling,
remote MCP networking, coding-model generation and Agentgateway live latency are
not measured here.

## Accounting and validation

48 physical Jev calls, all charges settled, total **$0.001688400**. Cumulative
known spend is **$0.794541350**, plus the unchanged historical **$0.01** reservation
for entry1830; accounted total **$0.804541350**, remaining **$4.195458650** of the
authorized $5. Ledger: 9,121 attempted, 9,120 settled, one historical unknown.
No retries or new unknown charges. No private workflow content was sent.

Before live execution a scripted provider rehearsal exercised all 96 observations.
An earlier rehearsal used the explicitly simulated backend, whose contract never
requests enforcement; the fixture was corrected to emulate the provider transport
before any live calls. Both local reports are preserved. No runtime enforcement
logic, policy thresholds or production defaults were changed by this measurement.

Raw exchanges and host logs stay in ignored `artifacts/beta-v020/live-tools-v1`.
The dedicated host workflows separately exercise timeouts, missing metadata,
malformed payloads, monitor mode and fail-closed enforcement. This two-label live
sample does not replace those checks or independent semantic qualification.
