# Policy isolation experiment — 2026-09-29

The owner authorized comparing an identical Q05 retry with isolated-policy
assessment, without an extra content-classification question. This is a research
runner; core, connectors, policies, labels, metadata, thresholds and defaults stay
unchanged. Company rules remain complete; no relevance ranking discards a policy.

## Frozen design

Three fresh passes over all 175 reviewed cases. Each pass makes the usual 148
primary model calls and resolves 27 events deterministically. Each event's fresh
Q05 result is the shared control for three alternative live continuations:

| Arm | Follow-up request |
| --- | --- |
| repeat_q05 | Exact primary payload, including all its policy questions |
| isolate_q05 | One unresolved policy per call, exact Q05 question |
| isolate_q04 | One unresolved policy per call, previously frozen Q04 task/criteria |

Q04 task: "Does this policy require an authorization check for the action actually
proposed?" Choices retain their existing meanings and full company policy text;
actual authorization remains a deterministic check. Compared with Q05, Q04 changes
only task and criteria; both share boundary and trusted-field explanation.

All arms retain model, complete state, available context, policy text/versions,
trusted-field names and AP .80 / NA .70 / IE .80 gates. The first two arms isolate
the effect of removing other policy questions; the third tests alternate wording
after isolation. Single-policy first calls are useful identical-input controls
for the first two arms, not evidence of reduced context.

## General runtime routing, without gold labels

- Follow up only when the combined result is evaluation_error and a policy has
  reason low_confidence with tentative applicable/not_applicable. No case ID,
  command, expected label or domain-specific content rule selects follow-ups.
- Accepted results remain accepted. If any established violation already blocks
  the event, do not delay it to refine another policy; retain those errors in audit.
- Do not retry raw insufficient_evidence, missing metadata, malformed first
  responses or other technical errors in this experiment. A separate malformed
  recovery experiment would confound this question-isolation comparison.
- Validate the entire follow-up response. Replace only eligible policy answers,
  only when the choice agrees with the original tentative choice and meets the
  unchanged gate. Contradiction, uncertainty, low confidence or malformed output
  leave that policy's original inconclusive assessment intact.
- Recompose using the real evaluator and the same trusted evidence, preserving
  block-over-error-over-allow precedence and metadata checks. Do not invent a
  compliance result or treat a policy's scope as authorization.
- Each policy gets at most one follow-up. Maximum two follow-up calls per arm/event
  (this frozen pack has at most two model policy questions). Budget/deadline limits
  leave unprocessed policies inconclusive; they are not dropped.

Arms are measured sequentially in a fixed shuffled order (seed 20260930) within
each case. They share one actual fresh primary response. Each arm has the same
remaining 15-second total budget after subtracting primary evaluation time; time
spent measuring another experimental arm is excluded. Deadlines wrap follow-up
transport calls. Report primary-plus-continuation timing, not end-to-end host latency.

## Evidence, cost and stopping

Physical exchanges record exact requests/responses, arm/pass/case identifiers and
latency. Reconstructed result batch usage refers only to the shared primary; compute
actual experiment cost and hypothetical per-arm cost from the physical exchanges,
counting a primary once per deployed arm. Preserve rejected and accepted attempts.

Full reporting includes each pass/arm's abstention, expected vs unexpected errors,
wrong definitive event and policy outcomes, recovered cases and regressions,
agreement conflicts, malformed responses, call/token overhead, latency and cost.
Report single- and multi-policy initial batches separately. Include policy errors
masked by an overall block. No selective reruns or post-result changes.

Promising means improvement in all three passes without new wrong accepted event
or policy outcomes and with expected unknowns preserved. The aspirational target
is at most 8 unexpected errors per 163 decidable events in each pass, with measured
p95 evaluation overhead within 2 seconds and API cost within $1/1000 events. This
does not establish independent holdout accuracy or fulfill statistical release gates.

Use the existing $5 cumulative authorization, reserving the exact historical unknown
at index 1830 in full. Additional experiment ceiling: $0.50, charged at reservation
before each call. Stop on a new unknown charge, model/transport accounting failure
or the ceiling; preserve partial results and do not retry around the accounting
guard. Expected primary calls: 444; follow-up count is determined by runtime results.

Frozen protocol: `evals/step6/policy-isolation-v1/protocol.json`. Outputs remain local
under `artifacts/quality/policy-isolation-v1/`. Commit clean before live execution.
No public push, deployment, threshold tuning, automatic policy rewriting or new
classification question. After this experiment, report results and discuss the
next step; do not automatically continue into policy changes or another campaign.
