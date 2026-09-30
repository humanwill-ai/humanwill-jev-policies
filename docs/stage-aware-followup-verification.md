# Optional stage-aware follow-up — implementation verification

Implemented 2026-09-30 after owner authorization. Config/5 accepts
`policy_assessment: q05_stage_aware`. Q05 remains the primary scope question;
eligible abstentions receive at most one full-batch follow-up. Normalized
`tool_action` selects the exact measured tool wording; every other stage uses Q04.
Selection does not inspect prompt keywords, case IDs or model classifications.

Existing `q05_q04`, `q05`, omitted and `standard` profiles retain their behavior.
The new profile shares the existing continuation implementation, preserving
same-choice agreement, thresholds, trusted metadata, original total timeout,
concurrency, byte/call budgets, strict response validation and explicit fallback.
Content-only semantic rules and deterministic checks keep their existing behavior.

Preview shows the exact question for each stage; result/4 records the selected
profile plus the existing primary/secondary evidence and both usage records.
The packaged `config-stage-aware-followup.yaml` starter leaves metadata-dependent
rules disabled. Enablement is documented in the [runtime contract](bounded-policy-followup.md).
Service and strict hook/client validators must be upgraded together to accept the
new profile enum. This implementation does not enable the profile in deployments.

## Verification

- Full offline suite: 253 tests passed on Python 3.14 before adding one final
  installed-artifact routing assertion. All 17 focused stage-aware tests, including
  that assertion, then passed on both Python 3.14 and 3.11. Ruff passed.
- Focused tests reuse the existing metadata/freshness, failure/fallback,
  cancellation, deadline, concurrency, batch limits, usage and connector contracts
  with the new profile. Additional checks compare exact measured wording and
  preview across every stage, preserve content-only semantics, and confirm the
  historical live source guard still rejects modified runtime code.
- Both arms of the frozen three-pass full-pack campaign replayed through the
  implemented evaluator: **1,050 event views and 970 exact provider payloads**.
  Saved decisions, policy rows, errors, coverage and requested enforcement match.
  The expected configuration hashes and runtime follow-up diagnostics differ;
  usage now includes both physical calls. Synthetic context was explicitly supplied
  for replay; production does not fabricate those observations.

The replay uses recorded replies locally, with no new API calls. Evidence is in
`artifacts/quality/stage-aware-runtime/`. Frozen protocols, labels and model
responses were not rewritten. The full live comparison remains development
evidence: [4.7% pooled unexpected abstention, with regressions and limits](stage-tool-v1-report.md).

No new real LiteLLM/Agentgateway process or interactive VS Code/Copilot acceptance
run is claimed. Connector checks use scripted replies through local service and
hook contracts. No deployment, publication or GitHub push. API spending is unchanged:
known $0.299032028 plus historical $0.01 reservation, leaving $4.690967972.

## Installed artifacts

Exact wheel and source archives installed outside the checkout and passed packaged
stage-aware configuration validation, tool-stage routing, service/hook contracts,
failed-follow-up fallback and service startup/authentication/restart checks.
No editable source import was used. Local verification record:
`artifacts/packaging/stage-aware-runtime/verification.json`.

| Artifact | SHA-256 |
|---|---|
| humanwill_policies-0.1.0.dev3-py3-none-any.whl | `d8e69ac1bb7510e9c7976c5e749555244aa1c27dbdc4908290d1b6848804a588` |
| humanwill_policies-0.1.0.dev3.tar.gz | `01f2b0b5664b968080d47f38e90d0a6ed7e0070f2288fabf881fc589b961cc12` |
