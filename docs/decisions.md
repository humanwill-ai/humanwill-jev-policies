# Decisions and open requirements

## Structural conversation experiment complete — 2026-10-03

At frozen `9040a7e`, the original 24 cases plus six boundary controls ran three
times per arm: 180 assessments / 221 paid calls. Only state.content representation
changes; questions, policy text, full content, gates and trusted facts remain
identical. Original cohort: legitimate passes 9→24/27, errors 18→3; violation
blocks 39→36/39 plus three new low-confidence historical-secret errors; no
definitive violation/unknown allows and all six expected unknowns retained.
Six masked disclosure misattributions remain in each arm. Extra controls retain
all 12 violation blocks and three unknowns, but flat legitimate work errors
2→3/3. See [full results](conversation-structure-v1-report.md).

Grouping remains research-only. Test full-payload content-policy handling and
flat fallback when roles are absent before adopting; no threshold relaxation or
automatic further campaign. All 180 results / 221 exact payloads replay; 90 pairs
reconstruct unchanged content and questions. Seven new offline tests pass.
New cost $0.027091554; known cumulative $0.471780128 plus the old $0.01 reserve,
remaining $4.518219872. Ledger 6,661 attempts / 6,660 settled, only historical
index 1830 unresolved. No runtime change, CI, push, deployment, release or streaming.

## Multi-turn live comparison complete — 2026-10-03

At frozen `a0a3980`, 24 synthetic provisional-label conversations × three repeats
per arm produced 144 assessments and 186 paid calls. Only conversation_scope
changed. Legitimate explicit false blocks14→0, errors7→18, allowed6→9 per27;
fail-closed stops21→18. Both arms block39/39 violations and retain6/6 expected
uncertain. Clarified disclosure misattribution on two download cases causes six
wrong policy decisions masked by correct source blocks. One malformed follow-up
was rejected and its charge settled. Keep this as partial development improvement,
not a solved conversation boundary or an enforcement qualification. No tuning or
extra campaign. See [full results](conversation-v1-report.md).

All144 normalized views and186 exact payloads replay;72 primary pairs differ only
by clarification. New cost$0.020388564, known cumulative$0.444688574 plus unchanged
old$0.01 reserve, remaining$4.545311426. Ledger6440attempts/6439settled; only historical
index1830 unresolved. Three experiment tests pass in addition to the294 prior
implementation tests. No hosted CI, push, deployment, publication or streaming.

## Conversation inspection clarification — 2026-10-03

Owner approved addressing abandoned blocked requests retained in gateway history.
Config/5 model-request questions now distinguish active work from abandoned
instructions, retain all content and whole-payload restrictions, and grant no
exemption to inline block/approval claims. The shared clarification survives Q05
and Q04; existing roles/order are used without new status fields or history
rewriting. Legacy questions, other stages, thresholds and enforcement remain
unchanged. All 294 local tests and Ruff pass (nine new contract tests); these use
scripted judgments, not live Jev. See [design and proposed semantic comparison](conversation-inspection.md).
No provider calls, hosted CI, push, publication or streaming implementation.

> Current candidate status and the guide index are in [preview status](preview-status.md).
> The dated sections below retain planning and decision history; older counts,
> profiles and milestone status are superseded by that current summary.

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
| Project license | Prepared for release review, 2026-09-30 | Apache-2.0, matching the owner-proposed Benchmark software license; original software/docs/synthetic examples, with explicit exclusions and third-party notices |

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

**Owner update, 2026-09-30:** defer GitHub Actions runs until immediately before
the final release. Use local validation in the meantime and avoid workflow
dispatches or pushes/PR updates that trigger CI. Reuse the existing Actions
infrastructure for final-candidate Agentgateway, container and cross-platform
checks. This preserves the reported remaining allowance; no fresh account balance
was checked. Required checks remain required, and publication still needs separate
owner approval. This supersedes the earlier suggestion to batch interim CI pushes.

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


## Full-policy live result — 2026-09-28

The authorized full175 Jev/OpenRouter pass completed at d624c9c with unchanged policies, labels, context, model, monitor modes and 0.80 gates. The shared-template path regressed: 142/175 exact events vs166, 228/272 policy outcomes vs260, fail-closed false blocks32/79 vs6, known violations allowed0/84, expected unknowns retained12/12. Raw scope errors12/226 (one malformed response) vs2/227; correct raw choices rejected for low confidence35 vs12. No tuning/reruns. See [full report](direct-policy-live-v1-report.md). Keep the new template experimental and preserve the previous measured path; release quality remains open. Cost $0.010850028, cumulative $0.089128796, remaining $4.910871204. All1560 cumulative evaluation calls settled. One normalized batch lacks usage after answer validation failure; its transport cost is settled and included.


