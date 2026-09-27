# Step 3 implementation evidence

2026-09-27 · `0.1.0.dev1` · private development milestone

**Software implemented; OpenRouter live smoke passed.** One authorized synthetic request used the existing macOS Keychain credential and reported a cost of **$0.000024696** against the **$5 total** cap. The earlier environment/.env-only check missed that credential. See the [live smoke evidence](smoke-2026-09-27.md). No direct-provider call has been made. The owner subsequently waived its separate live smoke for v0.1; synthetic direct transport contracts remain required. The [smoke procedure](provider-smoke.md) is available for optional future checks.

Delivered:

- Gateway-independent evaluator and `evaluate` CLI; scripted mock default and explicit hosted opt-in.
- Versioned config/2 and result/2; preserved Markdown/request/v1 validation. Explicit semantic, deterministic, and scoped-predicate strategies, with deterministic applicability conditions.
- Separate trusted in-process evidence and egress interfaces, source/completeness/event/freshness checks, optional metadata off, and no raw metadata forwarded to a provider. Authentication/source acquisition remain the embedding host's responsibility.
- Strict Choice/ID/model/numeric validation, per-policy evidence, independent assessment/requested action, error-preserving aggregation, simulation markers, and known/unknown batch usage.
- OpenRouter and direct TypeSafe HTTP adapters with fixed destinations, explicit model allowlists, no retry/fallback/redirect, byte/batch/concurrency limits, total deadline, immediate overload handling, and cancellation.

Local evidence: **88 tests pass on Python 3.11.5 and 3.14.0**. Tests include missing/malformed/extra answers, unknown models, low confidence/ties, batch failure aggregation, monitor/fail-open outcomes, incomplete coverage, all four event stages, spoofed/stale/replayed evidence, deterministic group/destination conditions, unrelated scoped actions, metadata-off non-disclosure, exact egress permits, limits, deadlines, overload/cancellation, both HTTP request shapes, credential/HTTP/network errors, and packaged CLI behavior. Adversarial text is kept as untrusted input in fixtures; these tests do not measure a live model's resistance to it.

Ruff formatting/lint, dependency consistency, runtime advisory audit, source/wheel build, and fresh wheel demo/evaluation checks are part of validation. The advisory audit reports no known runtime dependency vulnerabilities on the review date. Hosted CI repeats the deterministic tests and built-wheel example across Ubuntu/macOS and Python 3.11/3.14; consult [commit-specific Actions results](https://github.com/humanwill-ai/humanwill-jev-policies/actions/workflows/ci.yml) rather than treating workflow presence as a passing result.

The repository remains private. The step-3 increment did not include a service, gateway/Copilot connectors, host enforcement, semantic-quality benchmark, license choice, public release or deployment. The owner subsequently authorized steps 4–5 and waived direct TypeSafe live smoke as a release gate. See [current service/connector evidence](integration-report.md).
