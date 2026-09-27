# Steps 4–5 integration evidence

2026-09-27 · private development version `0.1.0.dev2`

**Step 4 is implemented and exercised on both real gateway processes. Step 5 software is implemented; Copilot CLI has real-runtime evidence, while VS Code Local's real-runtime gate remains open.** This is not a public-release or enterprise-readiness declaration.

The owner waived direct TypeSafe's separate live smoke as a v0.1 requirement. Both transport contract suites remain, and the earlier OpenRouter live smoke passed. **No paid provider calls were made for steps 4–5**; recorded total smoke spend remains $0.000024696 of the $5 cap.

## Implemented

- Authenticated Starlette/Uvicorn service with one frozen server-owned policy/configuration bundle, connector/stage-bound credentials, optional external-evaluation authorization, bounded JSON bodies, concurrency and total request deadlines.
- Health/readiness endpoints, safe structured audits and requested-versus-actual enforcement separation. Runtime results do not claim observed host enforcement.
- LiteLLM Generic Guardrail request/response endpoint plus the required text-profile pre-call callback; Agentgateway request/response webhooks with a required authenticated profile attestation.
- Separate Local and CLI hook parsers and outputs, bounded HTTP client, no transcript/file reads, no Jev credentials in hooks. CLI prompt assessment cannot request enforcement; allow preserves native permissions.
- Metadata remains independently switchable. The trusted in-process resolver is never invoked with metadata off. Default service has no directory/classification resolver; missing required facts remain errors.
- Configuration templates, installation/removal/rollback instructions, host-process reproduction scripts and a pinned Agentgateway Linux CI job.

See [operation and coverage reference](service-and-connectors.md).

## Real host observations

Tests use the actual service, decision engine and Jev HTTP adapter, with an injected **synthetic provider HTTP transport**, plus a controlled local OpenAI-compatible downstream. No Jev accuracy or latency claim follows from these tests. Test-only enforcement profiles are explicitly synthetic; shipped demo policies remain monitoring-only.

| Host | Exact environment | Observations |
| --- | --- | --- |
| LiteLLM | `1.102.1`, macOS x86_64/Python 3.11.5 and Ubuntu 24.04 CI | Allowed request reaches downstream; denied request does not; denied response is withheld. Monitor mode permits while assessing. Provider errors/timeouts at both stages block in enforce mode; a service outage prevents downstream invocation. Unsupported streaming/images/tools and client guardrail-control attempts are rejected. Earlier messages are inspected. |
| Agentgateway | `v1.5.0`, Linux amd64, Ubuntu 24.04 Actions runner | Same request/response allow/deny/monitor/provider-failure and unsupported-profile checks. Host returns 403 for policy rejection. [Pinned-host run](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/36319141577) records the initial full text-profile cases. The [expanded run](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/36319484745) includes response errors/timeouts, metadata bypass attempts and service outage. |
| Copilot CLI | `1.0.88`, macOS x86_64 and Ubuntu 24.04 CI, offline BYOK and isolated trusted workspace | Controlled file is created on allow and absent on tool deny/service failure. A blocked prompt assessment still allows the subsequent permitted action. A one-second host hook timeout and `disableAllHooks` both permit the controlled action. Six scenarios passed. |
| VS Code Local | editor `1.139.1` (`04c0d99f4fb0d8afe6ce4f0c58e31e183ac3e4b1`), bundled Copilot Chat `0.67.0` | Adapter/unit contracts pass. Attempted an isolated editor profile with a synthetic model/tool extension. Copilot logs reported missing token/sign-in, and no synthetic model/tool execution occurred. This is **inconclusive**, not evidence of a successful block. Actual Local allow, prompt-stop, tool-deny and host-bypass checks remain required. |

Agentgateway binary SHA-256: `daca5cda76e8c5ab0c1a75912fecf2d6365095403f810db72029c49d14a37e7b`. No Darwin x86_64 release asset exists for this version; Linux Actions provided the executable test environment.

