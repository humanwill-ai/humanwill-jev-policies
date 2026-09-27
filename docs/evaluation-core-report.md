# Step 3 implementation evidence

2026-09-27 · `0.1.0.dev1` · private development milestone

**Software implemented; live-provider acceptance gate pending.** No OpenRouter or TypeSafe call was made. The owner authorized a **$5 total** synthetic smoke budget. Neither provider key was set in the environment and no repository .env existed; credentials are still needed. Limit the planned smoke to one small request per route, with no automatic retries. The [smoke procedure](provider-smoke.md) makes the remaining gate reproducible without publishing or deploying anything.

Delivered:

- Gateway-independent evaluator and `evaluate` CLI; scripted mock default and explicit hosted opt-in.
- Versioned config/2 and result/2; preserved Markdown/request/v1 validation. Explicit semantic, deterministic, and scoped-predicate strategies, with deterministic applicability conditions.
- Separate trusted in-process evidence and egress interfaces, source/completeness/event/freshness checks, optional metadata off, and no raw metadata forwarded to a provider. Authentication/source acquisition remain the embedding host's responsibility.
- Strict Choice/ID/model/numeric validation, per-policy evidence, independent assessment/requested action, error-preserving aggregation, simulation markers, and known/unknown batch usage.
- OpenRouter and direct TypeSafe HTTP adapters with fixed destinations, explicit model allowlists, no retry/fallback/redirect, byte/batch/concurrency limits, total deadline, immediate overload handling, and cancellation.

Local evidence: **88 tests pass on Python 3.11.5 and 3.14.0**. Tests include missing/malformed/extra answers, unknown models, low confidence/ties, batch failure aggregation, monitor/fail-open outcomes, incomplete coverage, all four event stages, spoofed/stale/replayed evidence, deterministic group/destination conditions, unrelated scoped actions, metadata-off non-disclosure, exact egress permits, limits, deadlines, overload/cancellation, both HTTP request shapes, credential/HTTP/network errors, and packaged CLI behavior. Adversarial text is kept as untrusted input in fixtures; these tests do not measure a live model's resistance to it.

Ruff formatting/lint, dependency consistency, runtime advisory audit, source/wheel build, and fresh wheel demo/evaluation checks are part of validation. The advisory audit reports no known runtime dependency vulnerabilities on the review date. Hosted CI repeats the deterministic tests and built-wheel example across Ubuntu/macOS and Python 3.11/3.14; consult [commit-specific Actions results](https://github.com/humanwill-ai/humanwill-jev-policies/actions/workflows/ci.yml) rather than treating workflow presence as a passing result.

The repository remains private. No service, gateway/Copilot connector, actual host enforcement, live semantic evaluation, license choice, public release, or deployment is included. Finish the budgeted smoke gate for both actual provider routes; then proceed to step 4's authenticated service and real gateway tests. The live gate remains outstanding even if step 4 implementation proceeds alongside it.
