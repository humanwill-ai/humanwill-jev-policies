# Project brief

> Owner update 2026-10-03: streaming is deferred to a future release. The
> [real-workflow pilot](dogfood-pilot.md) has a private 50-case review packet and
> a local-only next-100-prompt collector. Live evaluation and actual hook
> invocation remain pending; no real-data accuracy or enforcement claim.

> Latest conversation experiment, 2026-10-03: [explicit policy subjects and dual views](conversation-views-v1-report.md)
> restore historical-secret blocks and reduce unexpected combined errors to 7/81,
> versus 9/81 grouped and 19/81 flat. Individual-policy matches regress versus
> grouping (224/270 versus 232/270). Research-only; no runtime adoption or new release.

> 2026-10-03: config/5 gateway questions now clarify abandoned versus active
> conversation requests without dropping history or trusting inline block notices.
> [Conversation inspection](conversation-inspection.md) records passing local tests
> and a [partial live improvement](conversation-v1-report.md): most legitimate
> cancellations still abstain. Streaming remains planned.

> A [research-only structured-context comparison](conversation-structure-v1-report.md)
> now improves legitimate passes to 24/27, with three historical-secret checks
> regressing to uncertainty. Runtime adoption is deferred pending that tradeoff.

> Development update 2026-10-03: the published v0.1.0a1 remains unchanged.
> Non-streaming proposal inspection passes actual LiteLLM/Agentgateway tests;
> MCP pre-execution passes actual-host tests for [LiteLLM](mcp-pre-execution.md)
> and [Agentgateway](agentgateway-mcp.md). These are unreleased additions;
> streaming and broader MCP bindings remain planned.

> Current candidate status and the guide index are in [preview status](preview-status.md).
> The dated sections below retain planning and decision history; older counts,
> profiles and milestone status are superseded by that current summary.

Updated 2026-09-28 · reviewed live evaluation complete; semantic release gate remains open

## Product and target user

Help enterprise AI platform and security teams **bring their own policies, test them against representative work, and apply them across gateways and coding agents**. The company or user supplies the rules. The service should preserve legitimate activity and expose policy violations, uncertainty, and enforcement gaps separately.

