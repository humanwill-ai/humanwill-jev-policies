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

A local container recipe now installs an explicitly selected wheel plus the locked dependencies, uses UID/GID 65532, and allowlists build context inputs. The default base tag is for development; an approved immutable base digest and recorded image identity are needed for release reproducibility. Docker/Podman is not available on this Mac, so no local image-build result is claimed. The Ubuntu CI job built it and ran the offline demo without network access successfully; see the integrated evidence below.

Artifact contract tests are not fresh executions of the actual LiteLLM, Agentgateway, Copilot CLI or interactive VS Code hosts. The updated unattended host CI now installs built wheels into the service and LiteLLM environments and runs copied harnesses outside the checkout; the integrated evidence below records the passing candidate run. Existing [pinned-host evidence](integration-report.md) remains separately scoped; the [connector guide](service-and-connectors.md) gives the real-host procedures. This packaging increment does not widen host support, establish a calibrated enforcement profile or change any policy threshold. Direct TypeSafe live smoke remains optional by owner decision.

[Quickstart](quickstart.md), [policy authoring](policy-authoring.md), [operations/rollback/troubleshooting](operations.md), and [release notes](../CHANGELOG.md) form the operating guide. See the separate service operations report for concurrency/fault tests. Licensing, public-content review, final candidate artifacts and owner publication authorization remain later release gates.

## Integrated candidate evidence

Commit `b6fbeb977e472d5a9c335fa8236200a5b0653f35` passed all seven jobs:

- [Policy core CI](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/36334410881): Ubuntu 24.04 and macOS 15, each on Python 3.11 and 3.14; 138 offline tests, exact wheel/source installations outside checkout, installed service startup/rollback, local service load/failure exercise, and dependency audit.
- [Pinned host CI](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/36334410894): LiteLLM 1.102.1, Agentgateway 1.5.0 and Copilot CLI 1.0.88 passed using installed wheels and copied harnesses outside the checkout. The LiteLLM environment also installed that job's exact wheel. Config/2 synthetic provider answers were used; no paid provider calls occurred.
- Ubuntu/Python 3.14 built the container and completed its offline demo with networking disabled. The selected immutable base was `python@sha256:a36c24f9cbdf4fd0f52d67f0823eeac19c2028c637cecc392d97f980d4fec56b`; the local CI image ID was `sha256:778111c929f8343378732b9448ac174c475e5c04b5747985358fcc1218525634`. No image was pushed to a registry.

The final local integrated wheel/source verification also passed on Python 3.14,
recorded in ignored `artifacts/packaging/integrated-verification.json`. Its hashes
were wheel `3a645d075970ed4163c12b0f1b56b2809fb9731e8c0aa0cd18ef9f218c2f809a`
and source `5f92402554a3da3f8c0f502fbc010c6fbca54899289e627e488e9e4005355d70`.
Later documentation updates do not make those the final public release assets;
step 8 must build and verify the actual reviewed release candidate.

Step 7's implementation and unattended installation/operation evidence are
complete for this development candidate. Interactive VS Code Local retains its
previous pinned runtime evidence; it was not rerun during this packaging work.
Step 6's human-reviewed independent quality and representative host/provider
latency gates remain open. This is a private development candidate, not a public
release or a claim of production readiness.
