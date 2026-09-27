# Foundation implementation evidence

2026-09-27 · `0.1.0.dev0` · private development milestone

This increment implements requested steps 1–2: freeze the small contracts and build the offline foundation (previous roadmap rows 0–1). It does not complete the public release or the evaluation milestone.

## Delivered

- Installable `humanwill-policies` package with `validate`, `preview`, `init-demo`, and schema export commands.
- Markdown collections/policies, recursive explicit includes, stable IDs, exact source hashes, immutable snapshots, and deployment configuration bound to the bundle digest.
- Restricted YAML, root-contained file access, cycle/duplicate detection, non-regular-file rejection, bounded input, and explicit validation errors.
- Optional metadata/source settings, exhaustive policy bindings, monitor defaults, dependency checks, and rejection of unsupported stage/enforcement settings. These checks do not authenticate metadata or evaluate rules.
- Local authoring/configuration and candidate request/result schemas. Three synthetic request cases cover content-only, finance authorization, and classified-document destinations; a result fixture is explicitly synthetic.
- Pinned runtime/development dependencies, original-code reuse decision, candidate compatibility table, and CI with minimal permissions and pinned action revisions.

## Verification

Local tests run on macOS with Python **3.11.5** and **3.14.0**: **50 tests pass** on each. They cover malformed/unsafe YAML, missing/duplicate IDs, include cycles and bounds, path escapes/symlinks/FIFOs, exact-byte and relocation-stable hashes, detached snapshots, mismatched bundle/configuration, metadata dependencies, unsupported CLI enforcement, timestamp/coverage consistency, CLI error output, and no-network offline operations.

Ruff lint/format and `pip check` pass. The original authoring examples validate. The runtime dependency audit reports **no known vulnerabilities** on the review date; it does not establish the absence of vulnerabilities. Dependencies are pinned, not artifact-hash locked.

Package verification builds a source distribution and then a wheel from it. A fresh environment installs that wheel and runs the packaged demo and schema export outside the checkout. The CI workflow repeats tests, build, and isolated installation on Python 3.11/3.14 across Ubuntu 24.04/macOS 15. See the [actual Actions runs](https://github.com/humanwill-ai/humanwill-jev-policies/actions/workflows/ci.yml) for commit-specific hosted results; workflow configuration alone is not evidence of a passing run.

Reproduce local checks with the README development commands. No provider credentials, model calls, hook installation, customer data, or paid evaluation are used by this milestone. Package downloads and the advisory audit require network access; offline commands do not.

## Boundaries and next increment

The first implementation supports POSIX filesystem operations on Linux/macOS. Windows and exact Copilot extension compatibility are deferred. The candidate host versions have not been exercised; no connector is supported yet. No registry artifact, GitHub release, license selection, visibility change, or deployment is included.

Step 3 starts with mock evaluation and deterministic decisions. Resolve semantic applicability versus metadata predicates, verified evidence provenance/freshness, aggregation, probability evidence, and deadlines before adding real Jev transports. Both actual provider routes, all required gateway/hook runtimes, semantic evaluation, and publication gates remain outstanding. See the [roadmap](public-release-plan.md).