## Applied asymmetric development settings — 2026-09-28

Owner approved applicable0.80 / not_applicable0.70 / insufficient_evidence0.80 and explicitly requested no tests. Applied explicitly in evals/step6/direct-policy-v2/config.yaml and the packaged config-policy-text.yaml demo; frozen v1 and implicit loader defaults are preserved. No tests, replay or API calls performed. Continue human review of the23 remaining legitimate failures identified by the existing offline replay. See direct-policy-evaluation.md and direct-policy-threshold-analysis-v1.md.


## Patch-confidence experiment — 2026-09-28

Owner requested100 live synthetic variations to investigate low confidence. Completed50 distinct requests x2 repetitions,100 calls,200 scope questions at clean65dc823. See [protocol](patch-diagnostics-v1-protocol.md) and [report](patch-diagnostics-v1-report.md). Frozen randomized order, no retries, runtime policies/template/gates unchanged.36 scored diagnostic judgments per condition (new labels provisional), four source-origin judgments unscored: correct accepted baseline15,tool context27,focused question30,concise policy16,concise+focused28. Explicit local provenance helps source confidence but not enough for disclosure; focused restricted-action wording is a more promising next experiment than simply shortening policies. All positive controls accepted. Two malformed responses have probabilities summing0.99; strict current validation retained. Not independent quality evidence or causal proof. Cost$0.008754060; total$0.097882856; remaining$4.902117144; all1660 cumulative calls settled.


## Focused full-policy pass — 2026-09-28

Owner accepted testing the focused question on all175 with brief context where needed. Completed at636cb85: full policies/labels unchanged, active0.80/0.70/0.80 gates, one neutral git-apply note,148 calls with no retries. Against recorded answers replayed at the same gates:156/175 vs151 exact,248/272 vs242 policy matches,14/79 vs23 fail-closed false blocks,0/84 known violations allowed,12/12 expected unknowns retained.13 fixes and8 regressions; disclosure improves but source/production policy results regress. Git-apply passes with source confidence0.77/disclosure0.93. Keep candidate experimental; no runtime template promotion. See [report](focused-policy-v1-report.md) and [protocol](focused-policy-v1-protocol.md). Run cost$0.010737426,total$0.108620282,remaining$4.891379718; all1808 cumulative calls settled. No malformed responses in this pass, strict validation unchanged.


## Clarified absence versus missing evidence — 2026-09-28

Owner requested clarifying the experimental generic question and reviewing the other12 legitimate evaluation errors. Added focused-policy-v2/question.json and opt-in clarified_question.py, preserving frozen v1 and runtime defaults. The task and answer criteria now explicitly choose not_applicable when no covered action/instruction is present, and reserve insufficient_evidence for missing information about a potentially relevant action. No policy/context/threshold changes or API calls. Saved-answer review:3 of the other12 are strong matches to this hypothesis (ordinary document text), while9 involve local transformations(2), command effects(5), or quotation/negation(2). This is qualitative diagnosis, not proven internal cause or a measured fix. See [case-by-case review](clarified-question-and-error-review.md).


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

Keep all ten short instruction variants experimental. Q05 is the most balanced candidate for future full-pack validation; Q02 improves the five difficult cases more but regresses controls. Policies, thresholds and runtime defaults remain unchanged. See [measured results](short-questions-v1-report.md).

## Q05 full-pack results — 2026-09-29

Completed all 175 reviewed cases with the frozen Q05 template: 149 definitive
decisions, all matching event labels; 26 inconclusive results (14.9%), of which
12 were expected and 14 unexpected (8.6% of 163 decidable cases). Fail-closed
would stop 9/79 legitimate requests; fail-open would permit 5/84 known violations
and all 12 expected unknowns. This remains above the initial error target.
No runtime default or release-readiness change. See [full measured results](q05-full-pack-v1-report.md).

## Proposed abstention-improvement experiment — 2026-09-29

[The bounded improvement plan](abstention-improvement-plan-v1.md) targets unexpected
abstention on decidable cases, preserving deliberate uncertainty. It proposes
Q05 plus one stage-aware secondary assessment, with policy clarification as a
separate fallback experiment. Saved-answer screening does not demonstrate the
5% target yet. No new live calls or runtime changes were made for this proposal.

## Policy-isolation experiment — 2026-09-29

Three fresh full-pack passes compared identical Q05 retry, isolated Q05 and
isolated Q04 after a shared primary. Isolation alone gave little improvement.
Isolated Q04 reduced unexpected abstention to 4.9%, 6.1% and 5.5%, with no wrong
accepted event/policy outcomes and all expected unknowns retained. This is promising
follow-up evidence, not a consistently met 5% target or proof that isolation causes
the improvement. No classifier, policy change or runtime adoption. See
[full results](policy-isolation-v1-report.md); discuss the next experiment before proceeding.

