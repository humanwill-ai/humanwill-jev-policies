# Project brief

Draft · 2026-09-27 · adaptable, not an approved architecture

## User and problem

**Proposed initial user:** a platform or security engineer responsible for a company's AI gateway and developer tooling. They need to express a small set of company-specific rules, test the rules against real work, and operate them consistently across supported environments without unnecessarily blocking legitimate activity.

**Hypothesis:** a portable service with measurable policy quality and explicit coverage is valuable enough to adopt. Neither demand, willingness to pay, nor Jev's suitability has been validated. Interview prospective users about recent incidents, current controls, workarounds, and budgets before expanding scope.

## Alternatives and potential differentiation

Existing options include gateway-native deterministic controls, LiteLLM's Alice and Conduct integrations, and Bifrost Enterprise's natural-language policy judging. `jev-edge` already provides broad gateway adapters, multiple judging backends, and monitor/enforce operation; its documented fail-open behavior differs from some likely requirements. See [evidence and source links](research.md).

Potential differentiation is **portable company policies with representative tests, measured error rates, and honest enforcement reporting**. Jev connectivity and low advertised token prices alone are insufficient. A customer served adequately by an existing product may need configuration or an upstream contribution rather than this service.

## Feasibility and boundaries

| Integration | Evidence-supported path | Boundary to preserve |
| --- | --- | --- |
| LiteLLM | Generic Guardrail API; pre-call text checking is a plausible first integration | Payload and enforcement depend on endpoint, mode, version, and configuration; validate trusted metadata and failure handling |
| Agentgateway | Upstream Jev webhook example and webhook source | Example evaluates newest input message and response choices; not all conversation context or tool execution |
| VS Code Local | Submitted-prompt stop and pre-tool deny/ask contracts | Hooks, trust, and runtime/version matter; submitted text is incomplete coverage |
| Copilot CLI | Prompt assessment; pre-tool enforcement | Configured prompt-hook output is dropped; command-hook timeouts fail open |
| Copilot cloud / SDK | In-environment hooks / input gate in an application we control | Cloud hooks do not intercept a task before GitHub receives it; SDK app control does not generalize to every Copilot interface |

These are documentation/source findings, **not successful end-to-end tests**. Local and Agent Host contracts must stay distinct. No universal Copilot interception claim is supported.

## Proposed MVP

First deliver an offline comparison on three owner-selected policies. If the evidence warrants a prototype, use a small authenticated HTTP service, versioned policy files, a Jev adapter, independent decision logic, and connector conformance fixtures. Preserve a backend interface for comparison and replacement.

Provisional sequence: **LiteLLM, then Agentgateway** for gateway reuse. Substitute VS Code Local as the second integration if coding agents are the primary customer need. Start in monitoring mode; enable blocking only for tested policies and supported host configurations.

Candidate request concepts: stage, content/context with provenance, trusted metadata, policy versions, inspection coverage and omissions. Candidate result concepts: allow/block/review/evaluation-error, policy IDs, judgments, versions, timing, and connector capability. Record actual enforcement separately after host observation; an evaluator cannot know that a host obeyed its answer. Unsupported review must be rejected as configuration or explicitly held/blocked, never silently allowed.

**Exclude initially:** broad governance UI, billing, multi-tenant SaaS, universal IDE coverage, multimodal inspection, streaming-output enforcement, autonomous policy generation, and a new human-approval system. Response/tool-action enforcement remains a later experiment unless the second integration specifically requires it.

## Evaluation and build-versus-extend

Compare Jev with deterministic rules and at least one suitable chat-model judge on the same held-out cases. Report false-block and missed-violation rates separately, uncertainty, adversarial failures, latency distributions, operational errors, and total cost. See the [evaluation plan](evaluation-plan.md).

**Recommendation:** conduct a bounded reuse spike before building the service. Test whether extending `jev-edge` can satisfy the selected policies, trusted metadata, failure modes, and portable policy/version records. Prefer contributions for reusable connector fixes. Build a small independent core only if the spike shows material incompatibilities or unnecessary coupling. Do not copy example thresholds as validated policy.

## Decisions needing owner input

1. Who is the first design partner/user, and what three concrete company rules hurt today? Supply legitimate and violating examples without private customer data initially.
2. Is the second integration Agentgateway or VS Code Local, and which deployed versions must work?
3. Can evaluation content leave the customer's environment for hosted Jev? What data classes, retention, and geographic constraints apply?
4. For each rule, what false-block rate, missed-violation rate, added latency, and failure behavior are acceptable? These are acceptance criteria to agree, not invented guarantees.
