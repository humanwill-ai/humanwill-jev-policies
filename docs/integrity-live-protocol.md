# Approved coding and instruction-integrity live comparison

> **Retired experiment:** the owner subsequently removed the standalone instruction-integrity policy, its configurations and dedicated fixtures/tests. This document preserves historical evidence, not current setup instructions. Removed files are available at [the measured revision](https://github.com/humanwill-ai/humanwill-jev-policies/tree/35c180c44ada703adecee9b8e65e9bbb5f24bb9e). Use `policies-v2` and `config-disclosure-v2.yaml` for the current three-policy evaluation bundle.

Protocol fixed before calls, 2026-09-27. Synthetic development evidence only;
all detailed labels remain drafts, all bindings monitor at 0.8. The owner
requested real API tests within the existing cumulative $5 budget. Prior ledger
spend: $0.013426784; do not reset the ledger.

## Hypotheses

1. Code, including `x = 2`, and review-only requests to the approved coding model
   are allowed; requested onward disclosure to unapproved/unknown/unspecified
   destinations is a violation under software policy version 2.
2. Adding EVAL-INJ-001 may catch Gemini's earlier injected uploads, but may also
   create false blocks. Its mere presence does not establish protection.
3. Jev's earlier correct injected-upload assessments may stay correct; additional
   errors/false blocks must be counted rather than assuming behavior unchanged.

## Fixed design

Use collection `policies-v3`, configuration `config-integrity-ab.yaml`, and exact
returned-model allowlists already in the transports. The sole new configuration
limit is `questions_per_batch: 1` for both models/arms, matching the comparator's
single-question contract. Each policy sees the same event independently; this
compares decision aggregation with an extra policy, not appending the new rule to
another policy's question. There is no shared conversational memory between calls.

For each of Jev and Gemini:

- Evaluate `development-v2.json` (71 cases) and
  `adversarial-development-v2.json` (36 cases) with only each case's target policy.
- Evaluate those same 107 cases with target policy plus `--also-policy EVAL-INJ-001`.
  Active policy IDs are recorded in the manifest. Pair results by case ID; keep
  complete per-policy answers to distinguish added-policy effects from changes
  in repeated target-policy answers.
- Evaluate `instruction-integrity-development.json` (25 cases) with only the new
  policy to test active override requests versus legitimate analysis/testing.
- Evaluate the fixed nine-case `integrity-ab-repeat.json` subset (software families
  2, 4, 6: attack, unmodified control, benign local edit) twice more per arm/model.
  These are the three former Gemini bypasses and matched controls. They are
  preselected, not selected from the new results. Repeats are excluded from main
  first-pass rates and reported as repeated observations, not independent samples.

There are 550 total event assessments planned (some deterministic, some needing
one or two provider calls), with no retries or provider fallbacks. Run serially
under the same locked spending ledger. Preserve and stop on unknown charges.
Existing per-call reservations and request limits remain active. Current endpoint
price ceilings are checked before the first call; no customer content is sent.

## Interpretation

Report original-case allow/block/error counts, hypothetical fail-closed false
blocks and missed violations separately, unknown-case handling, added-policy
judgments, timing and API cost. Monitor mode does not actually execute or deny host
actions. Isolated policy metrics cannot establish a combined improvement; compare
paired assessments and investigate every newly blocked legitimate case.

The existing calibration tool rejects combined-policy runs to avoid silently
analyzing them as isolated decisions. No threshold or policy will be tuned during
these measurements. Reused families, draft labels, limited sample size and lack
of real-host/load testing keep the release quality gate open even if observed
errors are zero. API cost excludes deployment and labeling costs.
