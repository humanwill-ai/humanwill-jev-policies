# Roadmap to the first public release

Updated 2026-09-27 · service/gateway and hook software implemented; runtime checks pass; policy quality and later release gates pending

**Target: `v0.1.0a1`, a public preview on GitHub.** Publish a usable, tested implementation with all requested connectors and a clear support boundary. Public availability does not establish production suitability or semantic accuracy for arbitrary company policies.

Current inventory: installable offline package/CLI, policy/configuration schemas, synthetic fixtures, automated tests and CI, plus policy/design documentation. See the [foundation report](foundation-report.md). The evaluation core and both provider adapters now have offline tests; OpenRouter live smoke passed; direct TypeSafe has synthetic contract coverage; its separate live smoke is optional. The HTTP service and all requested connector adapters are implemented; real gateway/CLI/Local tests pass on the pinned versions. No project license or GitHub release exists. See [steps 4–5 evidence](integration-report.md). See [step 3 evidence](evaluation-core-report.md). The repository remains private. The owner authorized steps 1–7, including parallel step 7 packaging and remaining step 6 gate work with two subagents. This does not authorize publication.

This is the delivery and publication checklist. [Release design](release-plan.md), [optional metadata](optional-metadata.md), and [evaluation plan](evaluation-plan.md) remain the technical references. M1–M4 below implement the existing milestones; M5 expands into evaluation, packaging, and publication gates.

## Fixed release scope

- Markdown policy folder, recursive explicit references, stable policy IDs/versions, immutable bundle digest, and offline validation/preview.
- Shared semantic evaluation plus deterministic policy decisions, monitor/enforce modes, explicit errors and coverage.
- Optional metadata, recommended off by default. Independent trusted sources when enabled, no authorization from user assertions, and explicit handling of unavailable facts.
- Jev through OpenRouter (development default) and direct TypeSafe. Both transports must be tested.
- LiteLLM text request and non-streaming response checks on the chosen chat-completions configuration; Agentgateway text request/response webhooks.
- Both Copilot profiles: VS Code Local submitted-prompt/pre-tool controls; CLI prompt assessment and pre-tool controls, with documented host bypasses. No claim of CLI prompt blocking or universal Copilot interception.
- Installable Python package, service/CLI, runnable examples, compatibility table, evaluation report, and public project documentation.

Defer governance UI, SSO administration, multi-tenant SaaS, approval workflows, multimodal/streaming inspection, other agent runtimes, decision caching, and registry publication. These are not prerequisites for a useful public preview.

## Work packages and exit evidence

Each row should become a small series of reviewable changes. A checkbox means evidence exists for the release candidate, not merely that a feature was coded.

| Step | Work | Exit gate and evidence |
| --- | --- | --- |
| 1. Freeze the implementable contract | Set package/CLI names, policy schema, request/result schema, feature switches, supported OS/Python/host versions, and limits. Complete the bounded benchmark/`jev-edge` reuse/license review. | Offline fixtures cover three representative policies; a compatibility table names exact versions and intended stages. Record adopted decisions and unresolved pilot questions. |
| 2. Build the offline foundation — M1 | Package skeleton, CLI, folder resolution, IDs/hashes, policy preview, configuration validation. Establish CI now. | Clean checkout installs; validation/preview need no credentials or network. Tests cover cycles, missing/duplicate IDs, symlink/path escapes, parser limits, snapshots, disabled rules, and unsupported configuration. |
| 3. Build the evaluation core — M2 | Mock backend, OpenRouter/direct transports, answer validation, decision aggregation, optional metadata predicates, deadlines and bounded resource usage. | Unit/contract tests prove every decision/error branch; metadata-off makes no enrichment calls or metadata disclosures; a missing answer/batch cannot allow. Budgeted synthetic OpenRouter smoke succeeds. Both transports pass contract tests; direct TypeSafe live smoke is optional per owner decision on 2026-09-27. |
| 4. Deliver the service and gateways — M3 | Authenticated HTTP service; pinned LiteLLM and Agentgateway configurations; request and response adapters; minimal logs and health/readiness endpoints. | Real host processes call a controlled mock downstream. Denied inputs never invoke it; denied outputs never reach the client. Fault injection verifies timeout/error/unsupported behavior. Authentication and policy selection cannot be weakened by request data. |
| 5. Deliver both Copilot profiles — M4 | Hook executable, runtime-specific payload/output handling, installation/removal instructions, explicit compatibility checks. | On both actual pinned runtimes, approved actions run and denied actions have no controlled side effects. Verify Local prompt stop, CLI prompt assessment, and timeout/disabled-hook behavior. Mock hook fixtures alone are insufficient. |
| 6. Measure policy quality | Freeze three narrow policies, labels, development/held-out split, rubric versions, and acceptance targets. Compare Jev with deterministic checks and one alternative judge. | Versioned report with separate false-block/missed-violation rates, uncertainty, errors, attacks, coverage/bypasses, latency, and cost. Only profiles meeting their predeclared targets are described as suitable for enforcement; all shipped examples default to monitoring. |
| 7. Make installation and operation reproducible — M5 | Wheel/source distribution, local container recipe, quickstart, policy-author guide, connector guides, troubleshooting, compatibility matrix, release notes and rollback. | A clean environment installs from the exact built artifacts and completes offline demo plus documented connector scenarios. No dependency on the developer checkout, temporary files, or unpublished private repositories. |
| 8. Prepare the public repository | Choose license, preserve third-party notices, review history and exposure, configure CI/security/contribution practices, build draft release assets. | Reviewed release-candidate commit, checksums, test/report links, third-party inventory and public-content review. No unresolved release-blocking findings. |
| 9. Publish and verify | Obtain owner go-ahead for the concrete candidate, then change visibility and publish the GitHub prerelease. | Public repository and release resolve without authentication; clean-clone install works; tag, commit, assets, checksums and documentation agree. |

