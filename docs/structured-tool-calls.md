# Non-streaming structured tool-call inspection

Development version **0.1.0a2.dev0**, reviewed 2026-10-02. This feature is not in
the published `v0.1.0a1` assets. Existing text-only profiles retain their behavior;
enable the new profiles explicitly and install the matching development build in
both the service and LiteLLM host. No new Jev accuracy or latency claim is made.

## What is checked

1. On input, evaluate supplied text messages, historical function calls, tool
   results and available function definitions as a `model_request`. Preserve
   arguments, roles and call IDs. Definitions and historical calls are **not new
   executions** and do not trigger `tool_action` policies.
2. On output, evaluate all supplied text and serialized function-call proposals
   as a `response`, including names/arguments that could disclose protected data.
3. Evaluate **each** newly proposed call separately as `tool_action`, preserving
   its name and parsed argument object. Resolve optional trusted facts separately
   for every event; approval of one call cannot authorize another destination.
4. An enforced block at any step withholds the entire response. Otherwise release
   it only after all required assessments complete. Monitoring records decisions
   without policy blocking; configured policy error fallbacks still apply.

The existing policy core, confidence thresholds and opt-in stage-aware follow-up
are reused unchanged. A policy needs `tool_action` in its stages to govern proposed
actions. Keep `response` policies for disclosure through generated text/arguments.
The action event contains the supplied name and arguments, not the full conversation,
tool results, repository or evidence that execution actually occurred. Coverage
`complete` refers only to that declared surface. Request history is untrusted input,
not proof that an operation occurred or was authorized.

Supported calls are OpenAI-style `type: function`, with a nonempty ID/name and
arguments containing a complete JSON **object**. Up to 32 calls per response are
supported, with separate policy decisions; multiple calls and multiple choices
must all pass. Duplicate IDs, duplicate JSON keys, nonfinite numbers, truncated
arguments, non-object arguments and unsupported call types are rejected. Tool
proposals with a non-`tool_calls` finish reason are rejected by the full-response
profile. Legacy `function_call`, multimodal content and streaming remain unsupported.

All assessments in a service request share its deadline and concurrency slot.
Input and relay output bodies are limited to 262144 bytes. A later malformed call
cannot be hidden behind an earlier allow. Gateway wire responses expose only a
combined allow/block, while audit records retain individual assessments and a
shared `assessment_group` plus `assessment_index`. Blocking can short-circuit the
remaining checks because no part of the model response is released. This is not
an atomic guarantee about what a separate agent eventually executes.

## LiteLLM

Use pinned LiteLLM **1.102.1** and install the development HumanWill wheel in its
environment as well as in the service environment.

- Start from [service-tools.yaml](../examples/connectors/service-tools.yaml).
  The principal must set `inspect_tool_calls: true` and authorize all three stages:
  `model_request`, `response`, `tool_action`.
- Start from [litellm-tools.yaml](../examples/connectors/litellm-tools.yaml).
  Set the approved coding model, its credential, gateway client authentication and
  matching connector token as in the [setup guide](service-and-connectors.md).
- Keep **both** the `tool_profile` callback and the pre/post generic guardrail.
  The callback validates the full request/response shape and completion status;
  the guardrail sends content to the policy service and applies its decision.
  Keep these required globally and exclude host configurations that bypass them.
- Approve hosted Jev egress in the service configuration and start the service with
  your policy bundle and evaluation configuration. Keep `stream: false` in client
  requests. Function definitions in `tools` are now accepted by this opt-in profile.

The Generic Guardrail API flattens response choices into text and calls. Each call
is assessed independently; choice-to-text association and input conversation are
not included in the individual action event. Do not infer context the host did not
provide. Additional callbacks must not mutate assessed output after these checks.

## Agentgateway: protected backend relay

Agentgateway **1.5.0's promptGuard webhook discards tool-call structure**. Its
`SimpleChatCompletionMessage` contains only `role` and `content`; request extraction
and response conversion use that reduced representation. Simply permitting tools
in the existing CEL profile would produce unchecked proposals.

The new profile uses this path:

```text
client → Agentgateway HTTP route → HumanWill relay → approved model backend
                                      ↕
                                     Jev
```

The response traverses the same route in reverse, after the relay has completed
response and proposed-action checks. This adds an HTTP hop and buffers the complete
non-streaming response. It is an alternative to the text-only webhook profile,
not an additional webhook that recovers missing fields.

