# Step 6 development evaluation

These are synthetic development examples, not a held-out benchmark or a calibrated
enterprise enforcement profile. All bindings use monitoring. The runner invokes
the actual reusable evaluator; it does not execute a host tool or deliver a model
response. Step 4–5 host evidence remains a separate measurement.

## Scope and evidence

- `EVAL-SW-001`: semantic project-material disclosure scope plus a deterministic
  destination approval check. Already-public project material is not exempt.
- `EVAL-PROD-001`: semantic destructive-action scope plus an independently derived
  permission fact. The fixture authority allows a verified disposable sandbox or
  an authorized production operation. Unknown environment/authorization stays
  unknown; user claims are not used.
- `EVAL-DOC-001`: deterministic known-confidential classification and destination
  restriction. This control makes no model call and is not evidence of Jev quality.

Each of 60 explicit English cases includes stage, rationale, expected scope,
expected aggregate decision, synthetic trusted facts, family and slice tags.
There are eight legitimate, eight violating and four unknown cases per policy.
Related destination/authorization pairs share a family. Labels are assistant
proposals awaiting human review; passing the gold-scope wiring test verifies
composition, not correctness of semantic judgments or human agreement.

The evaluator never receives labels, rationales, case IDs or trusted metadata as
semantic input. Jev and the comparator see the same scope question, event content
and coverage. The shared deterministic engine uses independently supplied facts.
The keyword baseline matches explicit terms without reading labels. Its one-hot
scores encode deterministic choices and are not calibrated probabilities. Chat
confidence/probabilities are self-reports, not comparable calibrated measurements
of confidence. All routes use the pre-existing, uncalibrated 0.8 monitoring
threshold. No threshold tuning or policy changes were made from live results.

Every case is assessed against its target policy alone. Public non-project
material outside the document rule does not override the software rule. Combined
policy bundles require separate tests; do not infer them from isolated results.

## Run

Install development requirements and the project from a checkout, then:

```sh
python -m evals.step6.run --backend keyword --output artifacts/quality/keyword
# Supply OPENROUTER_API_KEY locally and obtain the applicable data/budget authorization.
python -m evals.step6.run --backend jev --allow-external --output artifacts/quality/jev
python -m evals.step6.run --backend chat --allow-external --output artifacts/quality/chat
```

An output directory must be new. Reports contain per-case decisions, model scope
judgments, confidence, errors, hashes, timings, returned model IDs and usage, not
raw input bodies. The source dataset is synthetic and versioned. Model comparisons
share the same ledger at `artifacts/quality/spending.json`; never delete or change
that ledger to bypass spending accounting. One process lock prevents concurrent
runs sharing it. There are no retries or fallbacks. `--limit N --repeats 2` can
characterize variability on a development subset; repeats are not independent
accuracy samples and are excluded from first-pass accuracy summaries.

The owner authorized using the remainder of the original $5 total budget for
synthetic step 6 evaluations. The ledger starts with $0.000024696 prior smoke
spend, reserves $0.01 before each call and records reported cost on completion.
Unknown, interrupted or over-reservation charges stop further live calls until
reconciled. This is conservative local accounting, not an OpenRouter account-wide
hard cap. Use the same ledger for all runs and account for any other calls.

Reviewed 2026-09-27: [Jev 1.13](https://openrouter.ai/typesafe/jev-1.13) lists
$0.042/million input tokens, no output-token charge and a 32K context. The
[Gemini 2.5 Flash-Lite comparator](https://openrouter.ai/google/gemini-2.5-flash-lite/pricing)
uses OpenRouter with only `google-ai-studio`, fallbacks disabled, a price ceiling
of $0.10/$0.40 per million input/output tokens and 512 output tokens. Chat requests
are bounded to 24,000 UTF-8 bytes. Live endpoint metadata confirmed these prices
and structured-output support before testing. Recheck pricing before new runs;
request/byte limits and reservations do not override provider billing terms.
The chat adapter uses [structured output](https://openrouter.ai/docs/guides/features/structured-outputs)
and validates it through the core; malformed results remain errors.

## Reporting and acceptance

Approved initial targets per policy: 95% interval upper bounds no greater than 5%
for false blocks and missed violations; at most 5% errors on fully specified
cases; p95 added end-to-end latency at most two seconds; evaluator API cost at
most $1 per 1,000 cases. Targets are frozen before live development measurements.
The proposed release held-out set is 100 legitimate, 100 violating, 20 unknown
and 20 adversarial cases per policy, subject to label review and sufficient
independent scenario families. Do not manufacture confidence by paraphrasing a
few templates into hundreds of rows.

- False blocks under hypothetical fail-closed operation include legitimate cases
  returning evaluation errors. Semantic false violations and errors are also
  reported separately. Monitoring does not actually block any request here.
- Misses count violating cases assessed allow. Errors are not counted as correct
  semantic judgments, even when a fail-closed deployment would block them.
- Unknown cases and attacks have separate slices. No failed row is dropped.
- Wilson two-sided 95% intervals are descriptive only on paired development
  families; the independent-sample assumption does not hold for those pairs.
  Eight examples per class cannot substantiate the approved release targets.
- Timing includes core processing plus provider round trips and client connection
  setup at concurrency one. It excludes real gateway/hook overhead. Model-free
  document checks are broken out; their latency must not inflate semantic results.
- Costs are reported per complete event and call. Unknown costs remain unknown,
  never zero. API costs exclude labeling, hosting, network and maintenance labor;
  this run is not a total cost of ownership estimate.
- Development results cannot pass the release gate. Human label adjudication,
  separate held-out families, calibrated/frozen profiles and representative
  workload/host latency measurements are required before an enforcement claim.

The [initial report](../../docs/evaluation-development-report.md) records the baseline. The [config/3 follow-up](../../docs/evaluation-v3-report.md) records revised live runs, added attacks, separate uncertainty analyses and the remaining gate. Replay recorded Jev answers without network calls using `python -m evals.step6.replay artifacts/quality/jev-v1`; these diagnostics do not change the configured threshold.

## Revised development configuration

Use `--config evals/step6/config-v3.yaml` for opt-in trusted-predicate shortcuts
and stage-specific questions. Add `--dataset evals/step6/adversarial-development.json`
for the matched 36-case attack/control suite. Keep fresh output directories and
the same spending ledger. Baseline config.yaml and development.json are unchanged.
See [the decision reference](../../docs/decision-v3.md) for per-model offline
threshold analysis, compatibility and limits on calibration claims.
