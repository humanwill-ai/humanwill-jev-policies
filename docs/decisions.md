# Decisions and open requirements

Updated 2026-09-27. Owner requirements and proposed implementation choices are separate.

| Topic | State | Current direction |
| --- | --- | --- |
| Repository | Decided by owner | Private `humanwill-ai/humanwill-jev-policies`, alongside `humanwill-ai/humanwill-evals` |
| Project relationship | Decided by owner | Companion to `humanwill-benchmark`, applying company-driven policies to agents |
| Policy ownership | Decided by owner | Users/companies supply their own policy sets |
| Policy authoring | Decided by owner | Markdown folder, main file references same-folder/subfolder files, stable ID for each policy |
| First-release connectors | Decided by owner | LiteLLM, Agentgateway, and Copilot hooks; all three required |
| Jev access | Decided by owner | Direct TypeSafe and OpenRouter; OpenRouter for development/testing |
| Copilot runtime(s) | Decided by owner | Both VS Code Local and Copilot CLI, with distinct contracts |
| Contextual metadata | Decided by owner | Optional; easy enable/disable; combine trusted facts with semantic judgments, never accept claimed authorization as proof |
| Metadata defaults | Adopted for foundation | Off by default; independent source configuration; content-only policies still work; explicit treatment of dependent rules |
| Stage coverage | Decided by owner | Generated-answer and action policies require checks at those stages |
| Folder schema | Implemented v1 | Front matter, explicit includes, one policy per file, immutable hashes; see release plan/examples |
| Runtime stack | Implemented | Python 3.11–3.14 package/CLI and HTTP service on Linux/macOS; direct/OpenRouter providers and all required connectors |
| Build versus extend | Adopted after bounded review | Original independent core; no upstream code/text copied; see compatibility/reuse review |
| Initial enforcement | Proposed | Text gateway requests and non-streaming responses, plus supported pre-tool/prompt hooks; monitoring first |
| Uncertainty/failure | Proposed | Explicit error/indeterminate result; configurable failure action, default block in enforce mode |
| Human review | Proposed exclusion | Reject unsupported review configuration; no approval workflow in v0.1 |
| Customer demand | Unvalidated | Enterprise platform/security teams are the target, not validated paying customers |
| Hosted customer data | Open | Confirm policy-text/content egress, destinations, retention, and geographic constraints |
| Live budget / quality targets | Approved by owner | $5 cumulative synthetic smoke/evaluation budget; per-policy accuracy, error, latency and cost targets recorded below |
| GitHub Actions allowance | Owner reported 90% used, 2026-09-28 | Conserve remaining account quota through local validation and batched pushes; exact balance, reset date and overage settings unverified; separate from OpenRouter budget |
| Public release objective | Decided by owner | Plan a first release suitable for public GitHub publication; visibility remains private during preparation |
| Release label / artifacts | Proposed | `v0.1.0a1` public preview, source/wheel/checksums and evidence; see public-release roadmap |
| Project license | Awaiting owner choice | Proposed Apache-2.0 for original code/docs/examples; preserve licenses of reused material |

## Requirement update: 2026-09-27

The owner expanded the initial two-integration suggestion to three mandatory connector families, specified Markdown policy folders and IDs, and selected OpenRouter for development. These supersede the initial choice between Agentgateway and VS Code as a second integration. The enterprise focus and relationship to HumanWill Benchmark are now explicit.

Follow-up: metadata must be optional and switchable, including user/group information. Metadata-dependent policies still need authoritative evidence; turning the feature off cannot establish authorization. The owner also requires checks at the stages governed by a policy. The proposed release now includes non-streaming gateway response checks, superseding the earlier response deferral; unavailable stages remain explicit limitations. See [metadata and stage design](optional-metadata.md).

Publication planning: the owner requested steps toward a confident public first release. The [public-release roadmap](public-release-plan.md) adds real-runtime evidence, semantic evaluation, packaging, licensing, and a public-content review. Private alpha validation becomes preparation for the proposed public preview. Publication itself awaits a completed, reviewable candidate and owner go-ahead.

## Next concrete work

Steps 1–2 of the [public-release roadmap](public-release-plan.md) are implemented: authoring/configuration contracts, package/CLI, loader, IDs/digests, preview, tests, and CI. See the [foundation report](foundation-report.md). The roadmap now uses one-based numbering to match the requested steps; these were previously rows 0–1. No model calls, service, or connectors were implemented in this increment.