1. Copy [service-agentgateway-relay.yaml](../examples/connectors/service-agentgateway-relay.yaml).
   Set the fixed `model_backend.url`, `model`, and credential environment variable.
   Only an OpenAI-compatible `/chat/completions` backend is supported here. The
   submitted model must match the configured model. Customer-selected URLs and
   credentials are rejected; there is no multi-provider routing in this relay.
2. Supply a distinct `HUMANWILL_AGENTGATEWAY_TOKEN` to the service. Store the same
   token in a protected file readable by Agentgateway (do not include `Bearer ` or
   a trailing newline). Copy [agentgateway-tools.yaml](../examples/connectors/agentgateway-tools.yaml)
   and replace its token-file path. This HTTP route preserves full payloads and
   injects the connector token using backend authentication.
3. Start the service with that configuration and your policy bundle, then run
   `agentgateway -f /protected/agentgateway-tools.yaml`. Send non-streaming chat
   requests to the configured gateway listener, using the configured backend model.
   Add your normal client authentication and network restrictions before exposure.
4. Keep the original model backend inaccessible through an alternate unguarded
   route. The relay must be protected from direct unauthorized access too. Do not
   attach the old text-only promptGuard profile to this route.

Backend forwarding sends request content to the configured coding model separately
from policy evaluation's Jev data flow. Configuration of this fixed backend is an
explicit deployment choice; the Jev egress flag does not authorize or make that
model local. Only HTTPS or loopback HTTP is accepted. The relay never follows
redirects, retries generation, or forwards caller/connector credentials to the model;
it uses the separate configured backend credential. It strips upstream errors and
does not release malformed, oversized or streamed replies.

The example uses a **60-second total deadline**, including generation and policy
checks; choose compatible gateway/client deadlines. Generation plus checking cannot
use the old seven-second webhook budget for every workload. All relay protocol,
upstream and deadline errors fail closed, including monitoring deployments. Policy
evaluation errors still use their policy's configured fallback. No relay latency
or production throughput has been measured.

## Verification and remaining gate

The full offline suite passes **273 tests** on Python 3.14, including 13 new
focused tests. Ruff and formatting checks pass. Original LiteLLM text-profile
regressions pass all 22 host scenarios. Wheel/source installation, service/hook
contracts and service process checks pass outside the checkout.

Local synthetic checks cover parsing, history/definition separation, response and
action decisions, multiple calls, per-action trusted metadata, missing facts,
monitoring/error fallbacks, shared deadlines, fixed routes, redirect refusal and
oversized/unsupported output. These test enforcement plumbing, not Jev accuracy.

- Real pinned LiteLLM process: 26 new scenarios pass with an installed development
  wheel, a local model endpoint and synthetic evaluator transport, outside the
  checkout on Python 3.11. Includes missing trusted metadata in enforce/monitor modes.
- Relay over loopback HTTP: 26 corresponding scenarios pass. This is a real relay
  service/network test, **not** a real Agentgateway test.
- Agentgateway route configuration validates against the exact v1.5.0 JSON schema.
  **Real Agentgateway relay acceptance remains pending Linux validation**: the
  current macOS x86_64 environment has neither a compatible binary nor Docker.
  Its old text-profile results do not qualify this new route.

Run the prepared host checks after installing the current wheel:

```sh
python tests/hosts/tool_calls.py --host litellm --binary /litellm-env/bin/litellm
python tests/hosts/tool_calls.py --host agentgateway --binary /path/to/agentgateway
python tests/hosts/tool_calls.py --host relay
```

The existing host workflow includes the first two checks for the next authorized
batched CI run. No workflow was dispatched or paid provider called for this change.
Do not publish a new release or claim Agentgateway tool enforcement verified until
that remaining host gate passes. No MCP execution interception or streaming was added.

Machine-readable evidence: [local verification record](evidence/tool-calls-v1.json).
The raw synthetic reports and artifacts are retained locally under
`artifacts/tool-calls/`; they are not release assets.

## Source review

Reviewed 2026-10-02 against installed LiteLLM 1.102.1 source and Agentgateway v1.5.0
at `fe6732474a96a0363dfb9822859af4e9bab360fa`:

- [LiteLLM Generic Guardrail API](https://docs.litellm.ai/docs/adding_provider/generic_guardrail_api)
  documents input definitions/history and output `tool_calls`. The installed chat
  translator and generic API implementation confirm extraction and pre-return denial.
- [Agentgateway simplified message](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/llm/src/types/mod.rs)
  and [chat conversion](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/llm/src/types/completions.rs)
  establish the webhook's missing tool fields.
- [Pinned configuration schema](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/schema/config.json)
  defines the HTTP backend route and file-based backend credential.
