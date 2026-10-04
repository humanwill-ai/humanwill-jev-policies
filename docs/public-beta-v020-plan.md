# Public Beta 0.2 preparation — 2026-10-04

Owner authorized the four proposed preparation steps. Target `0.2.0b1`, presented
as Public Beta for controlled company pilots, with monitoring defaults. Publication
of the release/tag/assets remains a separate final step after concrete review.
The existing public `v0.1.0a1` is unchanged.

## Scope

Include the implemented non-streaming structured-call profiles, LiteLLM MCP and
Agentgateway ExtMCP execution bindings, existing Copilot contracts, active-intent
question clarification, and a versioned disclosure-preparation policy example.
Keep compact/grouped assessment experiments outside runtime. Streaming remains
deferred. No production identity/source/destination resolver or approval UI is added.

Beta is not a calibrated enterprise enforcement claim. Independent semantic
qualification and pilot experience remain open. Package compatibility and exact
host coverage must be recorded separately from evaluator correctness.

## Checks and release artifacts

1. Freeze package/API scope, beta version, example policy and migration notes.
2. Run full local offline tests/lint, wheel/source installation outside checkout,
   upgrade/rollback and current host checks. Run the existing four-job core matrix
   and three-job host workflow once for the frozen candidate, not duplicate pushes
   and dispatches. Retain packages, hashes, reports and container inventory.
3. Measure synthetic new tool/MCP paths with live Jev through actual local LiteLLM,
   including paired unguarded timing and side-effect checks. Linux Agentgateway
   actual-process enforcement uses Actions with synthetic evaluator judgments;
   do not call that live Jev or Agentgateway end-to-end latency evidence.
4. Refresh installation, security/failure boundaries, coverage and release notes.
   Review pending public source and packaged contents. Stage concrete artifacts
   and a release description for final publication review.

The live campaign must freeze its own synthetic workload/protocol, use the existing
$5 ledger with its unchanged historical reservation, and stop on new unknown cost.
No real workflow text is needed. Provider keys stay in local Keychain/processes,
never Actions secrets or public artifacts. Direct TypeSafe live smoke remains optional.

## Actions accounting

The repository is public and the existing workflows use standard hosted runners.
GitHub documents these runner minutes as free for public repositories
([billing reference](https://docs.github.com/en/billing/concepts/product-billing/github-actions),
checked 2026-10-04). The old billing API returned 410 and requires an unavailable
admin scope; no credential escalation or billing changes were made. Keep artifact
retention bounded and download the exact evidence. No paid runners/overages authorized.

Status: all four preparation steps complete; see [final evidence](beta-final-ci-report.md). Seven jobs passed, exact assets/release notes staged. No release/tag published or deployment performed.
