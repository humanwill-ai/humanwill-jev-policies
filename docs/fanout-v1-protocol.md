# Multi-question fan-out experiment — frozen protocol

2026-10-01. Owner authorized an isolated experiment and a refactor only if extremely
successful; otherwise retain the current approach for publication. Publication
itself remains a separate owner approval. No runtime edits or GitHub Actions.

Compare the current actual `q05_stage_aware` evaluator against a research wrapper
that sends Q05+Q04 for non-tool stages and Q05+Q04+tool wording for tool_action.
Only normalized stage selects questions. No tool classifier, policy omission,
case-ID routing, threshold changes, prompt enrichment or repeated selected retries.
The actual company rules, trusted conditions and Q05/Q04/tool templates are unchanged.

Every question variant uses a distinct wire ID, retaining its complete policy text.
The expanded request must fit existing16question/24,000byte limits. Validate the
whole expanded reply strictly, including otherwise unused alternatives; one
malformed answer invalidates that batch. The normal evaluator consumes Q05 first
and preserves every accepted primary result. On its ordinary eligible continuation,
consume cached alternatives without another physical call. A threshold-qualified
alternative contradicting Q05 (including qualified insufficient_evidence) vetoes
replacement. Otherwise use a qualifying agreeing tool answer before Q04 on tools,
or Q04 on other stages. No qualifying alternative retains the primary error.
Existing eligibility, unique-maximum, same-choice, metadata, deadline and fallback
rules still apply. Semantic rules are not expanded. No independent-vote claim.

Use all170active reviewed cases plus18new synthetic cases with provisional labels
frozen before measurement; new labels are not owner approval or independent holdout.
Fresh cases have empty research context,9allow/6block/3missing-trusted-fact outcomes,
and cover tool/prompt/model-request/response stages. Preserve reviewed cases' prior
neutral context identically across arms. Removed historical cases are not restored.

Two fresh paired passes, both arms for every case, seeded random case/arm ordering.
752event views. Each arm has its own actual primary call: batching can affect Q05,
so never assume or substitute the other arm's primary answer. Deterministic cases
make no model call. Max1128physical calls; additional spend ceiling$0.35 within the
existing$5 cap, with the same$0.01 oldreservation1830. Stop on new unknown charges,
changed ledger, call limit or budget ceiling. No automatic extra campaign.

## Predeclared exceptional-success gate

Every condition must hold before considering a runtime refactor:

1. Zero wrong definitive event or individual-policy decisions in the candidate,
   including expected-unknown cases. No increase over control in fail-closed false
   blocks or fail-open missed violations, in either cohort/pass.
2. At least50% fewer unexpected event abstentions overall, with net recovery on
   at least three distinct reviewed cases, and no correct control event regressing
   to error or a wrong decision. Benefit must appear in both repeats. If the control
   has too few errors to demonstrate this, the result is inconclusive, not success.
3. At least25% reduction in paired-subset p95 evaluator latency for cases where
   sequential control actually invokes a follow-up (at least10observations across
   at least3distinct cases); no more than10% overall evaluator-p95 increase.
4. Candidate evaluator API cost at most$1 per1,000events and at most2x control cost.
   All charges settled except the unchanged historical reservation. No payload or
   question-limit failures; the complete experiment and offline audit must pass.

These are a deliberately demanding engineering screen, not statistical enterprise
qualification. Fresh labels remain provisional and would need human review before
supporting promotion. If any gate fails or is inconclusive, do not refactor or
retune: preserve the current runtime and finish reporting for the preview.

Record physical calls/cost separately from the evaluator's cached continuation
view. The first view carries full paid batch usage, cached continuation zero cost.
Record per-policy/event outcomes, primary/secondary dispositions, malformed batches,
false-block/missed-violation fallback effects, and evaluator p50/p95/p99. Timings
include request construction/validation but exclude host/IDE/downstream generation;
do not label them real-gateway latency. Repeated tuned cases and provisional fresh
labels are not independent correctness evidence. Save exact synthetic exchanges
locally, freeze all inputs/source before live, and audit with no additional APIcalls.