## Q04 follow-up comparison — 2026-09-29

Three paired passes of the 175 reviewed cases plus 24 provisional fresh workflows
are complete at frozen source `03c72bb`. Reviewed unexpected errors per 163 cases:
Q05 15/15/15, full-batch Q04 10/9/10, isolated Q04 11/10/10; pooled rates are
9.2%, 5.9% and 6.3%. Fresh errors per 20 decidable cases: Q05 1/3/2, both
follow-ups 1/2/1 (6.7% pooled). No wrong definitive event or policy decisions;
all expected unknowns preserved. Fresh labels are model-authored and pending
review, not independent qualification. Prefer bounded full-batch Q04 as the
simpler next implementation candidate; isolation has no demonstrated advantage
and the 5% goal remains unmet. See [full report](q04-comparison-v1-report.md).
624 calls cost $0.037072056; known total $0.260080178 plus the historical $0.01
reservation, leaving $4.729919822. All new charges settled. No runtime, classifier,
policy, threshold or release change, and no push. Experiment complete;
no automatic additional campaign.

## Bounded Q04 runtime implementation — 2026-09-29

Owner authorized implementing the full-batch follow-up. Config/5 now supports
`policy_assessment: q05_q04`: Q05 first, at most one Q04 call for eligible
low-confidence scope answers, with unchanged gates, trusted metadata checks and
error fallback. Existing configurations retain their behavior. Result/4 includes
normalized primary/secondary evidence and usage for both attempts. See the
[runtime contract](bounded-policy-followup.md) and [verification](bounded-policy-followup-verification.md).
231 offline tests and 12 Python 3.11 focused tests pass; all 597 saved event views
replay exactly across 569 recorded payloads. Exact wheel/source artifacts pass
isolated installation, connector contracts and service process checks. No new
paid calls or interactive/live-host acceptance test. Semantic release gates and
the 5% target remain open; no deployment, publication or push.

## Small tool-classification probe — 2026-09-30

The owner-requested diagnostic tested ten previously failing tool-action cases plus
six controls, twice each, at frozen source `5518daa`. On 20 focus observations:
Q05 primary left 19 unresolved, Q04 left 17, explicit tool wording left 13, and
classifier-informed tool wording left 14. No wrong accepted event/policy decisions;
all control outcomes and expected unknowns retained. Classification added no unique
recovery. Prefer broader validation of tool-specific wording for known tool_action
stages before considering adoption; no runtime change or general error-rate claim.
See [full results](tool-probe-v1-report.md). 124 calls cost $0.007679826; known
cumulative spend $0.267760004 plus historical $0.01 reserve, remaining $4.722239996.
One classifier answer was malformed and rejected with its charge settled; no new
unknown charges. All exchanges and compositions audited; no push or further campaign.

## Full-pack tool wording comparison — 2026-09-30

The authorized three-pass comparison of all175 reviewed cases completed at frozen
`03f9a03`. Q05→Q04 unexpected errors:10/8/11 per163; stage-routed tool wording:
8/6/9. Pooled5.9%→4.7%, with9 paired recoveries and3 regressions to uncertainty;
no wrong definitive event/policy outcomes and all36 expected unknowns retained.
Same call count per strategy, no classifier, policies/gates/context unchanged.
The third pass remains5.5%, so consistent5% and independent release qualification
are not established. Recommend an optional stage-aware runtime profile next;
production currently remains Q05→Q04. See [full report](stage-tool-v1-report.md).
523 calls cost$0.031272024; known total$0.299032028 plus historical$0.01 reserve,
remaining$4.690967972. Two malformed primaries rejected/settled, no new unknowns.
All523 payloads/1575 views audited;11 focused offline tests and Ruff pass. No
publication, deployment, push, or automatic further campaign.

## Optional stage-aware runtime profile — 2026-09-30

Owner authorized `policy_assessment: q05_stage_aware` in config/5. It uses Q05
first, then at most one tool-specific scope follow-up on normalized tool_action
stages, Q04 elsewhere. Existing profiles and defaults remain unchanged. No
classifier, command-specific routing, policy selection or threshold changes.
Preview and result/4 profile enum are updated; upgrade strict clients with the
service. See [activation and contract](bounded-policy-followup.md) and
[verification](stage-aware-followup-verification.md). Full offline suite253 passed,
then all17 focused tests passed on Python3.14/3.11;1050 recorded event views and970
payloads replay exactly across both campaign arms. Wheel/source isolated install,
profile/connector and service process checks pass. This is implementation evidence,
not a new live host/model test or release qualification. No API calls, deployment,
publication or push; remaining API authorization unchanged at$4.690967972.

