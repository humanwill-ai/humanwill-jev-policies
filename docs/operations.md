# Operate, upgrade and troubleshoot

Applies to candidate `0.1.0a1`, Linux/macOS and the pinned [compatibility matrix](compatibility.md). Use [installation](quickstart.md) and the [service/connector guide](service-and-connectors.md) first. All shipped company examples remain monitoring-only; no calibrated enforcement profile is supplied.

## Establish a known deployment

Record the installed package version and artifact SHA-256, exact policy/configuration hashes from validation, host versions, enabled stages, provider route/model allowlist, trusted evidence sources, and timeout/failure settings. Keep the executable, bundle, config and hook registration protected from agents. Deploy distinct secrets per service principal. Connector tokens authenticate the calling integration; they do not authenticate the human whose request is being evaluated.

Logs exclude raw content, arguments, facts, credentials and exception bodies, but IDs/hashes and policy identifiers still need access control and a retention choice. Preview prints source text; do not capture it in routine shared logs. Review host/ingress logging separately. Hosted evaluation transmits applicable policy text and content externally when explicitly enabled. Installing the service locally does not change that data flow.

`GET /healthz` and `/readyz` indicate process/configuration readiness. They do not spend tokens, contact Jev, or establish accuracy. No automatic provider retry, route fallback, database, live reload or approval queue exists. Treat provider errors, overload and explicit failure bypasses as separate metrics from policy violations. Record real host outcomes separately from requested enforcement; an evaluator response cannot prove an action was stopped.

## Security considerations

### Hook enforcement depends on the host

The adapter can request a block only when the host invokes the hook and receives
its result in time. A fail-closed adapter configuration does not make the host
itself fail closed when it skips a hook or stops waiting for it.

The fresh `0.1.0a1` acceptance run on **VS Code Local 1.139.1 / Copilot Chat 0.67.0,
macOS x86_64**, observed the following with controlled synthetic model/evaluator
responses and a tool that creates a disposable marker file:

| Situation | Observed host outcome |
| --- | --- |
| Hook returns a policy denial within the host deadline | Submitted prompt stops before model invocation, or the proposed tool action is prevented |
| Provider/service failure is handled and the hook returns denial within the host deadline | Operation is blocked under the tested failure configuration |
| VS Code's hook deadline expires before the hook finishes | Host continues; the controlled action executes |
| Hook registrations are removed | No policy check runs; the controlled action executes |
| Hook registrations are restored | Policy denial prevents the controlled action again |

For the host-timeout tests, the harness delayed the hook command by **three seconds**
while setting the host deadline to **one second**. Both `UserPromptSubmit` and
`PreToolUse` tests recorded an explicit host timeout and subsequent marker creation.
The disabled-hook test used an empty hook configuration; it did not test every
possible administrative switch or workspace-trust setting. See the
[sanitized acceptance evidence](evidence/preview-vscode-local-2026-09-30.json)
and [verification report](preview-verification.md).

