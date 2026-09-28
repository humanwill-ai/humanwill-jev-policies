# Full-policy template: first live pass

Frozen before measurement on 2026-09-28. The owner requested a live test of the
implemented Markdown-policy/shared-template path. Use the existing cumulative
$5 synthetic OpenRouter authorization: $0.078278768 spent, $4.921721232 available,
1412 settled prior evaluation calls, no unknown charges.

Run all 175 accepted events in their original order (272 policy judgments), one
pass, concurrency one, no retries, fallback or selective reruns. Model:
`typesafe/jev-1.13`, returned version allowlist `typesafe/jev-1.13-20260917`.
All policies remain monitor; every confidence gate stays at 0.80.

Treatment: config/5, full authored Markdown policy bodies, shared rubric
`humanwill.policy/1`, result/4. No hand-authored semantic scope questions.
The policy bundle, reviewed labels, requests, context-v1 sidecar, synthetic trusted
facts, source catalog and predicate/shortcut behavior stay unchanged. Trusted
values and gold labels do not enter model questions. Content and these synthetic
policies/context are authorized for hosted evaluation; no customer content is used.

Compare with the preserved complete `artifacts/quality/context-live-v1` run.
The new JSON protocol pins inputs, current evaluator/runner sources and baseline
artifacts. Historical protocols are unchanged and their old source guards are not
bypassed. The new runner independently verifies accepted synthetic cases, event-bound
context, bundle, and comparison labels. It refuses a dirty checkout or existing
output directory for live execution. Stop on an unknown charge; use the locked
existing ledger and in-process Keychain helper.

```sh
.venv/bin/python -m evals.step6.direct_policy_live \
  --baseline artifacts/quality/context-live-v1 --validate-only
.venv/bin/python -m evals.step6.direct_policy_live \
  --baseline artifacts/quality/context-live-v1 \
  --output artifacts/quality/direct-policy-live-v1 --allow-external \
  --keychain-helper /Users/sergio/Documents/humanwill-benchmark/humanwill/keychain.py
```

Report event and per-policy matches, false blocks, known violations allowed,
expected uncertainty incorrectly allowed, raw interpretation errors, confidence
rejections, regressions, latency distribution and total settled cost. Retain all
175 and the previously defined generic/advanced split; do not retune the split or
labels after seeing answers. Preserve failures and the full raw local run.

This is one observation per case against a historical control. It cannot establish
causation, stability, independent holdout accuracy, production source resolution,
host end-to-end latency or release qualification. The fixture context sidecar is
not automatically available through production connectors.
