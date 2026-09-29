# Bounded policy follow-up

The runtime can use the measured Q05 scope question followed by **one Q04 call**
when the initial assessment abstains on a low-confidence scope answer. It operates
on the request and configured policies at runtime, without test labels, policy-ID
rules, an extra content classifier, or a tool detector.

## Enable or disable

In a `humanwill.config/5` configuration, set:

```yaml
policy_assessment: q05_q04
outcome_thresholds:
  applicable: 0.8
  not_applicable: 0.7
  insufficient_evidence: 0.8
```

The profile does not change thresholds; these are the values used in the development
comparison. `policy_assessment: q05` retains Q05 with no follow-up. `standard` or
omitting the setting preserves the original template and single-assessment behavior.
Older configuration formats reject the setting. The configuration digest captures
this choice. `preview` displays primary and potential follow-up questions.

`init-demo` includes `config-policy-followup.yaml` with the profile selected and
metadata-dependent rules still disabled. It is a starter, not an approved enforcement
configuration. Enable your own policy bindings and trusted metadata sources as needed.
Metadata remains optional; content-only policies continue to work with it disabled.

Only `scoped_predicates` questions use Q05/Q04. These ask whether an operation needs
the policy's trusted checks; they do not establish authorization. `semantic` rules
retain their compliant/violation questions and are not eligible for this scope
follow-up. Deterministic policies remain deterministic. A mixed batch retains all
its original questions; only scope wording changes in the second request.

## Runtime contract

The follow-up runs only after all primary batches succeeded validation, when the
combined decision would be `evaluation_error` and at least one scope policy has
reason `low_confidence` with raw choice `applicable` or `not_applicable`.

It does not retry malformed primary answers, transport failures, explicit
`insufficient_evidence`, missing-metadata errors, accepted outcomes, or errors
masked by another policy's violation. It sends the full original question batch
containing the first eligible policy, with Q04 scope wording. Policy bodies, event
content, coverage, stage and declared trusted fields are unchanged. Approval facts
remain in deterministic code. No synthetic fixture context is added to real events.

Accept a secondary answer only when it:

- passes the same strict model, answer-ID, probability and response validation;
- agrees with the original scope choice;
- meets that outcome's configured confidence threshold and has a unique maximum.

Only eligible answers can replace their primary answers. Already accepted answers
stay unchanged even if the second response disagrees. Trusted predicates and final
evidence freshness still apply. A successful scope assessment can therefore still
end in a metadata error or a violation.

There is at most **one extra provider call per event**, under the same semaphore,
original total deadline, request/response byte limits and `max_batches` call budget.
If primary evaluation required several batches, only the first eligible original
batch is revisited; other eligible policies remain unresolved (`call_limit`). If
there is no time or call/byte budget left, retain the primary result. No background
work or transport retries are launched. Cancellation propagates.

A malformed, failed, conflicting, indeterminate or still-low-confidence follow-up
preserves the affected primary error. Policy `on_error: block` or `allow`, monitor
mode and connector enforcement limitations continue to govern the outcome.

## Results and accounting

For `q05` and `q05_q04`, result/4 includes `policy_assessment`:

- profile, status, eligible and accepted policy IDs;
- rejected/deferred policy IDs and reasons;
- normalized primary and secondary scope answers for the eligible batch;
- the follow-up's index in `evaluation.batches` and a sanitized error code, if any.

`evaluation.batches` contains **both physical attempts**, with separate model,
tokens and API cost. Valid usage can be retained when a follow-up answer is
malformed. A failed or timed-out attempt with no validated usage has null cost;
null means unknown, never zero. Do not calculate total cost from only the last
batch. The old research recomposition's primary-only usage limitation does not
apply to this runtime implementation.

The audit fields contain no raw prompt or policy text. Existing minimal-content
service logging is unchanged. Use matching updated service and hook/client builds:
older strict result/4 validators may reject the new optional field. Omitting the
profile keeps the old result shape.

## Validation and limits

The preceding [live comparison](q04-comparison-v1-report.md) found 5.9% unexpected
abstention for full-batch Q04 versus 9.2% for Q05 alone on the repeated reviewed pack.
It did not consistently achieve 5%, establish production prevalence, or qualify
arbitrary customer policies. The fresh workflow labels remain provisional.

Implementation checks use scripted provider replies and offline replay of the
recorded campaign. The live experiment supplied synthetic neutral tool/resource
context; production connectors provide only their documented coverage. Identical
question wording does not guarantee identical production accuracy or latency.
Supported connector wire paths use the same evaluator; this change does not add
interception stages, trusted source resolution, or CLI prompt blocking. No new
interactive VS Code/Copilot or real gateway-host acceptance run is implied.
