# Steps 4–5 integration evidence

2026-09-27 · private development version `0.1.0.dev2`

**Steps 4–5 are implemented and exercised on both real gateways and both Copilot runtimes.** This is not a public-release or enterprise-readiness declaration.

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
| VS Code Local | editor `1.139.1` (`04c0d99f4fb0d8afe6ce4f0c58e31e183ac3e4b1`), bundled Copilot Chat `0.67.0` | macOS x86_64, signed-in isolated trusted workspace, synthetic model/tool extension. Fourteen scenarios passed: allowed action executes; prompt denial stops before model invocation; tool denial prevents the marker. Provider/service failures and malformed inputs block. Monitoring permits. Host hook timeouts at either stage and empty hook configuration permit the action. Restoring hooks restores denial. |

Agentgateway binary SHA-256: `daca5cda76e8c5ab0c1a75912fecf2d6365095403f810db72029c49d14a37e7b`. No Darwin x86_64 release asset exists for this version; Linux Actions provided the executable test environment.

CLI folder trust mattered: the first untrusted temporary workspace did not load hooks and the controlled action ran. After explicitly trusting only that synthetic workspace, hook events were observed and the allow/deny cases passed. This reinforces the documented trust/deployment boundary rather than demonstrating mandatory endpoint enforcement.

## Automated contracts and checks

98 unit/contract tests pass on local Python 3.11.5 and 3.14.0. The implementation at `8b1479c` passed all four Ubuntu/macOS × Python 3.11/3.14 [CI jobs](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/36319706556), plus all three Linux [real-host CI jobs](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/36319706538) for LiteLLM, Agentgateway and Copilot CLI. New cases cover connector authentication, wrong connector/stage, request-supplied policy/metadata spoofing, monitoring and policy fail-open distinctions, unsupported/version-mismatched payloads, duplicate JSON keys, compression, oversize/slow bodies, overload, disclosure opt-in, metadata resolver off/missing/verified, hook result binding and safe stdout/stderr. Lint and runtime dependency audit pass. The CI builds and installs the actual wheel outside the checkout. A separate fresh local wheel environment also passed demo creation, `serve` startup/readiness, unauthorized-request rejection and an authenticated no-egress evaluation; it made no provider call.

Host scenarios and reports are generated by `tests/hosts/gateways.py`, `tests/hosts/copilot_cli.py` and `tests/hosts/vscode_local.py`; local raw artifacts stay ignored under `artifacts/hosts/`. Run them again against the release candidate and record its commit, environment and outcome. Do not infer support on other versions/OSes from these results.

## VS Code Local acceptance — 2026-09-27

The original attempt was inconclusive because Copilot sign-in had not completed. After the owner confirmed sign-in, the actual Local agent (`github.copilot.editsAgent`) executed the synthetic fixture. A permitted control made two local model calls and created the marker. The `HW_DENY` submitted-prompt case made **zero model calls**, produced no marker, and returned the visible “HumanWill policy check denied this operation” message. A denied tool made two model calls (proposal and final response) but never executed the tool.

| Scenario | Marker created | Local model calls | Service-observed stages |
| --- | --- | --- | --- |
| Allow control | Yes | 2 | Prompt, tool action |
| Submitted prompt denied | No | 0 | Prompt |
| Proposed tool denied | No | 2 | Prompt, tool action |
| Provider error / provider timeout during tool check | No | 2 each | Prompt, tool action |
| Service unavailable during tool check | No | 2 | Prompt |
| Service unavailable during prompt check | No | 0 | None |
| Malformed tool payload | No | 2 | Prompt |
| Malformed prompt payload | No | 0 | None |
| Monitoring with both denial markers | Yes | 2 | Prompt, tool action |
| Host times out tool hook (1 second) | Yes | 2 | Prompt |
| Host times out prompt hook (1 second) | Yes | 2 | Tool action |
| Empty hook configuration | Yes | 2 | None |
| Restored hooks, denied tool | No | 2 | Prompt, tool action |

Provider timeouts are handled inside the service and deny within the host deadline. **Host hook timeouts bypass enforcement on this Local version.** The latter tests delayed the hook command for three seconds with a one-second host timeout; the Hooks output confirmed timeout and the controlled action ran. Empty hook configuration tests removal of hook entries, not the separate `chat.useHooks` switch or untrusted-workspace behavior. No claim of mandatory endpoint enforcement follows.

Reproduce with [the interactive host harness](../tests/hosts/vscode_local.py) and [synthetic extension](../tests/hosts/vscode_fixture/extension.js), following the [connector guide](service-and-connectors.md). It uses a dedicated signed-in profile, trust disabled only for the disposable fixture, and automatic tool approval in that profile so an unrelated permission prompt cannot masquerade as policy enforcement. Normal adapter allow output still preserves native host permissions. The model and evaluator transports are synthetic; Copilot sign-in still contacts GitHub. No paid model or hosted Jev requests are involved. Editor account/session logs and all local artifacts remain ignored and private; only sanitized outcomes belong in this report.

These results close the Local runtime gate for steps 4–5 on the stated version/configuration. Semantic policy quality, release packaging, license and public-content review remain later gates.

## Sources inspected

Reviewed current primary documentation and pinned host source on 2026-09-27:

- [LiteLLM Generic API](https://docs.litellm.ai/docs/adding_provider/generic_guardrail_api), plus installed `litellm==1.102.1` generic guardrail and custom-guardrail implementations. `api_key` sends `x-api-key`; fail-closed options must remain enabled.
- [Agentgateway v1.5.0 webhook source](https://github.com/agentgateway/agentgateway/blob/v1.5.0/crates/agentgateway/src/llm/policy/webhook.rs), [policy source](https://github.com/agentgateway/agentgateway/blob/v1.5.0/crates/agentgateway/src/llm/policy/mod.rs), and [configuration schema](https://github.com/agentgateway/agentgateway/blob/v1.5.0/schema/config.json). Request and response CEL contexts differ; the supported template was adjusted and tested accordingly.
- [GitHub hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference), [CLI BYOK](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-byok-models), and the installed CLI's environment/help reference. Current command pre-tool errors fail closed; timeouts remain fail-open. Do not apply that statement to every hook type or HTTP hooks.
- [VS Code Local reference](https://code.visualstudio.com/docs/agents/reference/hooks-reference), [hook configuration](https://code.visualstudio.com/docs/agent-customization/hooks), and [pinned hook service source](https://github.com/microsoft/vscode/blob/04c0d99f4fb0d8afe6ce4f0c58e31e183ac3e4b1/extensions/copilot/src/extension/chat/vscode-node/chatHookService.ts). The isolated signed-in runtime tests above additionally confirm the stated Local behavior.
