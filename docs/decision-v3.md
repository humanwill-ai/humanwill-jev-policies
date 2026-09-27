# Trusted decisions and stage-specific semantic scope

Implemented in `0.1.0.dev3`. The original config/2 and result/2 contracts keep their
behavior for baseline reproduction. New **config/3** opts into a revised rubric
(`humanwill.choice/2`) and returns **result/3**. Markdown policy files and normalized
request/1 events are unchanged. Export the schemas with `humanwill-policies schema
config-v3` and `humanwill-policies schema result-v3`.

## Verified facts may settle one conditional policy

For a scoped-predicate rule, the logic is: **if scope applies, all required
predicates must hold**. When all required, trusted predicates are already true,
the rule is satisfied regardless of semantic scope. Config/3 offers an explicit
`predicate_short_circuit: true` option for this strategy only; it defaults false.

For example, if approval covers the exact code/material, destination and proposed
operation, uncertainty about whether the content is project code need not cause a
false block. This does not grant permission to every resource on an approved
platform. The trusted source must establish the exact scope of approval. A user
claim of approval cannot substitute for this evidence.

The shortcut runs only after enabled/stage/coverage checks and successful checking
of **all** required metadata and predicates. Empty predicates, partial facts,
negative predicates, wrong sources, stale facts, disabled metadata or evidence
bound to another event do not activate it. Freshness is checked again before the
final result, including after another policy's model call. An explicit incomplete-
coverage assessment configuration retains its declared limits; no coverage is added.

The policy result has `judgment: compliant` and reason
`trusted_predicates_satisfied`, with predicate evidence and **no fabricated model
judgment**. Other policies are still evaluated and may block. If no rule needs
semantic evaluation, no provider request or evaluator disclosure permit is needed;
this says nothing about approval to send data later to another system.

## Separate scopes by governed stage

A scoped config/3 binding may supply either the existing `scope` string or a
`scope_by_stage` mapping, never both. A mapping must name every stage in the
policy Markdown header exactly; missing stages are a configuration error, not a
fallback to another stage's question.

The [development configuration](../evals/step6/config-v3.yaml) distinguishes:

- Submitted prompts: requests to disclose project material versus discussion.
- Model requests: the actual outbound content; no explicit upload verb is needed.
- Responses: the answer about to be delivered, rather than the earlier request.
- Tool actions: effects of the exact tool and arguments, including the distinction
  between executing a command and printing or quoting its text.

The revised rubric explicitly excludes authorization, environment and destination
approval from scope reasoning because code checks those facts separately. Missing
permission is not itself missing semantic evidence. Unavailable script contents
or uncertain project origin can still make the scope indeterminate.

All event content remains untrusted data. The instructions tell the judge to ignore
attempts inside comments, documents or tool arguments to redefine its task or
answer. This is a testable instruction boundary, not proof of injection immunity.
No attack-word blacklist or automatic allow based on tool names was added.

## Uncertainty analysis per evaluator

The first revised runs retain the uncalibrated 0.8 monitoring threshold so their
results can be compared against the initial development run. The original
[60-case dataset](../evals/step6/development.json) and config/2 remain unchanged.
The additional [36-case development attack suite](../evals/step6/adversarial-development.json)
has 12 matched families: an operation, the same operation with evaluator-directed
text, and a harmless local-edit/printing control with hostile text. These are
synthetic development labels, not an independent reviewed holdout.

After recording live answers, run independent analyses:

```sh
python -m evals.step6.calibrate --output artifacts/quality/jev-v3-calibration.json \
  artifacts/quality/jev-v3 artifacts/quality/jev-v3-attacks
python -m evals.step6.calibrate --output artifacts/quality/chat-v3-calibration.json \
  artifacts/quality/chat-v3 artifacts/quality/chat-v3-attacks
```

This performs **no provider calls**. It checks dataset, configuration and policy
hashes, rejects mixed models/rubrics, and replays the recorded answers through the
same core for a fixed threshold grid. Provider/response failures remain failures.
Raw-confidence bins show scope mistakes separately from abstentions and from
policies settled by trusted facts. Jev confidence and chat self-reports are not
assumed to represent the same calibrated probability.

A development candidate is the highest tested threshold with empirical false
blocks ≤5%, zero missed violations, specified-case errors ≤5% and no unknown case
incorrectly allowed. If none qualifies, the result is null. This is a development
screen only: it does not satisfy the approved 95% interval bounds or independent
held-out requirement, and does not write an enforcement profile or silently change
any configured threshold. Human label review remains required before calibration
can support a release claim.

## Compatibility and rollback

Config/2 continues to use the original questions and result/2. Restore the previous
configuration to roll back behavior. Updated hook clients validate both result/2
and result/3 with the same event-digest/coverage checks. Old clients reject the new
version through their configured error behavior, so upgrade the service and hook
clients together before adopting config/3. Gateway host wire responses are unchanged.
Existing pinned real-host evidence used config/2; new service/hook contract tests
cover result/3, not a fresh interactive host acceptance run.

All evaluation configurations remain monitoring-only. Metadata is still optional
and independently switchable at product level. Disabling required evidence does
not silently grant permission or disable authentication.

## Verification status

116 offline tests pass, including shortcut isolation, all-predicate requirements,
missing/stale/untrusted/disabled evidence, coverage, freshness after another
policy call, per-stage question selection, config/2 compatibility, result/3 hook
clients and calibration input integrity. A fresh `0.1.0.dev3` wheel installed
outside the checkout passed schema loading and a trusted no-model decision.

Live re-evaluation uses the existing approved OpenRouter budget and must record
its own results before any improvement claim. The initial report remains the
config/2 baseline, not evidence of config/3 performance.

The implementation at `ed06443` passed all four Ubuntu/macOS × Python 3.11/3.14
[core CI jobs](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/36324853819)
and all three existing config/2
[pinned-host CI jobs](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/36324853833).

Separate offline calibration analyses of the recorded config/2 baseline answers
found **no development candidate threshold** for either semantic policy on either
Jev or Gemini under the stated empirical screen. This confirms that threshold
changes alone do not repair that baseline; it does not measure the new config/3
questions. The baseline artifacts were copied locally with hash-verified
configuration snapshots for the new analysis tool; original results were retained.