## Active test-pack removal — 2026-09-30

Owner removed `candidate-v1-response-outside-session` as confusing. Future campaigns
must use `evals/step6/release/active-pack.json`, pointing to reviewed-v2 with174
unchanged remaining cases. The review UI marks the case removed, including migration
of saved approval, and shows35 active cases in the prior36 packet. Historical
175-case datasets, frozen protocols and reports remain intact; no accuracy gain
is claimed from removal. No local tests or API calls were run, as requested.

## Local-machine policy clarification — 2026-09-30

Owner approved EVAL-SW-001 v3: unless company policy or trusted configuration
specifies otherwise, the local machine and local temporary directories are
authorized for project work. Local copying/rendering/encoding/transformation
without onward disclosure is permitted; resulting material remains protected
when shared. Local authorization does not approve network-backed/synchronized
sharing. Active manifest now pairs reviewed-v3 (174 unchanged requests/labels,
updated software policy-version references) with policies-sources-v2. UI displays
the revised policy and preserves prior review progress. Frozen historical policy
bundles, datasets and measured reports remain unchanged. No tests/API calls run;
Jev behavior with this clarification is unmeasured.

## Local-policy targeted rerun — 2026-09-30

Owner-requested live rerun completed at99b630a: eight remaining tool failures×3,
actual q05_stage_aware runtime and active disclosure policyv3. Copying/rendering
allow3/3 each on first Q05 at confidence.97–.98; patch still errors on unchanged
source policy. Targeted errors20/24→13/24; five distinct cases still abstain,
alllowconfidence. No wrong definitive event/policy answers or malformed replies.
Gitclean3/3block; its inputs were unchanged, so do not attribute its recovery to
the policy edit. No full174-case quality claim. See [report](local-policy-rerun-v1-report.md).
41calls cost$0.003006066; known total$0.302038094+old$.01reservation,
remaining$4.687961906. All41payloads and24runtimeviews audited; allnewcharges settled.
No full localtests, extra campaign, deployment, publication or push.

## Patch-origin clarification and rerun — 2026-09-30

Owner authorized EVAL-SRC-001v2 clarifying locally produced patches as ordinary
editing, while third-party incorporation still requires source approval. Local
storage alone does not approve origin. Active manifest now reviewed-v4 plus
policies-sources-v3 (174unchanged requests/labels, updated source-version refs).
UI displays the new policy and preserves prior saved progress. Patch-only live
rerun at1501bca still errors3/3: primary applicable confidence.14/.04/.14; follow-up
insufficient_evidence.10 each, rejected asstill_indeterminate. Context still leaves
origin unestablished; label remains allow for comparison, no provenance invented.
See [report](patch-policy-rerun-v1-report.md).6calls cost$.000502236; known total
$.302540330+old$.01reserve, remaining$4.687459670. All6payloads/3views audited;
no newunknowns, broad localtests, extra campaign, deployment, publication or push.

## Existing local patch exemption passes — 2026-09-30

Owner authorized replacing “locally produced” with an exemption for applying any
existing local patch without re-establishing origin; fetching/downloading remains
governed. EVAL-SRC-001v3 in active policies-sources-v4/reviewed-v5 (174unchanged
requests/labels, source-versionrefs3). Patch-only rerun at06f2eea allows3/3 onfirst
Q05, source confidence.97/.98/.98, nofollowup; disclosure also passes. Context and
allotherinputs unchanged; no invented provenance. See [report](patch-policy-rerun-v2-report.md).
3calls cost$.000239400,known$.302779730+old$.01reserve,remaining$4.687220270.
All3payloads/3views audited. No fullpack/othercases/broadlocaltests/browserchecks/
deployment/publication/push. Full-pack regression behavior remains unmeasured.

## Four command cases removed — 2026-09-30

Owner explicitly removed these four cases from the active evaluation pack:

- `holdout-v1-prod-dry-run-rsync`
- `holdout-v1-prod-terraform-plan`
- `holdout-v1-prod-ansible-check`
- `holdout-v1-prod-kube-replace-force`

The active manifest now points to reviewed-v6: **170 cases**, with the unchanged
policies-sources-v4 bundle. Remaining requests and labels are unchanged. Historical
datasets, failures and measured rates remain intact; removing known failures is
a scope/selection change, not improved accuracy. The review UI hides them from
active review and retains them under Removed. No tests or API calls were run.

## Public-release preparation — 2026-09-30

