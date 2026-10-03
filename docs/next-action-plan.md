# Next action plan: tool-call and MCP enforcement

> Latest workflow comparison, 2026-10-03: [policy-specific targets](dogfood-views-v1-report.md)
> restore historical-secret blocking, but workflow abstention is 35% versus 30%
> with fresh grouping and 40% with fresh flat runtime. No candidate adoption:
> the friction target remains unmet. Labels are provisional; streaming is deferred
> and future capture invocation remains unobserved.

> Latest conversation experiment, 2026-10-03: [explicit policy subjects and dual views](conversation-views-v1-report.md)
> restore historical-secret blocks and reduce unexpected combined errors to 7/81,
> versus 9/81 grouped and 19/81 flat. Individual-policy matches regress versus
> grouping (224/270 versus 232/270). Research-only; no runtime adoption or new release.

Owner-approved sequence, 2026-10-01. **Steps 1–2 authorized 2026-10-02.**
The opt-in development implementation and local evidence are in
[structured tool calls](structured-tool-calls.md). LiteLLM real-host checks pass;
Agentgateway requires a backend relay because its webhook drops tool fields, and
the relay's real Agentgateway/Linux acceptance now passes. Step 2 is implemented
for both gateways with actual MCP servers:
[LiteLLM](mcp-pre-execution.md) and [Agentgateway](agentgateway-mcp.md).
Step 3 remains planned; no streaming implementation is included.
Owner added a pre-streaming concern on 2026-10-03: avoid treating abandoned
requests in conversation history as fresh instructions. The config/5
[conversation clarification](conversation-inspection.md) is implemented locally.
Its [live comparison](conversation-v1-report.md) shows partial improvement, with
six legitimate case types still failing closed through uncertainty. The subsequent
[structural-context experiment](conversation-structure-v1-report.md) improves
legitimate passes to 24/27 but makes the historical-secret check indeterminate.
It remains research-only. Review full-payload content-policy handling and absent-role
fallback before runtime adoption; do not ignore history or trust inline block notices.
This is the next feature sequence after the public `v0.1.0a1` preview. Saving this
plan does not start implementation, paid evaluations, deployment or another release.

## 1. Structured tool calls without streaming

Extend the LiteLLM and Agentgateway connectors to inspect structured tool calls
in non-streaming requests/responses. Reuse the existing `tool_action` evaluation
core and stage-aware follow-up; streaming support is not a prerequisite.

- Parse tool names and complete argument objects, including multiple calls in a
  response. Preserve argument structure and distinguish tool definitions and
  historical calls from newly proposed actions.
- Evaluate proposed actions against the policies for their stage, with explicit
  coverage and optional trusted metadata. Definitions alone are not executions.
- Withhold an enforceable model response until all required checks finish. Apply
  the configured monitoring, block and evaluation-error behavior explicitly.
- Update the current text-only restrictions only for newly supported shapes;
  malformed or unsupported content must not silently pass.

Exit evidence: real pinned-host tests for allowed and blocked proposals, multiple
calls, malformed arguments, missing metadata and service failures. Prove that an
enforced block prevents the client receiving an executable proposal. Checking a
proposal does not establish that the agent later invokes it unchanged.

## 2. MCP pre-execution enforcement

Add a connector that checks the actual tool invocation before forwarding it to an
MCP server. LiteLLM's MCP Gateway is the proposed first target; Prisma AIRS and
other gateway bindings remain separate integration work requiring their own tests.

- Route MCP traffic through the gateway and normalize the actual tool name and
  arguments as `stage: tool_action`. Preserve server context where supplied;
  authenticate any identity or authorization facts before trusting them.
- Use a blocking pre-execution integration point, such as LiteLLM's documented
  `pre_mcp_call`. Reverify the exact supported version and payload contract before
  implementation; the existing text-only connector is not MCP support.
- Configure required checks at the deployment level and make timeout, unavailable
  evaluator and unsupported-payload behavior explicit. Account for other hooks
  mutating arguments after assessment.
- Document that direct MCP connections and non-MCP tools outside this route are
  not covered. Tool-result inspection can be designed separately; it cannot undo
  actions that have already executed.

Exit evidence: a real local MCP server with observable side effects. Confirm
allowed calls execute and blocked calls do not, including failure and bypass
scenarios. Distinguish discovery, proposals, invocations and returned results.

## 3. Streaming with tested buffering and blocking

After the non-streaming and MCP paths are validated, add streaming support with
explicit rules for when content may be released to the caller.

- Assemble and validate complete tool-call names and arguments from streamed
  fragments before releasing an executable call. Handle interleaved/multiple calls.
- Define buffering for policy-governed text output too. Checks performed after
  delivery are assessment-only for content already released.
- Bound buffer size, time, cancellation and error handling. Retain explicit
  behavior for truncated, malformed or unsupported streams.

Exit evidence: prove that rejected tool calls or governed output are not delivered
before the decision, and measure time-to-first-token, total latency, memory and
failure behavior. Document each host's actual enforcement boundary.

## Constraints carried forward

Keep the policy core independent of gateways, metadata optional and trusted facts
separate from model judgments. Retain the selected sequential follow-up approach,
existing policies and thresholds unless a later change is explicitly scoped.
Do not relax content validation or infer authorization merely to support a new
transport. Preserve monitoring defaults and distinguish assessment from observed
enforcement. Plan representative new examples without treating tuned cases as an
independent holdout. Preserve the published tag/assets and historical evidence.

Each step needs its own compatibility review and bounded implementation/validation
plan. Existing provider and Actions budgets still apply; no automatic live campaign
is part of this saved sequence. Independent release qualification remains open.

## References

- [Current connector coverage](service-and-connectors.md#coverage-and-optional-metadata)
- [Existing follow-up contract](bounded-policy-followup.md)
- [LiteLLM MCP guardrails](https://docs.litellm.ai/docs/mcp_guardrail)
- [LiteLLM MCP routing](https://docs.litellm.ai/docs/mcp_config_reference)

The LiteLLM references were reviewed on 2026-10-01 alongside installed 1.102.1
source. That was documentation/source inspection, not an MCP runtime test.
