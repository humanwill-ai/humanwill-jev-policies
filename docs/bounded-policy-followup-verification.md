# Runtime Q05 → Q04 verification — 2026-09-29

Implemented the owner-authorized bounded full-batch follow-up as an explicit
config/5 profile, `policy_assessment: q05_q04`. Existing configurations retain
original behavior. [Runtime contract and activation](bounded-policy-followup.md)
describe eligibility, preserved decisions, trusted facts, failure fallback,
accounting, byte/call/concurrency limits, and coordinated client upgrades.

Validation completed without new paid API calls:

- 231 offline tests passed on Python 3.14, plus Ruff lint/format checks.
- All 12 focused follow-up tests passed on Python 3.11. They cover accepted and
  rejected agreement, unchanged full-batch payloads and preview, metadata/freshness,
  primary versus secondary failures, disabled profiles, byte/call budgets, total
  deadline, cancellation, semaphore ownership, usage and explicit error fallback.
- LiteLLM and Agentgateway request paths and both Copilot hook dialects passed
  through the service contract harness with scripted low-confidence and follow-up
  responses. CLI submitted prompts remain assessment-only. These are local ASGI
  and hook-client checks, not new real LiteLLM/Agentgateway processes or interactive
  VS Code/Copilot runtime acceptance tests. Existing stage/coverage limits remain.
- All 597 event views from the preceding three-pass experiment's full-batch arm
  reproduced their saved decisions, policy outcomes, errors, coverage and requested
  enforcement under the new runtime. All 569 provider payloads exactly matched the
  recorded primary/follow-up requests; replies were replayed locally. The expected
  configuration digest and new diagnostics differ. The new implementation records
  both physical call usage records instead of the research runner's primary-only
  recomposed usage. Saved synthetic context was supplied explicitly for this replay;
  the runtime does not fabricate it for real requests.
- Exact wheel and source artifacts installed in isolated environments outside the
  checkout. Both passed existing service contracts, the new connector/failure
  checks, packaged profile validation, and installed service process
  startup/restart/rollback checks. Report:
  `artifacts/packaging/q04-runtime/verification.json`.

Artifact identities:

| Artifact | SHA-256 |
|---|---|
| Wheel | `ef1e79f5c271bc52e190088b0abbabaae4767a09a095596bf77bd108a3e940dc` |
| Source archive | `a32a2efdc2045b6935a65faa0bf412c4a89347879749b4af201eacb24d2ed5cd` |

The replay script and summary are local ignored evidence under
`artifacts/quality/q04-runtime/`. Historical live protocols and their hashes were
not rewritten to accept the changed runtime. Their source guards continue to reject
it. Two historical composition tests now load offline fixtures directly; a separate
test confirms the historical paid-run guard still rejects the new source.

Known cumulative API spend remains $0.260080178 plus the existing $0.01 unresolved
historical reservation; remaining authorization is $4.729919822. No new model quality
claim, 5% target achievement, public release, deployment or GitHub push follows from
these implementation checks. The new workflow labels still await owner review.