CLI folder trust mattered: the first untrusted temporary workspace did not load hooks and the controlled action ran. After explicitly trusting only that synthetic workspace, hook events were observed and the allow/deny cases passed. This reinforces the documented trust/deployment boundary rather than demonstrating mandatory endpoint enforcement.

## Automated contracts and checks

98 unit/contract tests pass on local Python 3.11.5 and 3.14.0. The implementation at `8b1479c` passed all four Ubuntu/macOS × Python 3.11/3.14 [CI jobs](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/36319706556), plus all three Linux [real-host CI jobs](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/36319706538) for LiteLLM, Agentgateway and Copilot CLI. New cases cover connector authentication, wrong connector/stage, request-supplied policy/metadata spoofing, monitoring and policy fail-open distinctions, unsupported/version-mismatched payloads, duplicate JSON keys, compression, oversize/slow bodies, overload, disclosure opt-in, metadata resolver off/missing/verified, hook result binding and safe stdout/stderr. Lint and runtime dependency audit pass. The CI builds and installs the actual wheel outside the checkout. A separate fresh local wheel environment also passed demo creation, `serve` startup/readiness, unauthorized-request rejection and an authenticated no-egress evaluation; it made no provider call.

Host scenarios and reports are generated by `tests/hosts/gateways.py` and `tests/hosts/copilot_cli.py`; local raw artifacts stay ignored under `artifacts/hosts/`. Run them again against the release candidate and record its commit, environment and outcome. Do not infer support on other versions/OSes from these results.

## Remaining Local acceptance procedure

Use a separate **signed-in Copilot Local** test profile, a trusted disposable workspace, the exact pinned editor/extension, and a synthetic local model if available. Start `python tests/hosts/manual_service.py` (no hosted evaluator calls); set the printed synthetic token only in the test host's environment. Install the Local template with the current Python environment's absolute executable path. A synthetic `HW_DENY` marker triggers denial in this fixture.

Record the following with an allow control and service-side event evidence; absence of a tool side effect alone is insufficient if the agent never ran:

1. Allowed prompt reaches the synthetic model; submitted `HW_DENY` prompt stops before its model invocation.
2. Allowed tool creates a disposable marker; denied tool arguments containing `HW_DENY` never create that marker.
3. Service outage produces deny while the command completes within its host deadline.
4. Unsupported/malformed input produces deny; monitor verdict preserves ordinary permissions.
5. Host timeout and disabled/untrusted hooks have their actual observed outcome documented.

Do not substitute Agent Host, cloud or CLI behavior for these Local checks. No customer data, real payment action, destructive tool, or paid model is needed for the controlled fixture.

## Sources inspected

Reviewed current primary documentation and pinned host source on 2026-09-27:

- [LiteLLM Generic API](https://docs.litellm.ai/docs/adding_provider/generic_guardrail_api), plus installed `litellm==1.102.1` generic guardrail and custom-guardrail implementations. `api_key` sends `x-api-key`; fail-closed options must remain enabled.
- [Agentgateway v1.5.0 webhook source](https://github.com/agentgateway/agentgateway/blob/v1.5.0/crates/agentgateway/src/llm/policy/webhook.rs), [policy source](https://github.com/agentgateway/agentgateway/blob/v1.5.0/crates/agentgateway/src/llm/policy/mod.rs), and [configuration schema](https://github.com/agentgateway/agentgateway/blob/v1.5.0/schema/config.json). Request and response CEL contexts differ; the supported template was adjusted and tested accordingly.
- [GitHub hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference), [CLI BYOK](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-byok-models), and the installed CLI's environment/help reference. Current command pre-tool errors fail closed; timeouts remain fail-open. Do not apply that statement to every hook type or HTTP hooks.
- [VS Code Local reference](https://code.visualstudio.com/docs/agents/reference/hooks-reference), [hook configuration](https://code.visualstudio.com/docs/agent-customization/hooks), and [pinned hook service source](https://github.com/microsoft/vscode/blob/04c0d99f4fb0d8afe6ce4f0c58e31e183ac3e4b1/extensions/copilot/src/extension/chat/vscode-node/chatHookService.ts). Source inspection and fixtures do not close the real-runtime gate.