The owner requested the next release-preparation step and proposed matching
HumanWill Benchmark's license. Its software license was verified locally and
through GitHub as Apache-2.0; the separately licensed benchmark content was not
imported. Prepared LICENSE, NOTICE, LICENSING.md and package license metadata use
Apache-2.0 for this project's original software, documentation and synthetic
examples, preserving third-party and company-input rights. The owner selected
email security reporting and supplied sergio@humanwill.ai; SECURITY.md uses that
address. No mailbox access or response SLA was verified or promised.

See [public-release preparation evidence](public-preparation-report.md) for local
history/log scans, notices, dependency inventory, artifact validation and limits.
Actions remains deferred until final-candidate validation. No visibility change,
workflow dispatch, push, tag, release or deployment is authorized by this work.


## Final candidate hosted validation — 2026-10-01

Owner requested proceeding with the postponed GitHub checks at release-preparation
step 5. Run the existing core matrix and pinned host integrations with one batched
private push, retaining exact packages and container package/license inventory.
Local preflight passed 254 tests. This authorizes validation now, not public
visibility, release publication, billing changes or Actions overages. No paid
model calls are needed. Final results and publication approval remain pending.


Final result: all seven jobs passed at `5b1786b` without reruns. See
[final CI evidence](final-ci-report.md). Record the result with a documentation-only
follow-up that skips redundant CI; exact retained packages remain tied to the
tested commit. No provider spending, billing changes, public visibility change,
tag or release. The next step is concrete publication approval.


## Controlled latency comparison — 2026-10-01

Owner authorized separating prompt-only, prompt/response and natural follow-up
latency after reviewing the historical ~500ms versus ~1.8s results. Frozen0436c05,
current runtime/policies/gates unchanged. See [report](latency-paths-v1-report.md):
117requests,141calls,$0.013086738, no new unknowns. Meaningful prompt-only p95
470ms; two-call code-review p95 1,454ms; three-call warning subgroup p95 1,168ms.
All13warning and13placeholder response assessments error; monitoring permits
HTTPdelivery. These are measured paths, not a performance optimization, coverage
recommendation or independent accuracy result. README security/latency clarified;
no runtime change, CI push, deployment or publication. Remaining$4.631633144,
including unchanged historical$0.01 reservation in accounted spend.


## Multi-question experiment rejected — 2026-10-01

Owner authorized testing Q05/Q04/tool-specific questions together, with a runtime
refactor only for exceptional success. The frozen experiment at fcd9c2b compared
188 cases twice per arm (170 reviewed, 18 provisionally labeled fresh cases).
See [report](fanout-v1-report.md). Unexpected abstentions increased from 1/346 to
4/346 decidable observations; no paired event recoveries and three regressions.
No wrong definitive combined outcomes, but fresh individual-policy disagreements
were 1 control / 2 candidate, masked by correct blocks from another policy.
Overall evaluator p95 was 518/498 ms; follow-up-subset p95 was 853/2539 ms.
Candidate cost was 2.21 times control. Exceptional-success gates failed: retain
current sequential q05_stage_aware, with no runtime refactor or automatic retuning.

All 752 event views and 645 exact payloads were replay-audited. Six focused offline
tests passed before measurement. Cost $0.065933154; known cumulative $0.424300010
plus unchanged historical $0.01 reservation, leaving $4.565699990 of the $5 cap.
No new unknown charges. Research files and reports only; no CI, push, deployment
or public visibility change. Continue the existing experimental-preview release
path; independent qualification and concrete publication approval remain separate.


## First public prerelease published — 2026-10-01

Owner explicitly approved the concrete release and instructed making it public.
Published GitHub prerelease v0.1.0a1 at 3f086c0ec102b202d8150cf42739baf1ad62047e,
with all six approved assets and notes. Anonymous access/clone, exact downloaded
checksums and fresh Python 3.11 wheel installation/offline demo pass. See
[publication record](publication-v0.1.0a1.md). The repository is now public; prior
private/unpublished statements are dated history. Runtime, policies, thresholds
and monitoring defaults remain unchanged. No new CI/provider spend, deployment,
PyPI/container upload or announcements. Main documentation may record publication;
do not move the published tag or replace its approved assets. Qualification remains
open and separate from this experimental developer preview.


## Next feature sequence saved — 2026-10-01

Owner requested saving the discussed sequence as the next action plan:
structured tool-call inspection for non-streaming gateway requests/responses,
then MCP pre-execution enforcement, then streaming with tested buffering and
blocking. See [the plan](next-action-plan.md) for coverage boundaries and exit
evidence. Streaming is distinct from tool-call support. No implementation, test,
paid call, deployment or release was initiated by this planning update.


## Non-streaming tool-call implementation — 2026-10-02

