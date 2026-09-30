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