**Dependencies:** 1 → 2 → 3 → 4/5 → 6/7 → 8 → 9. Establish the dataset and documentation alongside implementation; finish the report against the candidate. Copilot access may delay its runtime evidence gates but do not block the offline loader or mock tests. Do not drop a required connector to meet a date without an explicit scope change.

## What confidence must mean

### Deterministic and integration gates

- [ ] Every shipped connector/stage has an allow, deny, monitor, error, and unsupported-coverage test. Record the host version/configuration and observed downstream behavior.
- [ ] Required metadata off/missing/untrusted/stale has the documented result. Complete negative facts are distinguished from unknown facts. Connector authentication survives feature toggles.
- [ ] Requester-supplied policies, groups, thresholds, and destinations cannot override trusted deployment settings.
- [ ] Wrong-stage evidence is not reused as permission. Mutated arguments, documents, or provider routes trigger the required new checks.
- [ ] Payload/concurrency/deadline limits are exercised; overload and provider failures have explicit outcomes. No uncontrolled retry loop or silent content truncation.
- [ ] Every supported deployment has tested restart/invalid-bundle handling and a way to restore the previous bundle/configuration. Disabling enforcement is an explicit operational choice.

### Semantic evidence gate

Finalize the [test policies under review](test-policies.md): the owner selected project-code/design/documentation protection with approved-system exceptions; destructive production actions and classified-document restrictions remain candidates. This replaces the earlier illustrative policy-class list. Retain metadata-off conformance tests separately. Label authorization/classification evidence independently of the text.

Proposed starting held-out set: **100 legitimate and 100 violating examples per policy**, plus at least 20 missing/unknown-evidence and 20 adversarial cases per policy: 720 cases across three policies. This is an initial evidence budget, not sufficient evidence for every enterprise error target. Keep authoring examples and threshold-tuning data outside the held-out set; group near-duplicates in the same split. Have a second human review labels and resolve disagreements.

The owner approved initial per-policy targets: 95% interval upper bounds ≤5% for false blocks and missed violations, ≤5% errors on fully specified cases, p95 added latency ≤2 seconds, and evaluator API cost ≤$1 per 1,000 cases. Before running the holdout, adjudicate labels and freeze rubric/configuration versions. Report sample counts and confidence intervals; expand the sample if it cannot substantiate the target. A model's confidence value is not evidence of achieved accuracy. Repeat a subset to assess variability; do not tune on the holdout and then report it as unseen.

Publish results for each policy, route, and relevant stage, including failed cases that can be shared safely. Include a representative concurrency/failure exercise, p50/p95/p99 added latency, retries, billed usage, and service overhead. Compare alternatives under the same evidence and fixed budgets. Do not claim superiority from advertised price or one aggregate score.

Passing transport tests does not require identical judgments across providers. It requires valid contracts, recorded model identity, and no silently substituted route. If no semantic policy meets its agreed targets, the planned enforcement preview is not ready: improve it or explicitly agree to a narrower assessment-only release. Publication is not a reason to conceal failure.

## CI and supported-environment plan

Start with the minimum supported Python version plus one current version validated during Step 1; record the exact versions rather than promising all future releases. Test the portable package on Linux/macOS and test hook scripts on each OS actually listed as supported. Additional OS coverage is explicit work, not inferred from Python portability.