Step 3 software is now implemented: mock/backend abstraction, deterministic and scoped predicates, strict Jev adapters, bounded batching/deadlines, and an assessment CLI. Its OpenRouter live smoke passed using Keychain; the direct TypeSafe live smoke is optional for v0.1 per owner decision. The owner approved a $5 total synthetic smoke cap. See [core contracts](evaluation-core.md) and [evidence](evaluation-core-report.md). Do not interpret a valid evaluation-profile configuration as measured accuracy.

Foundation decisions: package/CLI `humanwill-policies`, import `humanwill_policies`, version `0.1.0.dev0`; explicit include lists and one policy per file; reject all symlinks under the root; bounded restricted YAML; exact source and normalized configuration hashes; monitoring defaults and required explicit policy bindings. Freeze authoring format v1 and candidate request/result fixtures with versioned changes. Candidate host versions are recorded but untested; final VS Code Copilot extension build remains an integration-stage choice.

## Additional requirements and ideas

Append dated requirements here and update the plan when they change scope.

## GitHub Actions budget constraint — 2026-09-28

The owner reported GitHub's email that 90% of the included Actions minutes for
`humanwill-ai` have been used. Treat this as an account-wide resource constraint;
the email does not identify this repository's share, exact remaining minutes,
billing-cycle reset date, or paid-usage settings. No account billing audit has
been performed.

Source inspection at `128378cad8aa06f3677d9d9a8e9028f39bb0e97c` found four core
matrix jobs (Ubuntu/macOS, Python 3.11/3.14) plus three pinned-host jobs on every
main push and pull request, including documentation-only changes. Both workflows
also accept manual dispatch; the host workflow additionally runs on pushes to
`work/service-gateway-hooks`. Neither has path filters or concurrency cancellation.
This identifies opportunities to conserve minutes, not measured cost attribution.

For ongoing work, validate locally first, batch CI-triggering pushes, and avoid
discretionary hosted reruns while quota is unverified. Preserve final-candidate
Linux/macOS, packaging and host evidence requirements; local results must keep
their actual scope. Workflow changes such as cancellation of superseded runs,
safe documentation filtering and a smaller routine matrix remain proposals.
Existing workflow triggers and organization billing settings are unchanged.