Owner authorized step 1 of the saved plan. Add opt-in LiteLLM and Agentgateway
relay profiles in development version 0.1.0a2.dev0; retain the released text-only
profiles. Agentgateway v1.5.0 reduces webhook messages to role/text, so parsing
its webhook cannot establish tool coverage. Use a fixed, authenticated backend
relay instead, with bounded non-streaming bodies, no client route overrides or
redirects, and withheld output until response and individual action checks pass.
The owner was offered this relay versus deferral; absent a preference during the
independent LiteLLM work, proceeded with the stated recommended relay approach.

Definitions/history stay model-request context; each new call gets independent
trusted evidence resolution. Existing policies, semantic gates and follow-up
logic remain unchanged. No new API calls, host CI, push or release. See
[setup and verification](structured-tool-calls.md). Local real LiteLLM and relay
checks pass; actual Agentgateway relay acceptance remains an open Linux host gate.

## Agentgateway relay accepted; MCP execution binding — 2026-10-02

Owner approved actual Agentgateway validation followed by MCP implementation. One
targeted existing-workflow dispatch at `dabbbfb` passed 26 relay and 22 text
scenarios through Agentgateway 1.5.0; no duplicate jobs or paid provider calls.
[Evidence](evidence/agentgateway-tool-calls-ci.json) records the run and hashes.

The first MCP binding targets a dedicated LiteLLM 1.102.1 gateway. Its mandatory
pre-execution callback sends full arguments and resolved server context to the
existing native policy endpoint. Company metadata remains optional and separately
verified; server names/claims do not grant permission. No policy, evaluator,
threshold or follow-up changes. Existing proposal inspection is not disabled.

Actual local MCP server tests pass 18 scenarios with side-effect assertions; four
installed callback tests and 279 offline tests pass. Initial development testing
exposed LiteLLM skipping a ValueError-invalid guardrail while starting the proxy;
the final connector raises fatal configuration errors, verified for disabled mode
and missing credentials. This does not protect a deployment where the guardrail
is removed entirely or a later hook mutates arguments. Full setup, precise failure
behavior and exclusions are in [the MCP guide](mcp-pre-execution.md). No streaming,
new release, hosted MCP CI or live semantic/latency campaign.

## Agentgateway native MCP connector — 2026-10-03

Owner authorized implementation after LiteLLM MCP acceptance. Agentgateway 1.5.0
has a native ExtMCP request-phase interface exposing the resolved target and full
arguments before forwarding. Use a small authenticated loopback gRPC processor
that reuses the native HTTP policy service; do not introduce another traffic relay.
Only tools/call request checks, explicit target allowlist, fail-closed transport,
no mutations/retries, optional independently trusted metadata and existing policy
monitor/error decisions. Generated upstream protocol bindings and two optional
runtime dependencies are documented with preserved licenses.

285 local tests pass on Python 3.11, including six real gRPC wire tests. The exact
Agentgateway configuration passes the v1.5.0 schema. Actual Linux host validation
is the next gate; use one targeted existing-workflow dispatch and retain its wheel
and reports. No new provider calls, streaming or release. Setup and scope are in
[the Agentgateway MCP guide](agentgateway-mcp.md).

### Agentgateway MCP runtime acceptance

The single targeted run [37107052703](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/37107052703)
passes at `9ab0862`: 22 new MCP scenarios, all 48 existing Agentgateway scenarios,
and six gRPC wire checks. Other jobs skipped. Exact installed CI wheel and reports
were retained and downloaded; runtime files match the reviewed source.
[Evidence](evidence/agentgateway-mcp-v1.json) records hashes and every MCP result.
Local wheel/source installation checks also pass. No paid provider calls,
representative MCP latency benchmark, new main merge or release. The guide's
previous pending gate is now closed for this pinned native HTTP MCP profile.


## Explicit policy subjects experiment — 2026-10-03

Owner authorized the proposed dual-view experiment. Completed at frozen cd8f5a8:
30 unchanged synthetic conversations × three repetitions × three fresh arms,
270 assessments / 317 calls. Operator-owned research configuration assigns
current_operation or whole_payload explicitly; candidate retains flat content
and adds lossless groups with per-question subject instructions. No-role inputs
remain identical to flat. No classifier, label routing or runtime schema change.

Unexpected combined errors among81 decidable observations per arm: flat19,
grouped9, candidate7. Historical-secret block restored3/3 at confidence0.99;
all51 known violations blocked and9 expected unknowns retained. Legitimate passes
11/30→24/30→23/30: candidate has six low-confidence errors in two cases plus one
malformed local-build reply. No new definitive wrong outcomes, but policy matches
232→224/270 versus grouping: masked source uncertainty and the malformed batch.
Keep research-only; combined gains do not establish independent qualification or
a consistent5% target. See [complete report](conversation-views-v1-report.md).