PR CI: formatting/lint, type checks where useful, meaningful unit/contract tests, package build/install smoke, offline demo, and deterministic integration fixtures. Use a scheduled/manual real-host integration job where feasible; preserve human-run evidence for interactive Copilot checks. Live provider runs are explicitly budgeted and use synthetic inputs, kept separate from untrusted PR jobs. No keys or privileged tokens go to forked PR code.

Add dependency and secret checks, minimal workflow permissions, pinned action revisions, and a release build tied to the reviewed commit. Any failure affecting auth, policy selection, stage enforcement, parser containment, packaging, or declared contracts blocks release. Track the remaining known limitations openly; no arbitrary code-coverage percentage substitutes for these tests.

## Public repository and release package

Create these as working artifacts during Steps 7–8, not empty placeholders now:

- `LICENSE` and any required `NOTICE`/third-party attribution; `CONTRIBUTING.md`, `SECURITY.md` with a real reporting channel, and `CHANGELOG.md`.
- README with a short product promise, offline quickstart, the three connector families, stage limits, optional metadata, data-flow disclosure, measured results, and the HumanWill Benchmark relationship.
- Policy/config/API references, one runnable guide per connector profile, troubleshooting, compatibility matrix, and clear monitoring-to-enforcement instructions.
- Source distribution and wheel from the reviewed commit, SHA-256 checksums, dependency inventory/SBOM, test evidence, and public-safe evaluation artifacts. Provide a container recipe; defer image-registry and PyPI publication unless separately selected.

**License proposal:** Apache-2.0 for newly authored code and, if the owner agrees, new docs/examples. Review the [license text](https://www.apache.org/licenses/LICENSE-2.0) and preserve the actual licenses of anything reused. Do not automatically import or relicense benchmark datasets, policy material, or `jev-edge` code. Final licensing is an owner decision before publication.

Review **all Git history and refs**, commit metadata, tracked examples, reports, release assets, existing issues/PRs, Actions logs/artifacts, and references to private projects. Scan for credentials and private material; investigate findings rather than treating a clean scanner result as proof. GitHub notes that [making a repository public exposes Actions history/logs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility). Resolve any exposure before the visibility change, and recheck access/rules afterward. If a secret is found, revoke/rotate it and resolve history exposure before release.

## Final release checklist

Prepare a reviewable draft containing the exact candidate commit, proposed tag `v0.1.0a1`, license choice, artifacts/checksums, passing checks, measured report, known limitations, and final README/release notes. GitHub supports [draft releases and a prerelease label](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).

- [ ] All required features and real-runtime evidence above are complete.
- [ ] Publication/privacy/license review is complete; public assets contain no private customer content.
- [ ] Fresh-environment installation and offline demo pass from the actual release artifacts.
- [ ] Owner has authorized publishing this concrete candidate; steps 1–7 authorization does not change visibility.
- [ ] Make `humanwill-ai/humanwill-jev-policies` public and publish the prepared prerelease at the reviewed commit.
- [ ] Verify anonymous access, asset downloads, checksums, clean installation, and released configuration examples; verify org repository settings after visibility changes.

If a post-publication defect appears, mark the affected release/feature clearly and ship a new fixed version. Do not move the published tag to different code or assume returning the repository to private recalls copies. Maintain a small triage list and a named maintainer for reports; use the supported-version matrix to bound ongoing work.

## Immediate next work and owner inputs

**Steps 1–2 are implemented:** the contracts, offline loader/CLI, CI, and three synthetic policy classes are documented in the [foundation report](foundation-report.md). Step 3 software is implemented; its OpenRouter smoke passed and direct TypeSafe live smoke is optional for v0.1. Step 4 service/gateway implementation and real-host checks now pass. Step 5 adapters and both CLI/Local runtime tests pass, including documented host bypasses. See [integration evidence](integration-report.md). Step 6’s [initial development comparison](evaluation-development-report.md) and [config/3 follow-up](evaluation-v3-report.md) are complete, as is the [clarified-policy/instruction-integrity live comparison](integrity-live-report.md). Jev matches the revised software cases, and the owner removed the standalone integrity rule after it created false blocks without fixing Gemini's remaining bypasses; draft labels and held-out evidence still need review. The step 6 release gate remains open. Step 7 packaging and the remaining step 6 work now run in parallel. The [gate audit](step6-release-gates.md) separates observed development metrics from qualifying evidence; the [new review packet](step6-review-candidates-v1.md) supplies concrete cases for human adjudication. The [service operation checks](service-operation-gates.md) exercise local load, failures and recovery without provider calls. Elapsed time cannot substitute for release evidence.

Owner inputs needed before later gates: license choice and human label review. Policy intentions, initial acceptance targets and remaining-$5 synthetic evaluation budget are now recorded in [decisions](decisions.md). None requires placing secrets in the repository or in chat. Set a maintainer/security reporting destination before public release.
