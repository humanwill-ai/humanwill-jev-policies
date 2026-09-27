# Research ledger

Reviewed **2026-09-27**. Primary documentation and public source inspected; no gateway, hook, or live Jev evaluation executed. Source commits identify inspected development snapshots, not tested release versions. Vendor claims are not independent measurements.

## Confirmed documentation and source findings

### Agentgateway

The [project](https://agentgateway.dev/) covers LLM and MCP traffic. At commit `7e47ceb576aa9d3300cb0d2c7c35848fb0af048f`, its [Jev example](https://github.com/agentgateway/agentgateway/tree/7e47ceb576aa9d3300cb0d2c7c35848fb0af048f/examples/llm-guardrail-jev) is a separate Bun webhook. [Implementation](https://github.com/agentgateway/agentgateway/blob/7e47ceb576aa9d3300cb0d2c7c35848fb0af048f/examples/llm-guardrail-jev/guardrail.ts) uses `slice(-1)` on requests and examines each response choice. Three scored questions cover jailbreaks, harmful activity, and secrets; the example rejects at score >= 2 on a four-level rubric. This threshold is illustrative.

Jev runs through the gateway's TypeSafe route. The webhook returns HTTP 200 with an action containing the intended client rejection status. Its evaluator has an eight-second deadline and no retries. The [webhook source](https://github.com/agentgateway/agentgateway/blob/7e47ceb576aa9d3300cb0d2c7c35848fb0af048f/crates/agentgateway/src/llm/policy/webhook.rs) defines host-specific payloads and propagates call/parse errors; failure enforcement still needs integration testing. The [configuration](https://github.com/agentgateway/agentgateway/blob/7e47ceb576aa9d3300cb0d2c7c35848fb0af048f/examples/llm-guardrail-jev/config.yaml) enables full LLM access logging for demonstration. Do not adopt its logging or authentication setup as production defaults.

### LiteLLM

The [Generic Guardrail API](https://docs.litellm.ai/docs/adding_provider/generic_guardrail_api) exposes `POST /beta/litellm_basic_guardrail_api` and `BLOCKED`, `NONE`, and `GUARDRAIL_INTERVENED` actions. Current documentation includes optional structured messages, tool definitions/calls, identity-related metadata, and pre/post-call behavior. Availability varies by endpoint/stage; this is not complete host context.

At commit `f4308bc124eebc783dfc51790ce8db27ed21ae00`, the [implementation](https://github.com/BerriAI/litellm/blob/f4308bc124eebc783dfc51790ce8db27ed21ae00/litellm/proxy/guardrails/guardrail_hooks/generic_guardrail_api/generic_guardrail_api.py) agrees on the endpoint and actions. It adds `x-api-key` when configured and defaults to `unreachable_fallback=fail_closed`, `fail_on_error=true`. Unreachability fallback covers network errors/timeouts and 502/503/504; disabling `fail_on_error` broadly bypasses evaluation errors, while valid blocks still block. Client dynamic parameters can merge over configured parameters: our service must independently select/authorize policy versions and thresholds.

The [TypeSafe adapter source](https://github.com/BerriAI/litellm/blob/f4308bc124eebc783dfc51790ce8db27ed21ae00/litellm/proxy/guardrails/guardrail_hooks/typesafe/typesafe.py) evaluates tool-exchange relevance through System One and blanks low-relevance results. [Auto Router](https://docs.litellm.ai/docs/auto_router/) separately supports Jev classification. Neither establishes a general company-policy evaluator or compatibility with a chat `judge_model` slot.

### Copilot interfaces

The [VS Code Local reference](https://code.visualstudio.com/docs/agents/reference/hooks-reference) supplies submitted `prompt` text, supports common `continue:false` output, and permits `PreToolUse` allow/deny/ask. Nonzero exits have distinct semantics: exit 2 blocks, other nonzero exits warn and continue. [Configuration documentation](https://code.visualstudio.com/docs/agent-customization/hooks) makes Local hooks subject to `chat.useHooks` and Workspace Trust. Local and Copilot Agent Host use different runtime contracts, even where configuration formats are compatible.

The [GitHub hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference) says command/HTTP `userPromptSubmitted` output is dropped; SDK programmatic hooks can modify the prompt. CLI `preToolUse` supports enforcement. Command pre-tool crashes/nonzero exits deny, but **timeouts fail open**, including policy hooks. HTTP pre-tool errors/timeouts/non-2xx fall through to normal permission handling. Cloud execution has no interactive approval: `ask` becomes deny. Its hooks operate within the job, not before task submission to GitHub.

Inference: an application we own can gate input before its SDK submission call. That does not cover other clients. Universal interception of GitHub.com chat, inline completions, and all IDEs remains unestablished. The [Copilot application card](https://docs.github.com/en/copilot/responsible-use/chat) documents content filtering and development-time safety evaluation; it does not establish a universal configurable Jev judge or a single live grading model.

### Jev backend

[TypeSafe's API](https://docs.typesafe.ai/api) takes `state`, typed `questions`, and `model` at `/v1/systemone`, returning structured answers, model identity, and usage. Choice, Score, and Noul are distinct primitives; use an evaluation adapter, not assumed chat-completions compatibility.

The [model page](https://docs.typesafe.ai/models) lists `jev-1.13.0`, text-only input, 64k total request tokens with a separate 32k state-plus-longest-question limit, and $0.042 per million input tokens with free output. These are vendor specifications, not measured service costs. Pin versions; aliases move. Verify quotas and current billing before benchmarks. Retention, location, contractual terms, and customer suitability remain unresolved; a no-training statement does not establish zero retention for every account.

**Material finding:** TypeSafe's [known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13) explicitly say adversarial state can steer answers. It also describes difficulties with irrelevant context, multi-step reasoning, and transferring thresholds between primitives. Typed output does not establish robustness. Decomposing policies and controlling context are hypotheses to test, not mitigations proven sufficient.

### Existing alternatives

The [`jev-edge` README](https://github.com/kiwi0719/jev-edge) reports no known production use and deliberate fail-open operation. It documents many adapters and Jev, Laya, and compatible chat backends. At `2396e445ffe0ed08a4328401fb8ad3a78ce2a3ce`, its [LiteLLM adapter](https://github.com/kiwi0719/jev-edge/blob/2396e445ffe0ed08a4328401fb8ad3a78ce2a3ce/adapters/litellm/jev_edge_guardrail.py) delegates to `/_jev/authz`, converts network errors and certain unavailable responses into pass/error verdicts, and separately handles unjudgeable content. This is substantial reusable integration work; it is not demonstrated production maturity. The repository identifies Apache-2.0 licensing; inspect exact files/notices before reuse.

[Bifrost Enterprise](https://docs.getbifrost.ai/enterprise/guardrails) documents configured LLM judging for organization-specific natural-language rules. [LiteLLM's provider catalog](https://docs.litellm.ai/docs/guardrail_providers) documents Alice policy evaluation and Conduct rule enforcement. These are evidence of available capabilities, not of comparative accuracy, adoption, or our differentiation. Pricing/contract terms and customer fit require a separate comparison.

## Changes, tensions, and uncertainty

| Item | Status and implication |
| --- | --- |
| Generic Guardrail API feasibility | Stronger than tentative notes: docs and source agree. Still requires pinned-release execution tests. |
| Agentgateway scope | Newest-message input claim confirmed; response checking also exists. Do not describe it as input-only. |
| Copilot failure behavior | Timeout claim confirmed; distinguish command errors from HTTP failures instead of labeling all failures alike. |
| Jev robustness | Vendor documents adversarial susceptibility. Enforcement suitability is an open question, not merely an unmeasured optimization. |
| Low token price vs total cost | Price excludes our networking, retries, operations, labeling, and blocked-work costs. No performance advantage established. |
| Small context vs full coverage | Context filtering may improve accuracy but omit relevant evidence. Measure both and report omissions. |
| Portable service vs existing projects | Existing adapters reduce the technical gap; a separate product needs customer evidence. |

No direct documentation/source contradiction was found in the inspected gateway paths. Release availability, host bypasses, authentication provenance, timeout enforcement, streaming behavior, payload limits, and end-to-end coverage remain untested. Copilot findings are documentation-only; runtime internals were not independently audited.

## Reuse spike before implementation

Time-box an experiment using synthetic cases: configure one semantic rule and one trusted-metadata rule through `jev-edge`; attempt explicit failure handling and record policy/model versions. Compare extraction and failure fixtures with LiteLLM Generic Guardrail and Agentgateway formats. Check whether the desired independent decision core can be reused without importing an unnecessary proxy runtime. Record maintenance, licensing, deployment, and change-size tradeoffs. Choose contribution, extension, or a small new service from that evidence.

## Follow-up: OpenRouter and the benchmark companion

Reviewed 2026-09-27 after the owner specified Markdown bundles, all three connector families, and OpenRouter development/testing.

[OpenRouter's Jev tutorial](https://openrouter.ai/blog/tutorials/how-to-use-jev/) documents `POST https://openrouter.ai/api/alpha/decisions` with `typesafe/jev-1.13`, typed questions, and OpenRouter credentials. The [SDK access guide](https://openrouter.ai/blog/insights/what-is-jev/) also describes a TypeSafe-compatible route. The implementation plan chooses the explicit Decisions transport and keeps direct TypeSafe separate. This confirms a documented access path, not tested account access or transport equivalence. The generic chat/router listings should not be mistaken for the evaluation contract.

At benchmark commit `5be1e12c2865b47ebdc099a68ab7732fbae466ce`, the [package configuration](https://github.com/humanwill-ai/humanwill-benchmark/blob/5be1e12c2865b47ebdc099a68ab7732fbae466ce/pyproject.toml) uses Python 3.11+; its [policy guide](https://github.com/humanwill-ai/humanwill-benchmark/blob/5be1e12c2865b47ebdc099a68ab7732fbae466ce/docs/POLICY_OVERRIDES.md) describes versioned TOML judge-policy bundles, resolution provenance, and immutable snapshots. Those are useful reuse candidates, but the false-refusal/usefulness scoring contract is not arbitrary runtime company-policy enforcement. Do not change benchmark label eligibility or treat its existing dataset as a sufficient violation benchmark.

The [release plan](release-plan.md) supersedes the earlier sequencing recommendation: a small independent core with a bounded reuse review during the offline milestone, followed by all required connectors. No live evaluation, benchmark run, or customer-data transmission was performed in this follow-up.