Seven focused tests/Ruff pass; all270 results/317 payloads and charges audited.
Run cost$0.040052460; known$0.511832588 +old$0.01 reservation =accounted$0.521832588,
remaining$4.478167412.6978attempted/6977settled,only historical1830 unknown.
No runtime adoption, threshold change, push, Actions, deployment, release,
streaming or automatic next campaign.


## Real-workflow pilot prepared — 2026-10-03

Owner postponed streaming and approved preparing a 50-request historical replay
plus monitoring the next100 prompts. Extract only this project's native user text
and earlier final assistant replies, maximum5messages/10kcontentbytes, excluding
internal instructions/tools/attachments and all future text. Active private packet
hash47359eb36f453a3961dbd6ec654eab3fa387fc2530d8bcfb75fef8c231c568f2;
all50 labels pending human review before Jev results. No live calls.

Use existing SW/SRC policies and gates, actual current evaluator, monitor only;
explicit partial coverage, no research dual-view adoption. Operator-owned source
list awaits owner decision. Reviewed per-event authorization stays separate from
labels; unknown facts remain unavailable, no synthetic fixture permissions reused.
A one-run, input/source-bound real-data egress receipt is prepared inactive, with
proposed additional$.10 within existing$5; no authorization inferred from exports.

Project-local async capture hook installed, current-session only, maximum100,
private files, no network/blocking/context injection. Actual editor invocation
and trust remain unverified; no trust bypass. This is collection setup, not
active continuous Jev assessment. Seven offline tests/Ruff/JS syntax pass; active
packet secret scan zero matches, no visual browser check available. See
[setup, pending steps and coverage](dogfood-pilot.md). No API spend/push/CI/release.

## First private workflow replay completed — 2026-10-03

Owner's “yes, proceed” authorizes the exact real-data historical 50-case packet,
OpenRouter→TypeSafe, at most $0.10 additional. With no owner review export, preserve
pending labels and freeze separate assistant-provisional expectations before answers.
Do not imply human approval or authorize future automatic real-data egress.

At source7950bd7, unchanged runtime/policies/gates:30allow/20error/0block;18lowconfidence,
1missingmetadata,1malformed primary. Q04 ran19times and resolved1wholeevent;69calls
settled, exact50results/69payloads replay-audited. Median438ms,p95 858ms;cost$.008785896.
See [report](dogfood-history-v1-report.md). This is a friction signal, not a malicious
request detection measurement. All50 provisional expectations allow; no causal or
independent accuracy claim. No post-result tuning, extra live campaign or publication.

Known total$.520618484 plus unchanged historical$.01 reserve;remaining$4.469381516;
7047attempted/7046settled, onlyold1830unknown. Private full results HTML and raw
artifacts remain ignored. Future hook still unobserved; source catalog answer pending.

## Grouping-only real-workflow comparison — 2026-10-03

Owner explicitly authorized step1, comparing existing grouping to runtime, not
implementing it again or adopting policy-subject changes. At815d46f, same50private
cases+30existingcontrols,2freshpasses/arm,320assessments/415calls, no semantic input
or gate changes. Workflow42/100abstentions flat→28/100grouped; grouped36allow14error
on each50-casepass.15pairedfixes/1regression; reductionone-third misseshalvingtarget.
Synthetic34violations:flat34block,grouped32block2error; historicalsecretconfidence
0.89/0.91→0.64/0.73 causesbothregressions. Noexplicitviolation/unknownallows, but
fail-openwouldpermitthesecontrols. Keep research-only; no automaticnextcampaign.
See docs/dogfood-grouping-v1-report.md. All320results415payloads replayaudited,
160primarypairs differonlylosslessrepresentation.15focusedtests pass.
Cost$.052238172, allsettled;known$.572856656+old$.01reserve=accounted$.582856656,
remaining$4.417143344;7462attempted7461settled,onlyold1830unknown. No push/CI/release.

## Policy-target workflow comparison — 2026-10-03

Owner authorized existing explicit policy subjects plus full content. At69689b3,
50 unchanged private cases +30 safety controls, two passes of three fresh arms:
480 assessments,609 paid calls. Workflow errors: flat40/100, grouped30/100,
candidate35/100 (17/50 and18/50). Candidate improves flat slightly but regresses
against grouping; two errors are predeclared size-limit rejections of025, no calls.
Historical-secret confidence recovers0.99/0.99, restoring both lost blocks; all34
known violations block in candidate/flat, grouped32block2error. Candidate policy
matches150/180 versus grouped152, including masked source uncertainty. No definitive
violation/unknown allows. Keep experimental; no automatic next campaign/adoption.
All480results609payloads replay-audited,318 primary transform comparisons plus two
limit rejections verified.22focused tests pass. See docs/dogfood-views-v1-report.md.
Cost$0.082725846;known$0.655582502+old$0.01reserve=accounted$0.665582502,
remaining$4.334417498;8071attempted8070settled,onlyold1830unknown. No push/CI/release.

