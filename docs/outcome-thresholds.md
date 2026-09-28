# Global outcome thresholds

Implemented 2026-09-28, owner-authorized configuration feature. No live model
evaluation or threshold calibration accompanies this change.

Opt into `humanwill.config/4` to configure one confidence threshold per model
outcome, shared across all policies, stages, transports and connectors. Existing
config/1–3 files retain their previous behavior and hashes. Config/4 keeps the
config/3 scope questions and deterministic logic, and still returns result/3.
There are no per-policy threshold overrides in config/4.

```yaml
format: humanwill.config/4
outcome_thresholds:
  applicable: 0.80
  not_applicable: 0.80
  insufficient_evidence: 0.80
# Existing metadata, policies, provider and connector settings follow.
```

These are compatibility defaults, not calibrated probabilities of correctness.
Omitting the entire section supplies these defaults. If present, all three keys
are required; each must be a finite number from 0 through 1. Unknown keys,
booleans and strings are rejected. Values may differ independently; there is no
required ordering. Settings belong to trusted deployment configuration, never
user prompts or connector request overrides.

For an asymmetric experiment, an operator could change `not_applicable` to
`0.70` while keeping the other two at `0.80`. This is an illustration, not an
approved enforcement profile. The existing evaluation configurations remain
unchanged in monitoring at their original thresholds.

## Meaning and decision flow

| Global setting | Scoped-predicate answer | Content-only semantic answer |
| --- | --- | --- |
| `applicable` | `applicable` | `violation` |
| `not_applicable` | `not_applicable` | `compliant` |
| `insufficient_evidence` | `insufficient_evidence` | `insufficient_evidence` |

The semantic mappings reuse the three global gates; they do not rename or alter
the raw answers. **Applicable does not itself mean a violation.** After accepting
scope applicability, the service uses trusted predicates to decide whether the
operation is authorized. Missing required facts remain an error. Deterministic
policies and already-approved predicate shortcuts require no model confidence.

The gate compares Jev's returned `confidence`, not the winning choice's probability.
Confidence equal to the threshold is accepted. Below threshold, the result is
`evaluation_error`, with policy judgment `insufficient_evidence` and reason
`low_confidence`. Tied winning probabilities remain uncertain regardless of
threshold; malformed responses remain errors.

An accepted explicit `insufficient_evidence` answer also produces an evaluation
error, with reason `model_indeterminate`. Its threshold distinguishes that stated
uncertainty from low confidence; it cannot convert uncertainty into permission.
Results retain the original model choice, confidence and distribution. The
configuration digest identifies the effective thresholds, also visible in
`preview` output; changing any threshold changes that digest.

Failure behavior is separate and unchanged. Monitor mode requests no enforcement.
In enforce mode, `on_error: block` prevents uncertain actions; explicitly choosing
`on_error: allow` requests permission while retaining the error assessment. There
is no new approval workflow. Connector/host timeouts and bypasses retain their
documented behavior.

## Migration and runnable example

1. Change the configuration format to `humanwill.config/4`.
2. Remove every policy's `monitor_min_confidence` and every
   `evaluation_profile.min_confidence`. Config/4 rejects these fields instead of
   silently overriding them. Keep profile ID, model and dataset hash.
3. Choose the three global values. A deployment previously using one value
   everywhere can preserve its gates by setting all three to that value. Mixed
   per-policy thresholds require an explicit global choice; defaulting to 0.8
   does not preserve a previous custom value such as 0.9.
4. Validate and preview the configuration, then test the changed profile in
   monitoring. Semantic enforcement still requires an evaluation profile with
   the matching model; the schema does not establish measured quality.

The packaged demo includes `config-outcomes.yaml` with all three at 0.80 and
monitoring enabled. From an installed package:

```sh
humanwill-policies init-demo ./demo-outcomes
humanwill-policies validate ./demo-outcomes --config ./demo-outcomes/config-outcomes.yaml --json
humanwill-policies preview ./demo-outcomes --config ./demo-outcomes/config-outcomes.yaml --json
humanwill-policies evaluate ./demo-outcomes --config ./demo-outcomes/config-outcomes.yaml \
  --request ./demo-outcomes/request.json --mock-answers ./demo-outcomes/mock-answers.json --json
```

This uses scripted answers and makes no API calls. It verifies plumbing, not Jev
accuracy. Service and hook clients must understand result/3, as for config/3.

## Validation and evidence boundaries

Offline tests exercise threshold boundaries for all three outcomes and both
question strategies, trusted permission checks, shared settings across policies,
configuration rejection/hashing, ties, explicit uncertainty and monitor/failure
behavior. Service contract tests cover LiteLLM, Agentgateway and both hook clients
with scripted provider-shaped responses. These do not constitute new live-host
or model-quality measurements.

All historical policies, datasets, labels, source snapshots and measurement
results are preserved. Historical live protocols intentionally reject the changed
core: reproduce them at their recorded Git revisions. This also applies to the
source-pinned context and release-scope CLI helpers; the existing review HTML
continues to expose the preserved contexts and 102/73 split. Unit tests that reuse
those fixtures substitute only the historical source inventory inside test scope;
separate tests verify that unmodified live guards still reject the changed core.
No historical source hash is rewritten to claim equivalence.

Before adopting asymmetric values, freeze a new evaluation protocol and compare
false blocks, missed violations and uncertainty. Replaying stored answers can
measure decision-gate effects on those answers, but is development analysis, not
an independent holdout or evidence of improved model interpretation.

Verification completed: 181 offline tests pass on Python 3.14; the ten focused
threshold tests also pass on Python 3.11. Ruff lint/format checks pass. Both the
built wheel and source distribution install outside the checkout and pass the
old and new scripted demos, exported config/4 schema, service/hook contracts and
service startup/authentication/rollback checks. Local artifact evidence is in
`artifacts/packaging/outcome-thresholds-verification.json` (ignored). No hosted
model calls or public publication occurred.
