# Controlled gateway latency paths — frozen protocol

2026-10-01. Owner authorized a small live comparison following review of the
500 ms early result versus the later 1.8 s p95 workload. Synthetic content only,
Jev through OpenRouter, existing $5 cumulative authorization. No CI or deployment.

Use the current four policies, `q05_stage_aware`, gates 0.80/0.70/0.80, monitoring
and the same synthetic trusted resolver as preview-latency-v1. No policy, question,
threshold, runtime, resolver or request enrichment changes. Real LiteLLM 1.102.1
calls the actual adapter/service and live Jev; local downstream generation is
scripted to isolate added evaluation delay.

Three fixed workloads in `evals/step6/latency-paths-v1/workloads.json`: meaningful
local code review, meaningful warning against an unapproved download (a previously
intermittent uncertainty example), and the historical opaque placeholder as a
separately reported diagnostic. The latter is not a realistic response or evidence
of ordinary traffic latency. No semantic labels are supplied to the model.

For each workload run baseline (no guardrail), prompt-only (pre_call), and prompt
plus response (pre_call/post_call) arms. Rotate arm order across workloads as
specified in the workload file. Each arm has one initial request reported separately
and 12 warm serial requests, cycling 128/4096/12000 characters. There are 117 gateway
requests, 117 guarded stage assessments, and at most 234 provider calls (each
assessment permits at most one follow-up). Reserve ceiling $2.34 within the $4.644719882
remaining authorization, not an additional budget. Offline dress rehearsal uses
two requests per arm and a scripted backend, never the production ledger.

Record actual provider call count, per-stage result/follow-up disposition and time
for every gateway request. Do not force a low-confidence result, change thresholds,
retry a selected example, or claim a follow-up occurred when it did not. If no
meaningful response triggers one, state that limit and report the placeholder path
separately. No further automatic campaign to obtain desired behavior.

Compute added latency by subtracting the matching-index baseline request for each
workload before calculating percentiles. Include every completed request and error;
report outcome and call-count groups separately. Do not subtract percentiles.
Small samples make p95/p99 coarse; serial-only results do not establish capacity.
Arms are sequential, not randomized simultaneous trials; provider/time variation
limits causal attribution. Baseline and guarded responses must have identical
content within each workload. No full IDE/CLI or Agentgateway timings are measured.

Freeze source/configuration/workload hashes and the starting ledger. Hold its lock
throughout; retain the exact authorized historical entry1830 reservation of $0.01
and its null cost. Stop on any new unknown charge or changed ledger. Persist partial
results; never count an HTTP200 in monitoring as successful policy enforcement.
Preserve all earlier protocols and results unchanged. Commit locally before live
calls; no CI-triggering push. Retain raw synthetic exchanges under ignored artifacts,
then publish only a sanitized summary/report with actual charges and limitations.
