# Step 6 release-gate audit

2026-09-27 · **Engineering checks can proceed alongside packaging; the semantic release gate remains open.** No new provider calls were made for this audit. The cumulative recorded spend remains $0.052577498 of the authorized $5.

The current evaluation bundle has software policy version 2, production policy version 1, and document policy version 1. Jev through OpenRouter remains the intended evaluator. Gemini was a comparison baseline; its further tuning is not required. The owner removed the standalone instruction-integrity rule, and it remains removed. Existing adversarial tests check the reliability of these business rules.

## What the existing Jev results establish

This table recomputes the 107 target-rule-only primary observations in `integrity-ab-jev-development-base` and `integrity-ab-jev-attacks-base`, measured at source revision `35c180c44ada703adecee9b8e65e9bbb5f24bb9e`. Only the target policy was activated for each event in that historical bundle; the retired integrity policy was inactive. It is not a new run of the current tree. Repeated measurements are excluded from accuracy denominators.

| Policy | False blocks, count / legitimate; upper 95% bound | Misses, count / violations; upper 95% bound | Specified errors | Core/provider p95 | API cost / 1,000 events |
| --- | --- | --- | --- | --- | --- |
| Software | 0/19; **16.82%** | 0/27; **12.46%** | 0/46 | 481.7 ms | $0.029886 |
| Production actions | 1/14; **31.47%** | 0/20; **16.11%** | 1/34 (2.94%) | 420.5 ms | $0.028238 |
| Confidential documents | 0/8; **32.44%** | 0/8; **32.44%** | 0/16 | 0.70 ms | $0 |

Every confidence upper bound exceeds the approved 5% target. These Wilson intervals are descriptive: related scenario families and draft labels prevent them from qualifying as independent holdout evidence in any case. The production false block is a low-confidence assessment of a benign literal-command printing case, retained as a hypothetical fail-closed block and separately as an evaluation error. Its error rate is below 5% in this small sample; that does not remove the false block.

The software, production and document sets contain 49/38/20 events in 25/24/18 families respectively. All 11 deliberately unknown cases remain indeterminate. Jev's software result is encouraging, but zero observed misses is not a proven enterprise miss rate. The document policy is deterministic and makes no model call; its zero evaluator cost says nothing about real metadata-provider cost or correctness.

Observed core/provider latency and API cost are below their numerical targets. They exclude real host round trips, representative concurrency, deployment/metadata overhead, labeling and operations. End-to-end service/host latency remains a separate gate. The [service operation exercise](service-operation-gates.md) adds synthetic concurrency and failure evidence; it cannot establish live-provider tail latency.

Reproduce the descriptive audit from the existing ignored local artifacts:

```bash
python -m evals.step6.gates \
  --run artifacts/quality/integrity-ab-jev-development-base \
  --run artifacts/quality/integrity-ab-jev-attacks-base
```

The audit rejects pooling incompatible evaluator/configuration/protocol identities or duplicate primary event IDs. It never treats repeats as independent accuracy samples, unknown billed usage as free, hypothetical blocks as actual enforcement, or editable manifest claims as human-review proof. Its overall result stays `not_assessable` for the current development runner. All historical reports/artifacts and the cumulative spending ledger are preserved.

## Prepared now — owner label review complete

The editable [36-case review packet](step6-review-candidates-v1.md) places each policy beside event content, trusted facts, owner-approved labels and rationale. It covers all three rules and relevant stages, including approved coding assistance, actual onward operations, destructive shell/interpreter effects, metadata failures and evaluator manipulation. Each rule has four allow cases, six violation cases including two adversarial examples, and two missing-evidence cases.

This is **label calibration and scenario review**, not a claimed independent holdout. Several cases revisit known failure mechanisms. Exact duplicate and family-name checks pass, but those checks cannot establish semantic independence. Current tests inject gold scope answers to verify deterministic composition; they do not measure Jev's judgment of these cases. The live runner rejects the `review_candidate` split, so this packet cannot accidentally be evaluated as development evidence or promoted by an edited review-status string.

The [pre-review snapshot](../evals/step6/prospective/snapshot-v1.json) binds exact candidate, current configuration, policy bundle and evaluator source hashes. Hashes detect edits; they do not authenticate reviewers or establish approvals. Candidate changes require a new version/snapshot, preserving the prior review context. Validate it without network calls:

```bash
python -m evals.step6.gates --candidate
python -m unittest discover -s tests -p test_release_quality_gates.py -v
```

## What remains before the semantic gate can close

1. **Done: human label review of the current 36-case packet**, marked complete by the owner on 2026-09-27, with labels accepted unchanged. No second reviewer is claimed. This approval does not cover labels in a future independent holdout or retroactively approve superseded historical cases.
2. Assemble and independently review the actual holdout: the proposed starting budget is 100 legitimate, 100 violating, 20 unknown and 20 adversarial cases per policy. Do not fill it with minor paraphrases or assume this review packet is automatically eligible. Keep scenario families separate from development/tuning. Decide realistic host/stage/language/context mixtures; synthetic cases alone still cannot establish customer performance.
3. Freeze that reviewed dataset, exact rubric/configuration/model identity, thresholds, source revision and repeat subset before any live holdout measurement. Preserve threshold 0.8 unless separately changed using development evidence. Add a reviewed-holdout execution path after that protocol exists; the current runner deliberately supports only development data.
4. Run the frozen Jev evaluation within the remaining authorized budget; report errors, misses and false blocks separately by policy and relevant stage. Run a representative real host/service/provider latency workload with declared concurrency and failure behavior. Reconcile every billed call with the existing ledger. No customer data or new publication authorization is implied.
5. Apply the predeclared targets to qualifying evidence. Publish failed cases honestly. Only a profile meeting the targets can be described as suitable for enforcement; otherwise improve using development data and reserve a new holdout, or agree an explicitly narrower assessment-only release. Keep shipped examples in monitor mode.

A zero-error sample needs at least 73 independent observations per class just to put the two-sided Wilson 95% upper bound below 5%; with 100 per class, even one observed error puts that upper bound above 5% (about 5.45%). The 36-case packet cannot prove the approved rate targets even if every case is correct. A credible independent sampling and review plan is the next decision; more Gemini calls do not resolve them.

## Live performance follow-up

The [live latency report](release-latency-report.md) now records a passing
<=2-second p95 result for the declared LiteLLM and hook-executable workload,
including concurrency four. Whole-IDE/CLI scheduling, Agentgateway live latency
and customer production traffic remain outside that measured scope. Spend is now
$0.065024282 cumulatively. The [new 100-case targeted tranche](holdout-v1-label-review.md)
is frozen and ready for label review; no live holdout measurement has occurred.
The prior 36-case owner review remains complete.

## September 28: completed review and first combined live run

The owner export accepts 175 cases (93 updated, 46 source, 36 previously approved)
and excludes seven. The frozen Jev/OpenRouter run is complete: 161/175 exact event
outcomes, no known violations allowed overall, ten legitimate events returning
errors, and one source-policy unknown incorrectly allowed inside an event that
remained an error. Production/source uncertainty exceeds the specified-error
target. See [the report](reviewed-live-v1-report.md) and
[all policy disagreements](reviewed-live-v1-failures.md). Cumulative spend is
$0.071233898 of $5. Human label review is complete for this scope; independent
qualification and production source resolution remain open. Preserve this first
pass while developing fixes; do not relabel it as an unseen holdout after tuning.