[GitHub's billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-actions),
reviewed 2026-09-28 (live documentation; no source revision pinned), says included
minutes reset each billing cycle. After exhaustion, usage is blocked without a
valid payment method; paid usage is subject to configured budgets. The warning
alone therefore does not establish whether future jobs will stop or incur charges.
Actions spending is separate from the approved $5 OpenRouter evaluation cap.

## Step 3 decisions — 2026-09-27

- Preserve original v1 shapes; use config/2 for explicit strategies, deterministic applicability conditions, limits, and returned-model allowlists; emit result/2 with probability evidence, simulation marker, and batch usage. Markdown and request/1 remain stable.
- Combine facts through `predicates` or `scoped_predicates`; no model-derived authorization. Optional `when` conditions avoid applying confidential-document constraints to known-public material. Unknown facts stay errors.
- Keep trusted evidence and evaluator disclosure authorization in a separate in-process embedding interface. No payload flag, raw header, or CLI metadata file establishes trust. Actual authentication adapters remain future integration work.
- Default to complete declared coverage, no retries/fallback, bounded sequential batches, an overall deadline, and immediate overload errors. Mock runs never request enforcement.
- Core transport code covers both providers in step 3, superseding the earlier M3 placement of direct TypeSafe. The OpenRouter live smoke passed; direct TypeSafe live smoke is optional for v0.1 per owner decision. The $5 total synthetic smoke budget has provider-reported spend of $0.000024696 for one request. OpenRouter was already stored in macOS Keychain; the earlier environment-only credential check was incomplete. See [smoke evidence](smoke-2026-09-27.md).

## Steps 4–5 authorization — 2026-09-27

The owner explicitly waived direct TypeSafe's separate live smoke as a first-release requirement and authorized service/gateway and both Copilot-profile implementation. Retain direct TypeSafe transport and contract tests; OpenRouter remains the live development route. This does not authorize public publication.

Use Starlette + Uvicorn for the small HTTP layer, retaining the existing JSON Schema contracts instead of adding a second model/schema layer. The core stays independent. Optional metadata enrichment is a trusted in-process resolver; default service deployments do not promote client metadata to facts.

## Step 4–5 implementation status

Authenticated service, LiteLLM/Agentgateway adapters and both Copilot command profiles are implemented. Gateway, CLI and VS Code Local host tests pass with synthetic controlled evaluators/downstream effects. After completing Copilot sign-in, Local prompt stop and pre-tool denial were observed with working allow controls. Both Copilot runtimes can bypass checks on host timeouts or disabled hooks. See [integration report](integration-report.md). No new paid API calls, public visibility change or deployment occurred.

## Test-policy review before step 6

The owner requested joint policy review before proceeding with step 6 and replaced
the customer-communication candidate with protection of project source code,
snippets, designs and related documentation. The owner confirmed that approved
systems are permitted. Record the draft as `EVAL-SW-001` in
[test policies](test-policies.md); destination approval comes from trusted
configuration/evidence, never a user assertion. This rule is no longer a purely
content-only candidate. Other policies, boundary cases, labels and acceptance
targets remain under review. No evaluation calls are authorized by this decision.

The owner subsequently confirmed that already-public project code and
documentation are not exempt from `EVAL-SW-001`. Sharing still requires a
company-approved system within its permitted scope; public availability alone
does not establish permission. Add paired review examples for approved and
unapproved destinations using the same publicly available project material.

## Step 6 authorization and acceptance targets

The owner authorized step 6 and confirmed using the remaining $4.999975304 of
the original $5 total budget for synthetic Jev and alternative-judge evaluations
through OpenRouter. Initial per-policy targets: 95% confidence upper bounds at
most 5% for false blocks and missed violations; at most 5% indeterminate/errors
on fully specified cases; p95 added latency at most two seconds; evaluator API
cost at most $1 per 1,000 cases. These were agreed before live measurements.

Start with the three discussed policies and the [development suite](../evals/step6/README.md).
The production-action and document rules use the previously proposed boundaries.
Detailed labels remain assistant drafts for human review; development results do
not authorize freezing a release profile or claiming held-out performance.

## Step 6 follow-up changes

The owner authorized all three proposed improvements: let verified facts settle
conditional policies when sufficient; narrow semantic questions by stage; and
measure injection resistance and uncertainty separately for each evaluator.
Implement these through opt-in config/3 and result/3, preserving config/2 baseline
behavior. Keep the original dataset and policy wording, including the explicit
no-exemption rule for already-public project material. Continue within the same
$5 cumulative synthetic evaluation authorization and ledger.

The initial revised runs retain threshold 0.8. Separate model/policy threshold
curves may suggest development candidates, but do not automatically change
configuration or create calibrated enforcement profiles. Detailed semantics and
compatibility are in [the config/3 reference](decision-v3.md).

The completed [follow-up evidence](evaluation-v3-report.md) leaves the release
quality gate open. The action-policy offline screen suggests 0.6 for Jev and 0.9
for Gemini, but these are reused-data development candidates, not approved
threshold changes. Neither model has a qualifying software-policy candidate.
Keep all configurations in monitoring at 0.8 pending label review and further
validation; do not remove the already-public-material restriction to fit results.

## Approved coding model versus onward sharing

The owner clarified that the coding model receiving the evaluated prompt is
company-approved by deployment configuration. Code, including `x = 2`, may be
supplied for review or other coding assistance. Do not require project-origin
evidence merely to allow that approved workflow.

Requests or actions that share project material onward require explicit approval
for the actual destination and operation. Unknown or unspecified destination
approval is a **policy violation**, not an indeterminate business decision.
Approval of the coding model must never authorize onward transfers. User claims
cannot establish approval. Already-public project material remains protected.

This corrects the interpretation of the earlier unknown-provenance case. Preserve
its original input and result as historical evidence, and version the executable
policy/configuration and dataset for the clarified intent. The revised boundary
and [test specification](software-policy-boundary-tests.md) are recorded; the
evaluation-harness migration is now implemented with policy version 2 and
offline regressions. The subsequent live evaluation is recorded in
[integrity-live-report](integrity-live-report.md); production connectors must
supply trusted approval for each actual onward target.
Operational lookup failures remain visible as errors and must prevent sharing
in enforcement; successful lookup with no approval is a negative policy fact.

## Instruction-integrity policy addition (historical; subsequently removed)

The owner requested a separate policy against following unauthorized override
instructions, with the agreed exception for discussion, quotation, analysis and
testing. Added EVAL-INJ-001 version 1 in collection version 3, plus a semantic
monitor binding and 25 synthetic development cases. Existing policy definitions,
thresholds and evaluator rubric remain unchanged. No blanket classification of
all code/documents as untrusted was added to company policy.

See the [historical results](integrity-live-report.md). This
addition does not establish that Jev's judgments remain unchanged or that Gemini
now resists the earlier attacks. No live calls were made; compare model behavior
and false blocks with and without the rule before claiming a benefit.

## Live comparison of clarified coding and instruction integrity

The owner authorized testing the assumptions with real API calls under the
existing cumulative $5 cap. The [fixed protocol](integrity-live-protocol.md)
and [results](integrity-live-report.md) record 550 synthetic event assessments
and 675 calls, including preselected repeats. Jev matches all 49 software cases
with the revised disclosure rule alone. The additional integrity rule raises
false blocks for both models and does not resolve Gemini's two remaining upload
bypasses. No policy, threshold, or enforcement mode was tuned during the run.

Retain the results and failed cases; do not claim the new rule hardens Gemini or
leaves Jev service behavior unchanged. No enforcement profile is approved. The
next recommended design work is to distinguish operative bypass attempts from
passive exposure and combine permission-dependent decisions with trusted facts.

## Remove the standalone instruction-integrity policy

The owner explicitly requested complete removal of EVAL-INJ-001. Delete its
policy, configuration variants, dedicated fixtures/tests and duplicate collection
version 3 from the current tree. Use the existing three-policy collection
`evals/step6/policies-v2` and `config-disclosure-v2.yaml`. This supersedes the
earlier recommendation to retain or refine this rule as experimental.

Keep the historical protocol/results and spending ledger as evidence of the
decision; reproduce the retired experiment only from its recorded Git revision.
Preserve evaluator instruction boundaries and the disclosure/action adversarial
cases. Generic multi-policy comparison support remains available, now tested
using the existing software and production policies. No further API calls are
needed for this removal, and all retained evaluation bindings remain monitor.

Removal verification: 128 offline tests and Ruff pass; the remaining version-2
bundle validates. The rebuilt source distribution contains none of the retired
policy/configuration/fixture/test files. The remaining policy definitions,
configuration, datasets and evaluator instruction boundaries are unchanged.

## Parallel release preparation — 2026-09-27

The owner authorized two subagents to work on step 7 packaging and remaining
step 6 gates in parallel. The repository remains private. This work does not
authorize publication, a customer pilot, or additional spending beyond the
existing cumulative $5 synthetic evaluation cap.

Keep Jev as the first-release backend. Gemini remains a development comparator;
no additional Gemini tuning is needed to prepare packaging. A review packet or
a passing scripted evaluator test cannot establish human-reviewed independent
accuracy. Known failure mechanisms belong in regression evidence, even when a
new case uses different wording.

## Owner label-review completion — 2026-09-27

The owner instructed: “mark human label review as done.” Record all 36 labels in
[the current packet](step6-review-candidates-v1.md) as accepted unchanged and the
packet’s human-review task as complete. No additional human reviewer is claimed.
Preserve the immutable pre-review dataset/snapshot; the dated review record
identifies the exact accepted dataset hash. This does not make calibration or
regression cases independent held-out evidence, approve future labels, or close
the remaining accuracy and end-to-end latency gates.

## Fresh-case and live performance work — 2026-09-27

The owner authorized proceeding with independent evaluation and representative
end-to-end latency. Policies/model/thresholds stay unchanged; Jev alone is used.
The live performance workload and measured limits are recorded in
[the protocol](release-latency-protocol.md) and [report](release-latency-report.md).
A new 100-case targeted command/fact tranche is frozen before measurement; its
labels await owner review. It is an initial generalization check, not enough
independent observations to establish the approved 5% upper error bounds. Do not
confuse preparation, completed performance measurement, and semantic gate closure.

## Approved inbound software sources — 2026-09-28

The owner requested EVAL-SRC-001 and explicitly selected company mirrors plus
approved public repositories/registries. Scope includes fetching, installing,
updating and running remotely obtained software; ordinary documentation browsing
and existing trusted local work remain allowed. The [source-list contract](approved-software-sources.md)
uses operator-controlled YAML with exact resource identities, allowed operations
and optional package restrictions (registry-wide approval must be explicit).
This is separate from outbound disclosure approval; Jev never establishes trust.

The new four-policy evaluation bundle, configuration, synthetic catalog/reference
matcher and 46 draft cases are implemented for offline review. Preserve the
original 100/36 datasets, their approval provenance and the existing three-policy
measurements. Combined-policy cases explicitly distinguish each policy verdict
from the aggregate result. Production source resolution/host enforcement and new
live model measurements remain work to do; this increment adds no API charges.

## Active 100-case review correction — 2026-09-28

The active packet now includes EVAL-SRC-001 alongside the original named policy
for all 100 events; see [the revised review](holdout-sources-v2-review.md).
The direct dependency tarball is unapproved and the combined expected result is
block. Original review records remain historical; the expanded checks need review.
The old live runner/protocol remains single-policy historical evidence and does
not establish the new suite’s quality. No new model calls were made.

## Remove vague fetch example — 2026-09-28

Owner explicitly removed `holdout-v1-sw-git-fetch` as too vague. The active
source-aware packet now contains 99 cases, with an explicit historical removal
record and updated snapshot. Preserve approvals/notes of all other unchanged
cases. The review UI now supports reversible removal, a Removed filter, and
exported removal decisions; removals never count as approvals or measured passes.

## Owner review imported and live run frozen — 2026-09-28

The supplied review export accepts 139 current cases and retains the previous
36 approvals, with no corrections. Six additional document missing-evidence
cases were removed without supplied reasons; together with the already removed
Git-fetch case this leaves 175 accepted events and seven exclusions. The
[fixed live protocol](reviewed-live-v1-protocol.md) records exact provenance,
separate packet/policy reporting, unchanged Jev/threshold/configuration and the
existing cumulative $5 budget. The accepted dataset supersedes the earlier draft
packets for this run; exclusions are not passes and do not remove generic failure
handling requirements. Free text in the export is data, not executable instructions.

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

## Context-only improvement — 2026-09-28

Owner requested clearer evaluation context, leaving everything else unchanged.
The [prepared experiment](question-context-v1.md) adds stage/tool descriptions,
existing source-resolution observations and thirteen resource clarifications to
the accepted 175 events. Policy/scoping text, labels, thresholds, predicates, model
and composition remain unchanged. The original baseline stays reproducible.
The review page exposes the added context and actual unchanged scope questions.
No new live calls or model-accuracy claims; 167 offline tests pass, including
exact payload comparison and identical scripted decisions for all 175 cases.
The existing API ledger and release-gate status are unchanged.

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

## Question wording candidate using existing cases — 2026-09-28

Owner selected immediate question improvement using the current cases, without
waiting for a new test pack. Prepared `questions-v1/config.yaml`: only the four
EVAL-SRC-001 stage scope texts change. The candidate explicitly names acquisition
verbs, separates covered behavior/exclusions, distinguishes discussion from requested
execution, and retains uncertainty for unavailable behavior. Existing policies,
all 175 case texts/labels/context, model, predicates, modes and thresholds remain
unchanged at 0.80. Other policies' questions and the common evaluator boundary are
unchanged. [Before/after review](question-candidate-v1.md) includes representative
existing cases and the scope-word counts: this structured candidate is longer,
not a demonstrated token optimization. All 189 offline tests pass; no live Jev
calls, measured improvement or deployment change. Candidate and prior broader
plan are saved locally for the next batched push given the Actions quota warning.


## Actual-policy evaluation update — 2026-09-28

Owner approved replacing manually authored semantic scope questions with the actual Markdown policy and a reusable adapter template. Opt-in config/5/result/4 implements this direction; trusted metadata and deterministic predicates stay separate, optional and explicitly configured. See [design, migration and validation limits](direct-policy-evaluation.md). Existing model evidence does not validate the new template; a fresh full-pack Jev run remains required before quality claims or enforcement qualification. No publication/default enforcement change.