This is a companion to [HumanWill Benchmark](https://github.com/humanwill-ai/humanwill-benchmark). The benchmark measures harmful refusals and usefulness; this service provides a way to apply company-defined rules at runtime. It cannot force a downstream model to answer after our adapter allows a request, and it does not replace a provider's own controls. Track downstream refusal separately.

The commercial hypothesis is that portable, testable company rules solve a recurring enterprise problem. Demand, willingness to pay, and comparative advantage remain unvalidated.

## Confirmed owner requirements

- Policies are user/company-authored Markdown files in a folder. A main policy file references other files in that folder or subfolders.
- Every policy has a stable policy ID for later reference.
- The first release includes **LiteLLM, Agentgateway, and a Copilot hook connector**.
- Jev is available through direct TypeSafe and OpenRouter transports. Development and testing use OpenRouter.
- User/group and other contextual metadata are optional, with an easy deployment enable/disable switch. Where policies depend on identity, classification, or destination, combine verified facts with Jev judgments; user claims are not proof.
- Policies about generated answers or actions must be checked at those stages; a prompt check alone is insufficient.
- Aim at companies and large enterprises needing to apply their own policies to agents; maintain the connection to HumanWill Benchmark.

## Recommended first release

Build a small Python package with an offline policy validator/compiler, shared evaluation and decision core, authenticated HTTP service, and hook executable. Use Markdown plus minimal front matter, explicit recursive include lists, one policy per file, and immutable policy/bundle hashes. Keep transport and host translation separate from decision logic.

Gateway scope includes text requests before model invocation and non-streaming generated responses before delivery. Copilot scope includes submitted-text assessment and pre-tool control; provide separate VS Code Local and CLI profiles as required by the owner. Local can stop submitted prompts; CLI configured prompt-hook output cannot block, and both runtimes can fail open on host hook timeouts. Neither is universal Copilot interception. See [current evidence](research.md).

The [optional metadata design](optional-metadata.md) keeps content-only deployments simple, with metadata recommended off by default and independently configurable sources when enabled. Metadata absence does not prevent ordinary content checks. A policy that requires unavailable evidence is indeterminate, not satisfied; known-disabled dependencies must be resolved explicitly before enabling enforcement. Connector authentication remains separate.

Start policies in monitor mode. Enforced policies need explicit evidence requirements, calibrated thresholds, and failure behavior. An error or unsupported action must never silently become a policy pass. Actual enforcement is reported only where host evidence supports it. No human review workflow in v0.1.

Exclude a governance console, billing, multi-tenant SaaS, SSO administration, automatic policy rewriting, multimodal/streaming-output inspection, general policy inheritance, and universal agent coverage. Arbitrary company handbooks need refinement into testable rules; Markdown alone does not make a rule enforceable.

## Alternatives and build-versus-extend

`jev-edge`, LiteLLM's policy integrations, Bifrost Enterprise, and deterministic gateway controls cover parts of this need. The potential distinction is company-owned policy bundles with reproducible tests and consistent interpretation across gateways and agents—not Jev connectivity by itself. [Research and links](research.md) document the alternatives.

The bounded reuse review supports a small independent core for the new Markdown/service/hook requirements. The offline implementation is original; no upstream code or policy text was copied. See [compatibility/reuse findings](compatibility.md). Revisit connector fixtures only where contracts and licensing fit. Avoid turning preliminary research into a long blocker or assuming the benchmark's scoring contract is a runtime enforcement contract.

## Implementation sequence and validation

The [first-release plan](release-plan.md) specifies the folder contract, example files, architecture, connector boundaries, transports, and completion criteria:

1. Implemented: offline loader, validation, policy IDs, snapshots, and preview; see [foundation evidence](foundation-report.md).
2. Implemented: mock evaluation, deterministic decisions, and both Jev adapters; OpenRouter live smoke passed, direct TypeSafe contract-tested; its separate live smoke is optional.
3. Implemented: LiteLLM/Agentgateway service and real runtime enforcement evidence.
4. Implemented: both Copilot adapters; CLI and Local runtime checks pass with documented bypasses. See [evidence](integration-report.md).
5. Private candidate validation, packaging, and comparative evaluation report, followed by a public preview when release gates pass.

Measure false blocks and missed violations separately, with errors, missing coverage, bypasses, latency distributions, and total cost. Test direct/indirect injection and legitimate near-neighbors. The [OpenRouter transport smoke](smoke-2026-09-27.md) and [synthetic semantic development comparison](integrity-live-report.md) have run; independent reviewed holdout evidence is still pending. See [evaluation plan](evaluation-plan.md).

The [public-release roadmap](public-release-plan.md) defines the proposed `v0.1.0a1` evidence gates, licensing/public-content review, installable artifacts, and publication sequence. Target a usable public preview with bounded claims; production suitability for a customer's policies requires further validation.

## Remaining decisions

The three initial policy intentions, remaining-$5 synthetic evaluation budget and initial acceptance targets are recorded. Review proposed labels and choose the project license before publication; corporate data-egress/retention constraints are needed before a customer pilot. These do not block the offline foundation.

Step 6’s [initial synthetic development comparison](evaluation-development-report.md) identifies false blocks and injection-related misses. It does not substantiate enforcement readiness; human label review, development improvements and independent held-out evaluation remain.

## New policy requirement — 2026-09-28

Companies also restrict where agents obtain code, libraries and tools. Add
EVAL-SRC-001 with an operator-owned source allowlist, independently from upload
approvals. The owner confirmed mirrors plus approved public sources and scope
covering acquisition, installation, updates and remote execution, excluding normal
documentation browsing and existing local work. [The design](approved-software-sources.md)
and 46 new cases are available for review; production origin resolution and live
Jev evaluation of this policy are not yet established.

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

Ten short instruction variants were evaluated on 31 selected cases, twice each. Two tie at 38/62 correct outcomes versus 25/62 for a fresh long control; neither resolves all remaining failures. This is targeted development evidence, not full-pack accuracy or release qualification. See [measured results](short-questions-v1-report.md).

## Q05 full-pack results — 2026-09-29

Completed all 175 reviewed cases with the frozen Q05 template: 149 definitive
decisions, all matching event labels; 26 inconclusive results (14.9%), of which
12 were expected and 14 unexpected (8.6% of 163 decidable cases). Fail-closed
would stop 9/79 legitimate requests; fail-open would permit 5/84 known violations
and all 12 expected unknowns. This remains above the initial error target.
No runtime default or release-readiness change. See [full measured results](q05-full-pack-v1-report.md).

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