## Compact policy-target comparison — 2026-10-03

Owner authorized grouping+explicit targets without duplicated content. At6035354,
50sameprivate+30controls,2passes/3fresharms=480assessments583calls. Compact places
complete grouped history once in state.content; both target kinds refer to it,
meanings/permissions/policies/gates unchanged, previous no-role flat fallback retained.
Workflow:compact27/100errors (12/50,15/50),grouped28,dual36; no explicit false blocks.
Compact fixes3/regresses2 versusgrouping,fixes10/regresses1 versusdual. All34violations
blockcompact/dual,grouped32block2error;historicalsecretconfidence.99bothcompactpasses.
Individual-policy matches151/180compact anddual versus153grouped; maskederrorsremain.
Keep compact as researchcandidate, not default:15distinctunresolved workflowrequests,
frictiontarget unmet. Matched primary inputtokens21.6%lowerthan dual,workflowcost22.5%
lower,no compactsizeerrors. Report docs/dogfood-compact-v1-report.md;480results583payloads
replayaudited,318transformpairs+2dual sizerejections verified;25focusedtests pass.
Cost$0.080854536;known$0.736437038+old$0.01reserve=accounted$0.746437038,
remaining$4.253562962;8654attempted8653settled,onlyold1830unknown. No push/CI/release.

## Owner review: preparation for publication is governed — 2026-10-03

Owner confirmed preparation itself can introduce risk and must not proceed without
approval, even when publishing is a later step. Existing approved-system exceptions
remain scoped to the actual destination and preparation/disclosure operations.
Case008's previous provisional allow was too narrow; Jev's applicable0.82/0.84 is
consistent with the clarified scope. Recorded missing facts still imply evaluation_error,
not an explicit block; require fail-closed to prevent work. Monitor did not block it.

New EVAL-SW-001v4 bundle evals/dogfood/policies-preparation-v1, collectionv2; original
v3 and all frozen inputs/results remain unchanged. Owner scope review and assistant
runtime mapping are separate in review-decisions-v1.json. Future labels require
scope review before a new protocol; no blanket approval or negative fact invented.
See docs/disclosure-preparation-boundary.md. Bundle/config load checked; no live call,
replay, threshold/runtime change, push or new rate. Fourteen cases remain to review.

## Owner review: gateway integration wording ambiguous — 2026-10-03

Owner accepted015 as ambiguous intent with defensible abstention: intended product
connector feasibility research, potentially read as connecting the development
project and sending data to another gateway. Preserve original inputs/results;
clearer wording would be a separate future example, not a retroactive correction.
Two of15 cases reviewed,13 remain;026 currently under discussion, no label decision.
See docs/dogfood-case-review.md and review-decisions-v1.json. No new calls or tuning.

## Owner review: approved README push should allow — 2026-10-03

Owner confirmed case026 expected allow, conditional on trusted approval covering
the actual repository and complete requested operation. The measurement profile
had predicate_short_circuit disabled, so low scope confidence still caused errors
despite true permission predicates. Record this as decision-flow friction, not a
new model violation finding. A scoped permission shortcut remains an improvement
to consider; no setting was enabled and no threshold changed. Frozen evidence and
rates remain unchanged. Three of15 cases reviewed,12 remain; no calls or push.

## Owner review: public README preparation — 2026-10-03

Owner agreed027 is publication preparation requiring approval in its context,
rather than unconditional local-work allow. Its event has no onward-approval fact.
Recorded v3 result was low-confidence not_applicable/evaluation_error, not a correct
applicable finding; do not claim v4 performance from it. With v4 scope established,
missing metadata still prevents an allow under fail-closed. Frozen evidence unchanged.
Four cases reviewed,11 remain;029 under discussion. No new calls/settings or push.


## Focused context comparison authorized — 2026-10-04

Owner accepted grouped closeout of the15 workflow cases, without individually
approving all labels. See docs/dogfood-case-review.md. Prepare six historical
requests with original earlier discussion, preserving the bounded suffix, v3
policies, questions, gates and metadata. Two fresh arms/two repeats plus30 unchanged
safety controls:144 assessments,288-call ceiling,$0.10 within remaining$5 budget.
Publication-preparation cases005/027 are unscored v3 diagnostics; v4 stays separate.
Only content and explicit partial coverage differ;029 has a declared excerpt gap
to retain the same policy batching under24KB. See docs/dogfood-context-v1-protocol.md.
No runtime adoption, future-capture egress, streaming, Actions or push. Freeze source
and one-use real-data receipt before live calls; preserve old1830 reservation.
