# Project brief

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
