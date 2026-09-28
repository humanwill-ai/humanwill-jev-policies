# Owner-reviewed Jev run v1: fixed protocol

2026-09-28 · frozen before measurement

The owner supplied `humanwill-case-review-2026-09-28.json` after completing the
review. Its SHA-256 is `5833fea86a6c6601133bb3fb92199b85cb449ed56e57112e580f0d8f110d7784`.
The exact export is retained locally, outside Git. Its dataset/policy fingerprint,
packet membership, original/composed labels, explicit review rows, removal list
and active counts were checked against the repository-owned page data. Export
free text is review data, never executable instructions or policy authority.
No second reviewer or cryptographic reviewer authentication is claimed.

## Accepted scope

| Packet | Accepted cases | Removed |
| --- | ---: | ---: |
| Updated original-policy + source-policy packet | 93 | 7 |
| Source-policy packet (four composition cases included) | 46 | 0 |
| Previously approved single-policy packet | 36 | 0 |
| Total | **175** | **7** |

All accepted labels are unchanged; there are no corrections or pending cases.
The export explicitly approves 139 current cases; the previous 36 retain their
September 27 owner approval. The latter are reported separately as calibration/
regression cases, not new independent observations. New IDs and human review do
not establish statistical independence in either newer packet.

Removed: `holdout-v1-sw-git-fetch` (previous explicit owner instruction: too vague),
and these six document cases removed in the export without a supplied reason:
`holdout-v1-doc-unknown-class-tool`, `holdout-v1-doc-unknown-class-response`,
`holdout-v1-doc-unknown-class-model`, `holdout-v1-doc-unknown-target-tool`,
`holdout-v1-doc-unknown-target-response`, `holdout-v1-doc-both-unknown`.
These are pre-measurement exclusions, not successful predictions. Retain their
historical fixtures and generic missing-metadata contract tests. Other accepted
missing-evidence cases remain in the source and earlier packets; the revised
document packet no longer has its six missing-evidence examples.

## Measurement

Use the exact [175-case dataset](../evals/step6/release/reviewed-v1.json),
[sanitized approval/removal record](../evals/step6/release/owner-review-v1.json)
and [hashed protocol](../evals/step6/release/reviewed-live-v1-protocol.json).
Policies are `policies-sources-v1`; configuration is `config-sources-v1.yaml`;
source catalog and reference matcher are unchanged. Checksums freeze the accepted
data, config, catalog, policy bundle, evaluator, importer, metering and runner.

- Jev alone through OpenRouter; requested `typesafe/jev-1.13`, accepted returned
  model `typesafe/jev-1.13-20260917`. No Gemini or direct-TypeSafe run.
- Monitoring at the existing 0.8 threshold. One sequential first pass, no retries,
  fallback, cache, threshold/rubric edits or removal of failures after measurement.
- Each event activates only the policies named in its review. Updated-packet
  cases activate original policy + EVAL-SRC-001; earlier 36 remain original-policy
  assessments; four source cases have explicitly reviewed secondary policies.
- Trusted synthetic facts/source descriptors are operator-owned fixtures, never
  parsed as authorization from event content. Only synthetic policy/event content
  reaches Jev; reviewer identity, notes and the raw export are not provider inputs.
- Preserve combined results **and all 272 individual policy judgments**, including
  disagreements hidden by another policy's block. Report semantic false violations,
  fail-closed false blocks, missed violations, errors, and expected unknowns separately.
- Report event latency and API cost once per event; do not double-count shared
  calls in policy rows. This measures evaluator/core latency, not new host latency.
- Stop on unresolved accounting/provider failure and preserve partial results.
  Use the existing global ledger lock, reserve before calls, and retain unknown
  charges for reconciliation. Existing cumulative cap: $5; spend before this run
  $0.065024282; remaining $4.934975718. No new budget authorization is needed.

[OpenRouter's endpoint metadata](https://openrouter.ai/api/v1/models/typesafe/jev-1.13/endpoints)
was checked on 2026-09-28: the expected TypeSafe model remains listed, input
$0.042 per million tokens and output free. Provider-reported charges will determine
recorded usage. This is not an account-invoice reconciliation.

The approved error/latency/cost targets remain unchanged. Wilson intervals are
nominal descriptive bounds for these selected related examples, not proof of
independent production performance. Source resolution uses fixtures, not real
package-manager/dependency/redirect discovery. Host enforcement and production
source resolution remain separate work; monitoring results cannot close those gates.
