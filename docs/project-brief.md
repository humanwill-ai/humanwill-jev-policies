# Project brief

Updated 2026-09-27 · service/connectors implemented; runtime checks pass; policy-quality validation pending

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
