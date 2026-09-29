# Roadmap to the first public release

Updated 2026-09-28 · review and first combined live run complete; semantic and later release gates remain open

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

The owner reported 90% of `humanwill-ai`'s included Actions minutes used on
2026-09-28. Apply the [Actions budget constraint](decisions.md#github-actions-budget-constraint--2026-09-28):
validate locally first, batch CI-triggering pushes and reserve discretionary
hosted runs until quota is checked. Required candidate evidence remains a release
gate; budget exhaustion is not a passing check. Current automatic triggers are
unchanged, and Actions overages are outside the OpenRouter evaluation budget.

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

**Steps 1–2 are implemented:** the contracts, offline loader/CLI, CI, and three synthetic policy classes are documented in the [foundation report](foundation-report.md). Step 3 software is implemented; its OpenRouter smoke passed and direct TypeSafe live smoke is optional for v0.1. Step 4 service/gateway implementation and real-host checks now pass. Step 5 adapters and both CLI/Local runtime tests pass, including documented host bypasses. See [integration evidence](integration-report.md). Step 6’s [initial development comparison](evaluation-development-report.md) and [config/3 follow-up](evaluation-v3-report.md) are complete, as is the [clarified-policy/instruction-integrity live comparison](integrity-live-report.md). Jev matches the revised software cases, and the owner removed the standalone integrity rule after it created false blocks without fixing Gemini's remaining bypasses; draft labels and held-out evidence still need review. The step 6 release gate remains open. Step 7 packaging and the remaining step 6 work now run in parallel. The [gate audit](step6-release-gates.md) separates observed development metrics from qualifying evidence; the [new review packet](step6-review-candidates-v1.md) supplies concrete cases for human adjudication. The [service operation checks](service-operation-gates.md) exercise local load, failures and recovery without provider calls. Step 7 implementation and installation/operation evidence now pass: see the [packaging report](packaging-report.md) for all seven CI jobs, installed-wheel host tests and the offline container demo. Elapsed time cannot substitute for release evidence.

Owner label review of the current 36-case packet is complete. Later inputs include license choice and the separate review protocol for a newly assembled independent holdout. Policy intentions, initial acceptance targets and remaining-$5 synthetic evaluation budget are now recorded in [decisions](decisions.md). None requires placing secrets in the repository or in chat. Set a maintainer/security reporting destination before public release.

## Additional source-policy gate — 2026-09-28

The owner added EVAL-SRC-001 (approved inbound software sources). Its Markdown
rule, synthetic allowlist/reference matcher, monitoring configuration and new
46-case review packet are prepared; labels and live quality are pending. See
[the source-policy design](approved-software-sources.md). Existing integration
and latency evidence does not demonstrate production package-source resolution.
Before advertising automatic download restrictions, implement and test bounded
trusted origin resolution for the claimed host/tool workflows, including
redirects, transitive acquisitions, optional metadata and failure behavior.

## Active 100-case review correction — 2026-09-28

The active packet now includes EVAL-SRC-001 alongside the original named policy
for all 100 events; see [the revised review](holdout-sources-v2-review.md).
The direct dependency tarball is unapproved and the combined expected result is
block. Original review records remain historical; the expanded checks need review.
The old live runner/protocol remains single-policy historical evidence and does
not establish the new suite’s quality. No new model calls were made.

## September 28: completed review and first combined live run

The owner export accepts 175 cases (93 updated, 46 source, 36 previously approved)
and excludes seven. The frozen Jev/OpenRouter run is complete: 161/175 exact event
outcomes, no known violations allowed overall, ten legitimate events returning
errors, and one source-policy unknown incorrectly allowed inside an event that
remained an error. Production/source uncertainty exceeds the specified-error
target. See [the report](reviewed-live-v1-report.md) and
[all policy disagreements](reviewed-live-v1-failures.md). Cumulative spend is
$0.071233898 of $5. Human label review is complete for this scope; independent
qualification and production source resolution remain open. Preserve this first
pass while developing fixes; do not relabel it as an unseen holdout after tuning.

## Context-only live comparison complete — 2026-09-28

The authorized full rerun is complete at clean source `1007939`, with the exact
prepared context and all policies/questions/labels/thresholds unchanged. See
[results](context-live-v1-report.md) and [case comparisons](context-live-v1-cases.md).
Combined matches improve 161→166/175; raw scope errors fall 6→2/227; fail-closed
false blocks fall 10→6/79. No known violations or expected unknowns are allowed.
Six events improve and one formerly correct event regresses. The dry-run rsync
case changes from error to explicit false violation; the Kubernetes source answer
is still wrong but now contained by lower confidence. Production specified errors
remain above target, and p95 evaluator latency rises to 2.58 seconds. This one-pass
development comparison does not close the release gate or prove causality.
148 calls cost $0.007044870; all charges settled. Cumulative spend $0.078278768
of $5, leaving $4.921721232. No additional tuning or selective reruns were made.

## Narrower release scope — 2026-09-28

Owner accepted keeping advanced command interpretation as documented diagnostics
outside first-release acceptance. [Release scope v1](release-scope-v1.md) applies
input/capability criteria to all 175 accepted cases: 102 generic-policy cases and
73 advanced diagnostics (including 66 passing cases). No case, label, approval or
historical result is deleted; no runtime allow/bypass is added. This is a
post-measurement scope decision, not improved or independent accuracy evidence.
Two generic combined failures remain: explanation-only prompt and unapproved Git
fetch, both correct Jev choices rejected by the unchanged confidence gate. A source
error on an empty response is masked by a correct document block. Production
policy has only one generic example after this split; representative structured
action cases are required before claiming its quality. Statistical, latency and
production-resolver gates remain open. No provider calls or new spending.

## Global outcome thresholds — 2026-09-28

Owner authorized three configurable confidence gates shared across all policies,
rather than per-policy asymmetric settings. Implemented as opt-in config/4; see
[outcome thresholds](outcome-thresholds.md). All three default to 0.80, old configs
and historical evidence remain unchanged, and config/4 rejects legacy per-policy
thresholds. Scope applicability still requires deterministic authorization;
uncertainty handling and connector enforcement remain separate. Content-only
violation/compliant answers share the applicable/not_applicable gates. Result/3
remains compatible with existing connectors. Offline validation is not calibration:
no new live calls or spending, no qualified asymmetric enforcement profile, and
release quality gates remain open.

## Offline asymmetric-threshold comparison — 2026-09-28

Owner-approved replay is complete: all 175 original outcomes/evidence reproduce
through the current core, including the symmetric config/4 control. Changing only
`not_applicable` 0.80→0.70 improves combined matches 166→168/175 (generic100→101/102,
advanced66→67/73), policy matches260→264/272, and fail-closed false blocks6→4/79.
No outcome regresses; no known violation or expected unknown becomes allowed at
event or policy level. This is reused-answer counterfactual analysis, not new model
accuracy or calibration. [Report](threshold-replay-v1-report.md) retains all cases
and limitations. Deployment defaults/configs remain unchanged. Proposed next work:
three complete live stability repetitions under a new frozen protocol; none run
as part of this offline comparison. Spend remains $0.078278768 of $5.


## Actual-policy evaluation update — 2026-09-28

Owner approved replacing manually authored semantic scope questions with the actual Markdown policy and a reusable adapter template. Opt-in config/5/result/4 implements this direction; trusted metadata and deterministic predicates stay separate, optional and explicitly configured. See [design, migration and validation limits](direct-policy-evaluation.md). Existing model evidence does not validate the new template; a fresh full-pack Jev run remains required before quality claims or enforcement qualification. No publication/default enforcement change.


## Full-policy live result — 2026-09-28

The authorized full175 Jev/OpenRouter pass completed at d624c9c with unchanged policies, labels, context, model, monitor modes and 0.80 gates. The shared-template path regressed: 142/175 exact events vs166, 228/272 policy outcomes vs260, fail-closed false blocks32/79 vs6, known violations allowed0/84, expected unknowns retained12/12. Raw scope errors12/226 (one malformed response) vs2/227; correct raw choices rejected for low confidence35 vs12. No tuning/reruns. See [full report](direct-policy-live-v1-report.md). Keep the new template experimental and preserve the previous measured path; release quality remains open. Cost $0.010850028, cumulative $0.089128796, remaining $4.910871204. All1560 cumulative evaluation calls settled. One normalized batch lacks usage after answer validation failure; its transport cost is settled and included.


## Patch-confidence experiment — 2026-09-28

Owner requested100 live synthetic variations to investigate low confidence. Completed50 distinct requests x2 repetitions,100 calls,200 scope questions at clean65dc823. See [protocol](patch-diagnostics-v1-protocol.md) and [report](patch-diagnostics-v1-report.md). Frozen randomized order, no retries, runtime policies/template/gates unchanged.36 scored diagnostic judgments per condition (new labels provisional), four source-origin judgments unscored: correct accepted baseline15,tool context27,focused question30,concise policy16,concise+focused28. Explicit local provenance helps source confidence but not enough for disclosure; focused restricted-action wording is a more promising next experiment than simply shortening policies. All positive controls accepted. Two malformed responses have probabilities summing0.99; strict current validation retained. Not independent quality evidence or causal proof. Cost$0.008754060; total$0.097882856; remaining$4.902117144; all1660 cumulative calls settled.


## Focused full-policy pass — 2026-09-28

Owner accepted testing the focused question on all175 with brief context where needed. Completed at636cb85: full policies/labels unchanged, active0.80/0.70/0.80 gates, one neutral git-apply note,148 calls with no retries. Against recorded answers replayed at the same gates:156/175 vs151 exact,248/272 vs242 policy matches,14/79 vs23 fail-closed false blocks,0/84 known violations allowed,12/12 expected unknowns retained.13 fixes and8 regressions; disclosure improves but source/production policy results regress. Git-apply passes with source confidence0.77/disclosure0.93. Keep candidate experimental; no runtime template promotion. See [report](focused-policy-v1-report.md) and [protocol](focused-policy-v1-protocol.md). Run cost$0.010737426,total$0.108620282,remaining$4.891379718; all1808 cumulative calls settled. No malformed responses in this pass, strict validation unchanged.


## Nine-error diagnosis and incomplete effect-question experiment — 2026-09-28

Reviewed the remaining nine legitimate errors and prepared neutral tool descriptions
plus a shared question clarification. The broader question candidate regressed five
previously passing cases in the first11 paired events; do not promote it. A provider
timeout stopped the planned two-arm full-pack run after23 calls (22 priced replies,
one unresolved charge). No target case is demonstrated fixed; only base64 returned
new judgments, while tar timed out and the other seven were not reached. See the
[case-by-case findings and partial report](effect-question-v1-report.md). Keep the
smaller focused-policy-v2 candidate separate from tool-context experiments. Policies,
labels, runtime template, gates and release qualification remain unchanged. Known
cumulative spend$0.110940572 plus$0.01 reserved for the unresolved call; no further
provider calls until accounting is reconciled. Local source commit e1751bc; no push.


## Restart completed — 2026-09-29

Owner-requested fresh two-arm test completed at dd975e7:175 events per arm,296 new
calls, all new charges settled. Question-only149/175 exact; question+context156/175
versus saved baseline156. Context fixes4 of the nine target cases but still has
16 legitimate errors and3 known-violation errors; no known violation/expected unknown
is allowed.11 fixes and11 regressions against baseline; do not promote the broader
wording. [Full results](effect-question-restart-v1.md) distinguish changed context
from identical-payload variation and preserve the original interrupted attempt.
Known cumulative spend$0.135761732 plus the owner-authorized carried$0.01 unresolved
reservation; total accounted$0.145761732, remaining$4.854238268. No runtime change,
release qualification or GitHub push.

## Short-question experiment — 2026-09-29

The ten-variant wording experiment does not change public-release readiness. No variant resolves every remaining failure; no runtime candidate was promoted and no push or publication occurred. See [measured results](short-questions-v1-report.md).
