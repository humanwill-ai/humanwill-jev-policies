# Full-pack focused-question experiment

Frozen before measurement on 2026-09-28 after the owner accepted the recommendation
from the100-call patch diagnosis. Test the focused common task/answer criteria with
the **full unchanged Markdown policies** on all175 accepted events. Use active
confidence gates applicable0.80, not_applicable0.70, insufficient_evidence0.80.

The experiment uses an evaluation-only backend wrapper; deployed runtime templates,
company policy files and historical case labels remain unchanged. It reuses the
exact focused task and three criteria from patch-diagnostics-v1 for all scoped
policies and stages, without policy-ID-specific questions. Existing context-v1 is
retained. One extra sentence accompanies only the discussed git-apply case:

> Reads an existing patch and edits local files; this operation does not fetch, upload or execute the patch. Its origin and approval are not established by this description.

This is a neutral fixture observation about the exact supplied operation, not a
new production command parser, blanket local-file trust, or proof of authorization.
No new patch origin is invented. Other unavailable scripts/manifests stay unavailable.
The sidecar is not automatically supplied by production connectors.

One sequential pass, no retries/fallback/selective reruns, model typesafe/jev-1.13
with returned allowlist typesafe/jev-1.13-20260917. All175 cases and272 policy
judgments remain, including advanced command diagnostics. Trusted predicates and
positive shortcuts are unchanged; expect148 provider calls. Monitor only.

Primary comparator: saved direct-policy-live-v1 answers replayed at the same
0.80/0.70/0.80 thresholds (151/175 exact;23/79 false blocks if fail-closed).
The runner first reproduces all original0.80 decisions/configuration digests,
then changes only not_applicable to0.70. The original malformed response is retained
as an error, not repaired or supplied with an invented answer. This control replay
has no API calls. Also save comparison against the unmodified live0.80 baseline.

Pin all input/source hashes and baseline artifacts. Start live work from a clean
commit, reuse the locked cumulative$5 ledger and in-process Keychain credential.
Prior spend$0.097882856; remaining$4.902117144;1660 calls settled. Do not alter the
strict probability-sum validator during this experiment. Save full synthetic
provider requests/responses locally for diagnosis, separate from normalized results.

Report exact event/policy decisions, explicit false violations, fail-closed false
blocks, known violations allowed, unknowns wrongly allowed, raw scope errors,
confidence rejections, malformed responses, cost and evaluator latency. Preserve
all regressions and the existing generic/advanced partition. Positive changes do
not automatically qualify deployment. The comparison is historical, not randomized
or a fresh repeated control, and has one observation per case. The task and one
case's context change together; their separate contribution is not isolated here.

```sh
.venv/bin/python -m evals.step6.focused_policy_live \
  --baseline artifacts/quality/direct-policy-live-v1 --validate-only
.venv/bin/python -m evals.step6.focused_policy_live \
  --baseline artifacts/quality/direct-policy-live-v1 \
  --output artifacts/quality/focused-policy-live-v1 --allow-external \
  --keychain-helper /Users/sergio/Documents/humanwill-benchmark/humanwill/keychain.py
```
