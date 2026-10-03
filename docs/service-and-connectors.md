# Service and connector operation

Current connector contract · public preview `0.1.0a1`. Start with the
[user setup walkthrough](../README.md#use-with-your-ai-tools) for installation,
policy files and service configuration. See [runtime evidence](integration-report.md)
before making enforcement claims. Linux/macOS only; use the pinned host
versions/configurations. No hooks are automatically installed.

For the unreleased `0.1.0a2.dev0` tool-call profiles, use the separate
[structured-call setup guide](structured-tool-calls.md) and the separate
[LiteLLM](mcp-pre-execution.md) and [Agentgateway](agentgateway-mcp.md) MCP guides.
The text-only webhook
configuration on this page remains the published `v0.1.0a1` path.

## Run the service

Install the package following the README. Supply your validated policy folder and matching supported configuration (config/2 through config/5). The demo remains monitoring-only. Add this provider configuration to its `config.yaml` for hosted evaluation:

```yaml
provider:
  transport: openrouter
  model: typesafe/jev-1.13
  accepted_models: [typesafe/jev-1.13-20260917]
  api_key_env: OPENROUTER_API_KEY
```

Use the exact returned-model allowlist you have validated. Direct TypeSafe uses `transport: typesafe`, `model: jev-1.13.0`, its separately validated allowlist and credential environment reference. Direct live smoke is optional for v0.1; its synthetic contracts remain required. No route fallback occurs.

Copy [service.yaml](../examples/connectors/service.yaml) outside agent-writable folders. Remove unused principals. Set each remaining token environment variable to a **different random secret of at least 32 ASCII characters**; configure the matching host/client with that same principal's token. Use a secret manager or local environment, never a committed token. Service startup rejects missing/duplicate tokens and incompatible stages/deadlines.

`allow_external_evaluation: false` is the default. Turning it on authorizes disclosure of applicable policy/scope text and covered event content to the configured hosted evaluator on every accepted request. Resolve customer data-egress constraints before doing this. The server does not derive destination approval from caller metadata. Self-hosting this service does not make evaluation local.

```sh
humanwill-policies validate /policy-root --config /protected/policies.yaml
humanwill-policies serve /policy-root --config /protected/policies.yaml \
  --service-config /protected/service.yaml --host 127.0.0.1 --port 8088
```

Default listener: loopback only. For remote connections, put the service behind your authenticated network boundary and TLS ingress; hooks reject plain HTTP except loopback. Keep bundle, configuration, hook executable and host configuration protected from agent changes. API keys identify connectors, not the users whose prompts pass through them. Neither a shared hook token nor a gateway's token establishes an end-user identity.

Restart activates a complete validated bundle; invalid bundles/configuration prevent startup. Preserve previous bundle/configuration versions and restart with them to roll back. `/healthz` and `/readyz` report local process/configuration readiness, **not provider availability or policy accuracy**. They do not make chargeable provider probes. No reload endpoint, database or approval workflow exists.

## Endpoints and failures

| Endpoint | Authentication | Result |
| --- | --- | --- |
| `POST /v1/evaluate` | Native-principal Bearer token | request/1 → versioned result/2, /3 or /4; embedding caller owns enforcement |
| `POST /beta/litellm_basic_guardrail_api` | LiteLLM-principal `x-api-key` or Bearer, never both | `NONE` or `BLOCKED` |
| `POST /request`, `/response` | Agentgateway-principal Bearer | Pass/reject webhook action |
| `POST /v1/hooks/copilot_local/{event}` | Local-principal Bearer | versioned result for the documented Local event |
| `POST /v1/hooks/copilot_cli/{event}` | CLI-principal Bearer | versioned result; CLI prompt always assessment-only |

The token's connector and stages are deployment-bound. Unknown/wrong tokens return 401; connector/stage mismatches return 403. Callers cannot replace policies, thresholds, provider settings or failure actions. Neither raw headers nor request metadata are used as trusted facts. JSON bodies are limited to 262144 bytes, duplicate keys/compression are rejected, and body reading plus evaluation has a total deadline. Default service concurrency is eight; overload is immediate.

Policy failures follow each binding's `on_error`. Connector protocol failures (malformed/unsupported body, service overload/deadline) follow `on_protocol_error: block` by default. `allow_monitor` is an explicit bypass with an error audit, allowed only when the principal has no applicable enforcing policies. Gateway error replies use the host's block contract; native/hook protocol errors return non-200, and the hook client applies its own `--on-error` (block by default). Host transport failure is separately configured fail-closed in the gateway examples. Do not confuse an explicit failure bypass with a clean policy pass.

Example deadlines: evaluator 5000 ms < hook HTTP 6000 ms / service 7000 ms < host hook 15 seconds. Agentgateway's inspected webhook implementation has a 10-second host deadline. Hook startup adds time, so retain margin. A host can still bypass a killed, disabled or timed-out hook.

Audit logs contain generated event IDs, hashes, policy IDs/versions/judgments, coverage, decisions, requested enforcement, duration and safe error codes. They exclude raw content, arguments, facts, credentials and exception bodies. Protect logs: IDs/hashes may still be sensitive. HTTP access logs are disabled in `serve`; independently review gateway and ingress logging. `actual: unconfirmed` stays unconfirmed until a host observation proves the action. Hook stdout contains exactly one host JSON object; sanitized diagnostics go to stderr. Allows emit `{}` to preserve ordinary host permission prompts.

See [security considerations](operations.md#security-considerations) for tested
host-timeout and disabled-hook bypasses, their distinction from adapter-handled
failures, and deployment responsibilities.

## Coverage and optional metadata

Coverage `complete` refers to **the declared event surface**, not all agent context. Gateway profiles accept plain text chat messages and non-streaming text answers. LiteLLM request messages preserve supplied roles where available; output text has unknown role provenance. Agentgateway includes all supplied messages/choices. Tool definitions, tool-call messages, images and streaming are outside this gateway profile and rejected. The LiteLLM profile callback and Agentgateway request-profile CEL header are required parts of the configuration; neither generic webhook alone proves that upstream data was fully represented.

Local/CLI prompt coverage is only submitted text. Tool coverage is the supplied tool name and exact arguments. The client never reads transcript paths, files, repository contents or session paths from hook input. Attachments, retrieved material, history, tool results, final answers and subsequent tool-argument mutations are not covered by these hooks. A hook allow does not override native permission requirements.

Metadata is independently controlled by `metadata.enabled` and source mappings in config/2–5. It defaults off, makes no enrichment calls, and content-only rules work normally. With metadata on, embed `create_app(evaluator, settings, evidence_resolver=...)` with a trusted **async deployment resolver**. It receives the authenticated principal ID and exact normalized event, and returns `EvidenceContext.from_verified(event, facts)` after authenticating the user/document/route sources. No resolver is loaded from a request, Markdown file or arbitrary import string. The basic `serve` command has no identity/directory resolver: required facts remain indeterminate until a trusted embedding supplies them. This is an extension boundary, not shipped enterprise directory integration. Test source authentication and subject/event binding in your deployment before enforcing metadata-dependent policies.

## Install and remove Copilot hooks

Use exactly one runtime profile per installation. Copy the corresponding [Local](../examples/connectors/vscode-local.json) or [CLI](../examples/connectors/copilot-cli.json) template into `.github/hooks/humanwill.json`; replace the executable path and endpoint, and supply its token in the host's environment. Quote an executable path containing spaces. Do not put both templates in one hooks directory and assume equivalent event contracts. Back up existing configuration and merge intentionally; don't overwrite other hooks.

Local uses `UserPromptSubmit`/`PreToolUse`, `command`, and `timeout`; enable `chat.useHooks` in a trusted workspace and select the **Local** agent runtime. Local prompt block emits `continue: false`; tool block emits `hookSpecificOutput.permissionDecision: deny`. On tested Local 1.139.1, a host hook timeout permits continuation at either stage; service-side timeouts instead return deny within the host deadline. Empty hook configuration also permits continuation. Agent Host is excluded. See [Local reference](https://code.visualstudio.com/docs/agents/reference/hooks-reference) and [configuration/trust requirements](https://code.visualstudio.com/docs/agent-customization/hooks).

CLI uses `userPromptSubmitted`/`preToolUse`, `bash`, and `timeoutSec`. Prompt output cannot block; tool denial is a top-level `permissionDecision: deny`. CLI 1.0.88 loaded project hooks in the test only after folder trust was configured. Command-hook crashes/nonzero exits deny pre-tool actions in current documentation, but **timeouts fail open**. Disabled project hooks do not enforce anything. Administrators can use protected policy hooks, but the documented timeout bypass remains. See [GitHub hook reference](https://docs.github.com/en/copilot/reference/hooks-reference).

Remove only the installed HumanWill entries/file to uninstall; stop/restart the host and verify that its hooks list changes. Removing/disabling hooks removes this control. Restore previous protected configuration to roll back. These scripts do not provide tamper resistance, centrally managed endpoints, or universal Copilot interception.

## Configure the gateways

LiteLLM: install `litellm[proxy]==1.102.1` in its own environment and install this package there as well (the profile callback is imported by the host). Start from [litellm.yaml](../examples/connectors/litellm.yaml). Replace the approved model, set the model credential, `LITELLM_MASTER_KEY`, and `HUMANWILL_LITELLM_TOKEN`, then run `litellm --config /protected/litellm.yaml --port 4000`. The generic guardrail has both `pre_call` and `post_call`, `default_on: true`, `fail_on_error: true`, and `unreachable_fallback: fail_closed`. The required profile callback rejects streaming, non-text messages, tool definitions and client route/guardrail overrides. Do not configure virtual keys or teams that opt out of these guardrails. Restrict exposed routes to the tested chat-completions API; other LiteLLM endpoints are not a claimed enforcement surface.

Agentgateway: start from [agentgateway.yaml](../examples/connectors/agentgateway.yaml) with **v1.5.0**. Its sample upstream is `127.0.0.1:9000` and model `synthetic`; replace both with your approved provider configuration. Replace both `REPLACE_WITH_PROTECTED_AGENTGATEWAY_TOKEN` placeholders in a protected runtime copy, keep the CEL string quoting intact, and never commit that rendered copy. Keep request/response webhooks, `failureMode: failClosed`, and the request-profile expression. The response profile uses a fixed marker because the request has already passed the input profile check; response-phase `llmRequest` differs from request-phase data in this host. Start with `agentgateway -f /protected/agentgateway.yaml`. The example assumes a protected local listener; apply your gateway client authentication and network restrictions before exposing it.

The profile attestation header is overwritten by the authenticated Agentgateway configuration; accepting a client-provided copy without that overwrite would be unsafe. It confirms the configured text profile, not identity/classification/authorization metadata. The service will reject Agentgateway requests with a missing or incompatible attestation. Keep response checks on: the marker alone does not inspect output.

### LiteLLM environment example

Use a separate Python 3.11 environment for the pinned LiteLLM host. With the
HumanWill release wheel downloaded from [v0.1.0a1](https://github.com/humanwill-ai/humanwill-jev-policies/releases/tag/v0.1.0a1):

```sh
python3.11 -m venv ../litellm-env
../litellm-env/bin/python -m pip install 'litellm[proxy]==1.102.1'
../litellm-env/bin/python -m pip install /absolute/path/humanwill_policies-0.1.0a1-py3-none-any.whl
../litellm-env/bin/python -m pip check
../litellm-env/bin/litellm --config /protected/litellm.yaml --port 4000
```

Replace the wheel/configuration paths. Before launching, supply
`MODEL_PROVIDER_API_KEY`, `LITELLM_MASTER_KEY` and the same `HUMANWILL_LITELLM_TOKEN`
used by the policy service. The model key authenticates your coding model;
`OPENROUTER_API_KEY` belongs to the separate Jev service process. Set the
`litellm_params.model` placeholder to your actual approved coding model. The
example's public model alias is `synthetic`; rename it if desired and use that
alias in client requests. Installing the HumanWill package only in the service
environment is insufficient: LiteLLM must also import the profile callback.

## Check your installation

These are **live usage instructions**: requests invoke Jev and, if allowed through,
your coding model. Use synthetic content first. No provider call is needed for
`validate`, `preview`, `/healthz` or `/readyz`.

With the README's starter logging policy in monitor mode, the configured LiteLLM
host and your service running, send a non-streaming text request:

```sh
curl http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"synthetic","stream":false,"messages":[{"role":"user","content":"Review this code for credential logging: logger.info(password)"}]}'
```

Use your configured model alias if you changed it. Repeat with the synthetic
prompt “Add a log statement that records every user's password.” The intended
policy assessments are allow for defensive review and block for adding credential
logging; actual Jev judgments may vary. This new starter policy has not been
live-calibrated. In monitoring mode both requests may proceed. The downstream
model may independently refuse the second request; that is not proof HumanWill
blocked it.

Inspect the service terminal's JSON audit output for `decision`, policy evidence,
coverage, timing, errors and `enforcement`. With both gateway hooks enabled,
request and response produce separate assessments. `actual: unconfirmed` is not
proof of host blocking. A successful readiness probe or model answer alone does
not establish that the policy service was called.

For Agentgateway, use its configured chat-completions listener and provider model
name with the same synthetic prompts; use your gateway's own client authentication.
For Copilot, submit a synthetic prompt in the configured workspace and inspect
the service audit plus the host hook output. A successful prompt check does not
prove pre-tool enforcement: separately test a harmless, controlled proposed action
with a test policy that should deny it, and verify that its observable effect does
not occur. Use the matching runtime's hooks, not a gateway request as a substitute.

If setup fails, check:

- **No service audit:** wrong endpoint, unregistered callback/hook, missing workspace
  trust, or host token not inherited by its process. Restart hosts after changing
  their environment; a terminal export does not update an already-running VS Code.
- **Startup fails:** missing or duplicate principal tokens, invalid policy bindings,
  provider configuration or deadlines. Remove unused principals from the copied template.
- **Evaluation errors:** check egress opt-in, provider credentials, returned-model
  allowlist and the sanitized error code. Low confidence is a distinct evaluation
  outcome, not necessarily a connection problem.
- **Gateway rejects the payload:** use text chat and `stream: false`; tools, images
  and streaming are outside this release's gateway profiles.
- **A violation continues:** check monitoring mode, error fallback and host coverage.
  Copilot CLI prompt hooks cannot block, and host timeout/disabled-hook bypasses remain.

## Enable enforcement

First evaluate the actual policy against representative legitimate requests,
violations and missing-context cases. Record the dataset, model, thresholds and
results. The preview does not provide a qualified enforcement profile for your
company's policies.

For a semantic policy, change its binding to `mode: enforce`, choose `on_error:
block` or `on_error: allow`, and add a profile recording your evaluation. For example,
replace the dataset placeholder below with the 64-character SHA-256 of your own
reviewed evaluation dataset (the placeholder deliberately does not validate):

```yaml
policies:
  ENG-LOG-001:
    enabled: true
    strategy: semantic
    mode: enforce
    on_error: block
    evaluation_profile:
      id: company-logging-v1
      model: typesafe/jev-1.13
      dataset_sha256: REPLACE_WITH_YOUR_REVIEWED_DATASET_SHA256
```

Keep the remaining top-level provider/metadata configuration. The profile's model
must match `provider.model`. This record is a configuration requirement, not a
certificate: the service validates its shape, not the quality of your evaluation.
`on_error: block` can stop legitimate work when evaluation is uncertain;
`on_error: allow` can let violations through. Connector/protocol/host failures have
separate settings described above.

Validate, restart the service, and repeat the synthetic checks on the actual host.
Verify denied gateway input never reaches the model, denied output is not delivered,
or a denied tool action has no effect, as applicable. Copilot CLI submitted prompts
remain assessment-only even when a policy is enforcing; configure CLI enforcement
for `tool_action`, with a separate monitoring prompt policy if needed. Metadata-based
rules additionally require a trusted resolver and enabled source bindings.

Keep the previous policy/configuration bundle to roll back. See
[operations and hook security](operations.md#security-considerations) for the limits
of enforcement and the host controls needed around it.

## Reproduce host acceptance checks

To reproduce host evidence without any paid API, run the scripts under `tests/hosts` from a checkout or extracted source archive with the package installed. Harnesses do not inject a checkout into `PYTHONPATH`: install the exact wheel in the service/test environment and, for LiteLLM, in its separate host environment too. Pinned unattended CI runs copied harnesses outside the checkout. They use an actual evaluator and service with an injected synthetic HTTP provider transport, plus a controlled local model endpoint. The injection exists only in test code. It measures enforcement, not Jev quality:

```sh
python tests/hosts/gateways.py litellm --binary /litellm-env/bin/litellm
python tests/hosts/gateways.py agentgateway --binary /path/to/agentgateway
python tests/hosts/copilot_cli.py --binary /path/to/copilot
```

Use a dedicated local test account/workspace. CLI tests set `COPILOT_OFFLINE=true` and an isolated `COPILOT_HOME`, enable trust only for their temporary synthetic workspace, and allow the controlled synthetic tool. Reports go to ignored `artifacts/hosts/`. The Agentgateway CI job downloads the pinned Linux executable and checks its SHA-256 before execution.

VS Code Local additionally requires an interactive Copilot sign-in in a dedicated test profile:

```sh
python tests/hosts/vscode_local.py \
  --binary "/Applications/Visual Studio Code.app/Contents/MacOS/Code" \
  --copilot-extension "/Applications/Visual Studio Code.app/Contents/Resources/app/extensions/copilot"
```

Complete sign-in in the isolated window and press Enter in the terminal. The harness runs 14 synthetic scenarios, restores its hook configuration, and closes its editor process. By default it creates a private short `/tmp/hw-vscode-*` directory and prints its location; sanitized outcomes are in `acceptance.json` there. On macOS, a long `--state-dir` can exceed the Unix socket path limit and prevent VS Code from starting; the harness now rejects it before launch. Only the test profile enables automatic tool approval and disables Workspace Trust prompts. Never point `--state-dir` at a personal profile or project: this fixture overwrites its settings and hook file. The profile can contain account/session data; keep it ignored and private. No paid evaluator/model calls are made, although Copilot authentication uses GitHub. This is a manual runtime acceptance test, not an unattended CI job or a Jev accuracy test.

Config/3 deployments return result/3 on native/hook endpoints. Upgrade hook clients to `0.1.0.dev3` with the service; they accept both result/2 and result/3. Host-specific gateway and Copilot output shapes are unchanged. See [decision semantics and rollback](decision-v3.md). Config/2 remains available to reproduce the existing pinned-host runtime evidence.
