# Multi-question experiment — retain the current approach

2026-10-01. **Do not adopt the candidate or refactor the runtime.** Sending Q05,
Q04 and (on tool-action events) tool-specific wording together failed the
predeclared exceptional-success gates. The existing sequential, stage-aware
follow-up remains the selected development profile for the experimental preview.

The experiment was frozen at `fcd9c2b4df0a437ccda09a590be1bc10cb6495f5`.
See the [protocol](fanout-v1-protocol.md) and
[sanitized results](../evals/step6/fanout-v1/results-summary.json).
Each approach evaluated 188 distinct cases twice: the 170 active reviewed cases
and 18 new synthetic cases with provisional labels. That is 376 observations per
approach, 752 altogether, using 645 physical API calls. The new labels are not
owner-approved or independent holdout evidence.

## Results

| Measurement | Current sequential approach | Questions together |
| --- | ---: | ---: |
| Unexpected abstentions, among 346 decidable observations | 1 (0.29%) | 4 (1.16%) |
| Expected abstentions preserved | 30/30 | 30/30 |
| Wrong definitive combined decisions | 0 | 0 |
| Individual-policy disagreements against provisional fresh labels | 1 | 2 |
| Median evaluator latency | 356 ms | 375 ms |
| p95 evaluator latency | 518 ms | 498 ms |
| p99 evaluator latency | 788 ms | 1,134 ms |
| Physical API calls | 329 | 316 |
| API cost | $0.020540 | $0.045393 |

There were **no paired event recoveries and three regressions**. The reviewed
cohort alone had one unexpected error in the control versus three in the
candidate; the provisional fresh cohort had zero versus one. All definitive
combined decisions matched expected outcomes, but this does not mean every
individual policy judgment was correct.

On the 13 paired observations (seven distinct cases) where the control actually
used a follow-up, batching reduced median latency from 740 to 384 ms. However,
p95 rose from 853 to 2,539 ms because of a slow observation. This small subset
does not establish a reliable tail-latency improvement. Overall p95 improved
only about 4%, while cost increased to 2.21 times control. Timings cover the
evaluator, including deterministic cases, not gateway or whole-IDE execution.

## What failed

| Case / pass (one-based) | Expected | Current result | Candidate result |
| --- | --- | --- | --- |
| `sources-v1-response-warning` / 1 | Allow | Allow | Low-confidence error |
| `fanout-fresh-tool-write-tests` / 2 | Allow | Allow | Malformed-response error |
| `sources-v1-fetch-unapproved` / 2 | Block | Block | Malformed-response error |

Both approaches also returned a malformed-response error on
`holdout-v1-sw-rclone-source` in the first pass. This was a shared failure, not
a candidate regression. Across the experiment, one control batch and four
candidate batches failed strict validation because probabilities summed to 0.99.
One candidate malformed batch concerned an expected-uncertain case, so it did
not create an additional event mismatch.

The candidate validates the entire expanded response as declared before the
run. Consequently, an otherwise unused Q04 answer with malformed probabilities
invalidated the local-test-writing batch. Additional answers create additional
validation failure opportunities under this contract. We did not relax the
validator, normalize probabilities or retry failures after observing results.
The warning case instead lacked a qualifying agreeing alternative. Each arm
received fresh primary answers; sampling variation and batching effects cannot
be separated by these observations alone.

The provisional response-install-helper case correctly blocked acquisition from
an unapproved source, but also incorrectly triggered the disclosure policy:
twice in the candidate and once in the control. The correct source block masked
that policy disagreement in the combined outcome. Preserve this diagnostic;
do not describe the experiment as having zero individual-policy errors.

If errors were configured to block, legitimate requests stopped would increase
from 0/170 to 2/170 observations. If errors were configured to allow, known
violations permitted would increase from 1/176 to 2/176, plus all 30 expected
uncertain observations in either approach. These are fallback consequences for
this constructed pack, not observed host enforcement or production prevalence.

## Decision and verification

The candidate failed the quality, recovery, follow-up p95 and relative-cost
gates. It passed request-limit checks and stayed below $1 per 1,000 evaluations,
but all gates were required. There is insufficient benefit to justify a runtime
refactor. This rejects this specific experiment; it does not prove all forms of
batched questioning are ineffective.

Six focused offline tests passed before the live run, including scripted
composition and payload checks across all 188 cases in both arms. Afterwards,
all 752 normalized event results and all 645 exact provider payloads were
replayed and audited offline. Frozen inputs and the spending ledger were
verified. Raw synthetic exchanges and the replay audit remain local under
`artifacts/quality/fanout-v1/`; the linked sanitized summary is retained in Git.

The experiment cost **$0.065933154**, with no new unknown charges. Cumulative
known spend is $0.424300010 plus the unchanged historical $0.01 reservation:
$0.434300010 accounted, **$4.565699990 remaining**. The ledger contains 6,254
attempts, 6,253 settled, and only the previously authorized unknown entry 1830.

Runtime code, policies, thresholds and defaults remain unchanged. No further
campaign, GitHub Actions run, push, deployment or publication was performed.
Continue public-preview preparation with the current approach; independent
qualification and concrete publication approval remain separate.
