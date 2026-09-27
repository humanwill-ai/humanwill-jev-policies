# Installation and packaging evidence

Recorded 2026-09-27 for private development version `0.1.0.dev3`. These are local artifact checks, not publication approval or a semantic-quality result.

## Verified locally

A clean wheel installation and a clean installation built from the exact source archive both passed on macOS x86_64, Python 3.11.5 and 3.14.0. Each environment was created outside the developer checkout, used a private temporary pip cache, installed the archive's locked runtime dependencies and passed `pip check`. The verifier checked that imports resolved inside the new environment, not the source tree. No HumanWill Benchmark checkout or unpublished dependency was used.

For each of the four installations:

- `init-demo`, configuration validation, prompt-stage preview, request schema export and scripted mock evaluation passed. The demo returned `allow`, `simulated: true`; it did not perform enforcement or evaluator calls.
- All 11 existing service/hook contract tests passed, covering both gateway adapters, both Copilot dialects, config/2 and config/3 hook results, authentication, stage restrictions, errors, monitoring, unsupported coverage and metadata trust.
- The installed `humanwill-policies serve` process started and served health/readiness, rejected unauthenticated evaluation, and returned an explicit evaluation error with external egress disabled. An invalid replacement configuration prevented startup; restoring the previous configuration and restarting passed.
- The source archive contained the container recipe, ignore rules, verification scripts, quickstart and release notes. The wheel supplied its schemas and offline demo.

The policy-author guide's Markdown collection/policy and config/3 snippets were extracted verbatim and validated together; prompt-stage preview passed. Ruff checks and formatting passed for the new scripts. The runtime and development locks now pin `typing-extensions==4.16.0` on every supported Python version, matching AnyIO's actual Python <3.15 requirement.

Local reports are ignored files `artifacts/packaging/step7-verify-311.json` and `artifacts/packaging/step7-verify-final-314.json`. They record identical tested inputs:

| Artifact | SHA-256 |
| --- | --- |
| `humanwill_policies-0.1.0.dev3-py3-none-any.whl` | `2473dc4569e7e5237c4c8637132fd1d92a32d9c0ce25f694c49cfdc73230087d` |
| `humanwill_policies-0.1.0.dev3.tar.gz` | `1666a6a51d50e49ca571fdd0c073490d23ba5b2fbf794adbf327cf23b0e67783` |

These hashes identify the development artifact snapshot tested before this evidence document was added. Rebuilding the source archive after documentation or other changes changes its hash; regenerate candidate evidence from the final reviewed commit. They are not published release checksums.

## Container and actual-host boundary

A local container recipe now installs an explicitly selected wheel plus the locked dependencies, uses UID/GID 65532, and allowlists build context inputs. The default base tag is for development; an approved immutable base digest and recorded image identity are needed for release reproducibility. Docker/Podman is not available on this Mac, so no local image-build result is claimed. The Ubuntu CI job is configured to build it and run the offline demo without network access; its result must be observed before marking that gate complete.

Artifact contract tests are not fresh executions of the actual LiteLLM, Agentgateway, Copilot CLI or interactive VS Code hosts. The updated unattended host CI now installs built wheels into the service and LiteLLM environments and runs copied harnesses outside the checkout; this candidate’s CI outcome is recorded separately after execution. Existing [pinned-host evidence](integration-report.md) remains separately scoped; the [connector guide](service-and-connectors.md) gives the real-host procedures. This packaging increment does not widen host support, establish a calibrated enforcement profile or change any policy threshold. Direct TypeSafe live smoke remains optional by owner decision.

[Quickstart](quickstart.md), [policy authoring](policy-authoring.md), [operations/rollback/troubleshooting](operations.md), and [release notes](../CHANGELOG.md) form the operating guide. See the separate service operations report for concurrency/fault tests. Licensing, public-content review, final candidate artifacts and owner publication authorization remain later release gates.
