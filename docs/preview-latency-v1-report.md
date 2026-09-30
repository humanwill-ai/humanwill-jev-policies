# Preview profile end-to-end latency confirmation

2026-09-30 · frozen source `6450402` · runtime `0.1.0a1` ·
[protocol](preview-latency-v1-protocol.md)

The selected `q05_stage_aware` profile was exercised through real LiteLLM 1.102.1
and the real Local/CLI hook executables, with live OpenRouter Jev and synthetic
content. All four final policies were configured in monitoring mode. No research
context sidecar was supplied. The downstream generation endpoint was a local mock.

## Timings

Nearest-rank percentiles; small samples make tail estimates coarse. LiteLLM figures
below subtract the matched-index baseline duration, not one percentile from another.
Baseline and guarded groups ran separately, so temporal/provider variation remains.

| Workload | Requests | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: |
| LiteLLM added delay, serial | 12 | 1,080 ms | 1,800 ms | 1,800 ms |
| LiteLLM added delay, concurrency 4 | 24 | 1,329 ms | 1,749 ms | 2,904 ms |
| Local hook executable, serial | 12 | 793 ms | 980 ms | 980 ms |
| Local hook executable, concurrency 4 | 12 | 886 ms | 975 ms | 975 ms |
| CLI hook executable, serial | 12 | 817 ms | 898 ms | 898 ms |
| CLI hook executable, concurrency 4 | 12 | 896 ms | 979 ms | 979 ms |

Gateway timing includes request and response policy checks. Hook timing includes
Python startup, HTTP and evaluation, excluding IDE/CLI host scheduling. Inputs are
128, 4,096 and 12,000 characters. The single initial gateway request took 2,209 ms
with guards versus 1,065 ms baseline; report it separately from warm samples.
Peak provider concurrency was four. This is not capacity certification, Agentgateway
live-provider latency, or evidence that every request meets a two-second deadline.

## Outcomes: monitoring success is not policy success

All 74 gateway requests (baseline plus guarded) returned HTTP 200; all 48 hook
executions exited successfully. **Of 122 guarded assessments, 85 allowed and 37
returned `evaluation_error`.** The 37 errors are every guarded response; the fixture
returns the same opaque text, `SYNTHETIC_ALLOWED_RESPONSE`, without meaningful
response content or conversation context.

Both disclosure and source scope had low-confidence errors for those responses.
Each triggered a bounded follow-up and remained an error. Monitoring allowed their
HTTP delivery; an enforcing fail-closed deployment would withhold those 37 replies.
The marker's name is not authorization or proof that it contains adequate context.
This workload was not a human-labeled semantic benchmark, so these are reported as
observed errors, not retrospectively relabeled passing accuracy cases.

All 37 guarded input assessments and all 48 hook assessments allowed. The latency
result therefore includes 37 unresolved follow-ups and is not merely a primary-only
best case. The response uncertainty is a concrete reminder that the reviewed pack's
0.21% unexpected abstention rate is not a production-wide estimate. Before enabling
response enforcement, validate representative real response content, available
context and the company's chosen fallback.

## Accounting and limits

159 physical calls, all charges settled, costing **$0.014862204**. Total accounted
project spending is **$0.355280118**, including the preserved historical $0.01
reservation; **$4.644719882** remains under the original $5 authorization. No new
unknown charges or accounting stop. Cost excludes infrastructure and downstream
model generation, which was mocked.

The workload uses a test-owned trusted resolver; it does not establish production
identity, source or destination verification. Fullpack accuracy and connector
protocol/enforcement tests are separate evidence. See [the pack report](preview-final-v1-report.md)
and [candidate verification](preview-verification.md). Raw results remain local in
`artifacts/quality/preview-latency-v1/report.json`.
