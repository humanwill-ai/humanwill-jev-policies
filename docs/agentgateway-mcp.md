# Agentgateway MCP pre-execution

Development `0.1.0a2.dev0`, reviewed 2026-10-03. This uses Agentgateway **1.5.0**'s
native **ExtMCP gRPC interface**, not the text-only guardrail webhook or the LLM
backend relay. The public `v0.1.0a1` artifacts remain unchanged.

## Operation

Agentgateway resolves the MCP target, removes the multiplexing prefix from the
tool name, and calls `CheckRequest` with the target name and complete structured
arguments. HumanWill normalizes those into a `tool_action` event and calls the
existing authenticated HTTP policy service. Company policy evaluation, Jev
follow-ups, optional trusted metadata, monitoring and policy error fallback are
unchanged. A configured target name identifies a route; it does not approve the
tool's destination or establish the caller's authorization.

An enforced block returns `AuthorizationError` before Agentgateway forwards the
invocation. Allowed and monitored results return `Pass`. The connector never
returns argument/header mutations, grants identity claims or retries invocations.
It ignores client headers and CEL metadata for authorization; a production trusted
metadata resolver must supply any identity, approval or classification facts.

## Setup

Use a development checkout and install the optional gRPC dependencies:

```sh
python -m pip install '.[agentgateway-mcp]'
```

Start the normal policy service with your company Markdown folder, evaluation
configuration, and a protected copy of
[service-agentgateway-mcp.yaml](../examples/connectors/service-agentgateway-mcp.yaml):

```sh
humanwill-policies serve /absolute/company-policies \
  --config /protected/config.yaml \
  --service-config /protected/service-agentgateway-mcp.yaml \
  --host 127.0.0.1 --port 8088
```

Policies governing invocation must explicitly include `tool_action`. Start in
monitor mode; configure enforcement and error fallback with representative policy
tests. Hosted Jev still requires a configured evaluator credential and explicit
`allow_external_evaluation: true`. The example leaves external evaluation disabled.

Provide two distinct random credentials of at least 32 characters:

- `HUMANWILL_MCP_TOKEN` in the service and connector environments.
- `HUMANWILL_AGENTGATEWAY_MCP_TOKEN` in the connector environment. Put the same
  token in a protected Agentgateway token file, **without a Bearer prefix or
  trailing newline**. Do not include it in the YAML or repository.

Start the connector next to Agentgateway:

```sh
humanwill-policies agentgateway-mcp --url http://127.0.0.1:8088 \
  --target company_tools --port 9001
```

The gRPC listener binds only to `127.0.0.1`: run it in Agentgateway's network
namespace, including a shared pod namespace if containerized. Remote plaintext
gRPC listeners are deliberately unsupported. The HTTP service can be remote over
HTTPS. Every gRPC request must authenticate using its transport Authorization
metadata, independently of any headers embedded inside the ExtMCP message.

Copy [agentgateway-mcp.yaml](../examples/connectors/agentgateway-mcp.yaml), replace
the token-file path and upstream MCP address, then run:

```sh
agentgateway -f /protected/agentgateway-mcp.yaml
```

Point the agent at the gateway's `/mcp` endpoint. Keep normal gateway client
authentication and MCP permissions; the sample is a local wiring example, not a
public-facing authenticated deployment. Prevent direct upstream access when this
is meant to be a mandatory control. Each configured MCP target must be supplied
to the connector with a repeated `--target`; unknown targets block.

Use `methods: {tools/call: request}` and `failureMode: failClosed`. An empty
`requestHeaders.allowed` means **all headers**, so the sample uses only `:method`.
No incoming authorization header is forwarded in the ExtMCP body. The connector
does not use even that header as authorization evidence.

## Failure behavior and limitations

- An enforced violation blocks before execution. Monitoring records an assessment
  and passes the call. Evaluation errors use the policy's existing configured
  fallback; connector/HTTP failures always deny, including in monitor mode.
- If the connector is unavailable or gRPC fails, Agentgateway's `failClosed`
  setting is essential. Removing the guardrail or selecting `failOpen` bypasses
  this control. A healthy process alone does not demonstrate enforcement.
- The connector uses a 6-second HTTP deadline (configurable up to 9 seconds),
  below the pinned gateway's 10-second default processor timeout. The service
  example allows 5 seconds. Incoming protobufs/verdicts are bounded to 262144
  bytes, and the default gRPC concurrency limit is 8. Overload rejects requests.
- Only synchronous `tools/call` request checks are supported. Unknown received
  parameters/extensions, malformed argument objects, unexpected targets and
  wrong phases reject. Standard progress-token metadata is ignored. Discovery
  bypasses this processor by configuration; tool results, resource reads, prompt
  retrieval and asynchronous task flows are not inspected by this profile.
- The adapter checks Agentgateway's parsed parameters, not arbitrary raw client
  extensions. It cannot inspect referenced files/scripts, the full conversation,
  the tool implementation or network operations the tool later performs.
- Use this as the sole argument-processing MCP guardrail, without later body or
  argument transformations. Later processors can mutate an already-approved call.
  Gateway permissions still apply after this check; a HumanWill allow is not proof
  that the tool executed. Retain gateway/server telemetry for actual outcomes.
- This is independent of LLM streaming. Streamable HTTP for MCP does not imply
  support for inspecting streamed model responses. Keep response disclosure
  policies at the LLM gateway as a separate control.
- Native HTTP MCP routing is the initial qualification target. Stdio, legacy SSE,
  OpenAPI-derived tools, Kubernetes resource bindings and newer Agentgateway
  versions need separate validation. No MCP latency or new semantic accuracy claim.

## Source and verification

Current [MCP guardrail documentation](https://agentgateway.dev/docs/standalone/latest/documentation/mcp/guardrails/setup/)
describes ExtMCP. The implementation is pinned to the v1.5.0 source at
[`fe6732474a96a0363dfb9822859af4e9bab360fa`](https://github.com/agentgateway/agentgateway/tree/fe6732474a96a0363dfb9822859af4e9bab360fa):
`crates/protos/proto/ext_mcp.proto`, `mcp/session.rs`, `mcp/handler.rs`, and
`mcp/guardrails/{client,mod}.rs`. Source inspection confirms target resolution →
request guardrail → MCP authorization → upstream forwarding. Current documentation
may describe newer versions; it does not replace pinned runtime verification.

Six local gRPC wire tests pass. The actual Agentgateway/MCP-server harness is
prepared for a single targeted Linux host-workflow run; its result is pending.
It checks allowed/denied invocations, errors/timeouts, missing trusted facts,
both service and connector outages, resolved target separation, unknown targets,
concurrent calls, and discovery. Each permitted call must execute with identical
arguments, and each denied call must produce no tool-side effect. The evaluator
is synthetic: these are enforcement plumbing tests, not live Jev accuracy tests.
