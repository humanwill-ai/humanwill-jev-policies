# MCP pre-execution through LiteLLM

See [beta installation and exact validation](public-beta-v020.md) for this candidate.

Public Beta candidate `0.2.0b1`, reviewed 2026-10-02. This is separate from
the published `v0.1.0a1` text-only connectors and from optional model-proposal
inspection. The first supported execution binding is **LiteLLM 1.102.1 `/mcp/`**
with Streamable HTTP. [Agentgateway's separate native MCP binding](agentgateway-mcp.md)
now also has actual-host acceptance evidence. Prisma AIRS, REST MCP endpoints and
Responses API automatic execution have not been runtime-qualified here.

## Flow

1. The agent calls a tool through the company's LiteLLM MCP gateway.
2. LiteLLM resolves the server and invokes the mandatory `pre_mcp_call` guardrail.
3. HumanWill copies the tool name and **complete argument object**, including
   nested/non-string values, into a `tool_action` request. It adds the gateway's
   server reference as context. It does not forward incoming credentials,
   headers, claimed identity or group membership.
4. The authenticated policy service applies company policies for `tool_action`,
   existing Jev evaluation/follow-ups, and independently verified metadata when
   configured. The server reference is not evidence that a destination is approved.
5. The callback verifies that the returned verdict covers this exact request and
   that the invocation has not changed during the check. An enforced block raises
   an error **before forwarding to the MCP server**. Otherwise LiteLLM continues
   with the original arguments. HumanWill does not retry or rewrite invocations.

Tool discovery is not execution and does not trigger action assessment. This
connector does not inspect tool descriptions for poisoning or returned tool
results. It sees arguments, not the contents of referenced files, scripts or URLs,
the full conversation, or the implementation/effects of arbitrary tools.

## Configure a dedicated MCP gateway

Install the beta candidate in your policy-service environment and in the
same environment as `litellm[proxy]==1.102.1`. The public preview wheel does not
contain this connector. Keep the existing LLM gateway and its response policy
checks separate for this initial deployment: its text/tool chat callbacks reject
non-chat events and must not be installed on this MCP-only gateway.

```sh
python -m pip install .
```

In the dedicated LiteLLM environment, install the same checkout:

```sh
python -m pip install 'litellm[proxy]==1.102.1'
python -m pip install .
```

Copy [service-mcp.yaml](../examples/connectors/service-mcp.yaml) and
[litellm-mcp.yaml](../examples/connectors/litellm-mcp.yaml) to a protected
configuration directory. Replace the sample MCP server URL with your managed
server. Set `HUMANWILL_MCP_TOKEN` to a random token of at least 32 characters in
both processes, and `LITELLM_MASTER_KEY` only in the gateway. Use a distinct token
from other connectors. Remote policy-service connections require HTTPS.

Use your existing Markdown policy folder and matching evaluation configuration.
Policies intended to govern execution must include `tool_action` in their
`stages`; a prompt-only policy does not become an action policy automatically.
The service principal is restricted to `tool_action`. Start policies in monitor
mode; enable enforcement and set error fallback only after reviewing your policy
tests. Follow [policy authoring](policy-authoring.md) and
[service configuration](service-and-connectors.md) for bindings/provider setup.

For hosted Jev, provide the configured evaluator credential and explicitly set
`allow_external_evaluation: true` in your copied service file. Policy text and
covered tool arguments then leave your environment through the selected provider.
The example keeps this opt-in disabled.

```sh
humanwill-policies serve /absolute/company-policies \
  --config /absolute/configuration/config.yaml \
  --service-config /absolute/configuration/service-mcp.yaml \
  --host 127.0.0.1 --port 8088
```

In the dedicated gateway environment:

```sh
litellm --config /absolute/configuration/litellm-mcp.yaml --port 4000
```

Point your agent's MCP client at `http://127.0.0.1:4000/mcp/` with its gateway
authorization token, rather than at the upstream server. Retain the gateway's
normal authentication and tool permissions. Before enabling developer access,
verify a permitted and a denied synthetic call against server-side effects.
A healthy proxy or an HTTP 200 response alone does not establish enforcement:
MCP denials can be returned as `isError: true` inside an HTTP 200 response.

## Failure behavior and coverage

- Monitoring still evaluates but does not block policy violations or policy
  evaluation errors. Enforced policy errors use the existing configured fallback.
- Transport outage, malformed/mismatched service verdict, unsupported invocation,
  or callback deadline expiry block at the connector, even in monitor mode.
  There is no connector fail-open switch in this initial profile.
- The default callback deadline is 6 seconds; the example service deadline is
  5 seconds. Normal argument assessment adds evaluator/network latency; no new
  representative MCP latency benchmark has been run.
- The guard is mandatory for its event and ignores per-request global-guardrail
  opt-outs. It rejects other modes, parallel operation and masking/scoping options.
  Invalid settings and missing credentials stop startup in the tested host. If
  the guardrail is removed entirely from configuration, HumanWill cannot protect
  that gateway: control configuration access and verify denial at deployment.
- Deploy it as the **sole pre-execution argument-processing guardrail**, outside
  LiteLLM pipelines/load-balanced guardrail groups. Divergent `modified_arguments`
  and added `extra_headers` are rejected. Changes during assessment are detected;
  a later hook, agent bypass, compromised gateway or tool implementation can still
  invalidate the guarantee. Do not claim binding to final execution under arbitrary
  third-party mutating hooks.
- Network/credential controls must prevent direct upstream MCP access if this is
  intended as a mandatory control. Local shell tools and other routes are not
  covered. A tool's follow-on network access is not automatically intercepted.
- MCP pre-execution can be the primary action-policy check when all relevant calls
  traverse it. Model-proposal inspection remains an additional optional layer;
  generated-response disclosure checks remain useful before any execution occurs.
  This feature does not automatically disable existing proposal checks.
- HumanWill's service audit remains an assessment with requested enforcement,
  not a receipt proving a tool ran. Host tests observe actual server-side effects;
  production execution telemetry is separate. Review LiteLLM/server logging too:
  the connector's minimal payload does not control their independent logs.

## Evidence

An installed wheel outside the checkout, actual LiteLLM 1.102.1 process, actual
local MCP server, real policy-service HTTP requests and a synthetic evaluator
pass **18 runtime scenarios**. These cover discovery, allowed/denied calls,
evaluator errors/timeouts, missing trusted metadata, policy-service outage,
concurrent calls in enforce/monitor modes, and two invalid-startup cases.
Assertions compare executed arguments and count side effects; a denial must have
zero side effects. Four installed callback checks exercise mandatory selection,
unsafe options, errors/allow behavior and argument mutation while awaiting a
verdict. Six new offline tests cover normalization, privacy, verdict binding,
monitoring, protocol failures and the client deadline. Full suite: 279 passing.

[Machine-readable evidence](evidence/mcp-pre-execution-v1.json) records exact
runtime hashes, wheel hash and local reports. No paid provider calls, new Jev
accuracy measurement, hosted MCP CI run or release publication were performed.
The existing host workflow includes these checks for its next required run.

```sh
# Run after installing the beta candidate wheel in the pinned LiteLLM environment:
python tests/hosts/mcp_guardrail.py
python tests/hosts/mcp_calls.py --binary /absolute/litellm-env/bin/litellm
```

## Source review

Reviewed on 2026-10-02 against installed LiteLLM **1.102.1**:
`mcp_server_manager.pre_call_tool_check`/`call_tool`,
`ProxyLogging._convert_mcp_to_llm_format`/`_execute_guardrail_hook`,
`CustomGuardrail.should_run_guardrail`, and guardrail initialization. This binding
uses the native callback to retain complete arguments, rather than the generic
translation's extracted text leaves. Package-source hashes are in the evidence
record; changing host versions requires revalidation.

[LiteLLM MCP guardrails](https://docs.litellm.ai/docs/mcp_guardrail) documents
pre-execution hooks and the importance of default-on selection for MCP subcalls.
[MCP configuration](https://docs.litellm.ai/docs/mcp_config_reference) describes
gateway routing. Current online docs also describe discovery scans and other
entry points; these are not automatically claims about this pinned runtime.