Policy `on_error: block` and the hook client's `--on-error block` govern failures
those components can handle. They cannot force VS Code to wait, invoke an absent
hook, or honor an output it has stopped waiting for. Treat provider timeouts,
host timeouts and disabled hooks as separate operational conditions. These observed
Local semantics must not be assumed for every Copilot runtime or future version;
CLI has its own [contract and evidence](service-and-connectors.md#install-and-remove-copilot-hooks).

### Deployment implications

Keep policy bundles, service configuration, hook executables and registrations
protected from agents and users who must not change the control. Budget for
provider evaluation, any bounded follow-up, HTTP and process startup so the hook
can return before the host deadline; larger timeouts reduce accidental expiry but
do not eliminate bypasses. Retest actual host behavior after upgrades or changes
to configuration.

Monitor host hook loading and timeout diagnostics as well as service assessments.
A skipped hook may produce no service event, so silence in service logs is not
proof of compliance. Such host monitoring and protected endpoint administration
are deployment responsibilities, not automatic capabilities of this service.

These hooks alone do not guarantee mandatory company-policy enforcement. Where a
control must remain effective even if an endpoint hook is skipped or disabled,
apply authorization or restrictions at the actual tool, resource, execution or
network boundary as appropriate. Such controls require separate implementation
and validation; this adapter does not supply them. An `allow` result covers only
the inspected event and does not authorize later actions or unseen content.

## Upgrade and roll back

1. Preserve the previous exact package artifact, complete policy folder and configuration, protected hook/gateway files, and evidence hashes. Build a fresh virtual environment for the new artifact; never replace a running environment piecemeal.
2. Validate the candidate bundle/configuration and reproduce the offline demo plus relevant connector scenarios. Upgrade hooks and strict result-schema clients with the service, including result/4 follow-up audit fields and profile enums.
3. Start the candidate on a separate protected loopback port and check readiness and authentication. A policy/configuration error must prevent startup. Exercise synthetic allow/deny/error cases on the actual selected host before shifting traffic. Readiness alone is insufficient.
4. Point the protected connector configuration to the validated instance, restart the affected host where required, and confirm both coverage and actual enforcement. Observe latency, provider errors and user false blocks. Monitor mode assesses decisions without requesting a policy block; protocol failures still have their explicit configured behavior.
5. If checks regress, restore the previous package environment **and its matching whole bundle/configuration**, reconnect the hosts, and repeat the smoke checks. Do not mix thresholds or configuration/profile settings with an incompatible old client. Retain the failed candidate evidence for diagnosis.

A stopped/unreachable service should trigger the configured gateway fail-closed behavior or hook error output, but a host can bypass a timed-out/disabled hook. Switching off hooks removes the control; it is not equivalent to successful evaluation. There is no transparent zero-downtime or tamper-resistance guarantee. An invalid new bundle does not hot-replace a live bundle: it is rejected when starting the new process. The packaging verifier exercises startup, invalid configuration rejection, and restoration/restart of the previous configuration.

## Troubleshooting

| Symptom | Check and resolution |
| --- | --- |
| `destination_exists` from `init-demo` | Select a new directory; initialization intentionally refuses to overwrite files. |
| `invalid_configuration`, unknown/disabled source, missing binding | Validate the full selected bundle and its matching configuration. Bind every policy; explicitly disable or monitor rules whose trusted evidence is unavailable. Never remove a requirement merely to make validation pass. |
| Missing credentials or `provider_auth` | Set the provider's configured environment variable in the service process. Offline validation needs no key. Never put the key in Markdown, logs or hook JSON. |
| `egress_not_authorized` | External disclosure is disabled. Review the intended route/content and explicitly enable it only after authorization. Readiness remains healthy because it does not probe the provider. |
| 401/403 from service | Check the configured principal's token, connector and stages; caller policy/role claims do not override these settings. Each principal needs a distinct ASCII token of at least 32 characters. |
| Unsupported content or gateway block | Check the required LiteLLM callback / Agentgateway profile header, text-only messages, no tool definitions and non-streaming response profile. Do not strip unseen content and mark coverage complete. |
| Required fact is unknown despite request metadata | The `serve` command does not trust wire metadata. Supply an authenticated embedding resolver, correct source/event bindings and freshness, or explicitly disable the dependent rule. |
| A hook allows after a timeout | This is a documented host bypass. Keep evaluation < service/client < host deadlines with startup margin. Test the actual pinned runtime; this service cannot change host timeout semantics. |
| CLI submitted prompt continued after a violation | CLI's submitted-prompt hook is assessment-only. Use supported pre-tool checks for action enforcement; Local has a different prompt-stop contract. |
| VS Code has no hook activity | Select Local, enable hooks, establish workspace trust and Copilot sign-in, then verify the registered hooks. Agent Host and other interfaces are outside this profile. |
| A permitted request later discloses data | Prompt permission is scoped to that event. Inspect the response/action at its governed stage and verify actual target/operation approval; a coding-model approval is not onward-sharing approval. |
| Container cannot read mounted policies/config | Numeric UID 65532 needs file-read and parent-directory-traverse permissions; use protected read-only mounts and appropriate SELinux labels. |
| A rule falsely blocks useful work | Preserve policy/config/model versions and a privacy-reviewed example, review expected labels, then test changes on development data. Do not tune on a held-out set and report it as unseen. |

Sanitized error codes and bounded coverage are intentional. Logs are not a transcript recovery mechanism. Share only reviewed synthetic reproduction material in public issues; publication and the security reporting channel are separate release gates.
