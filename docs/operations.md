# Operate, upgrade and troubleshoot

Applies to `0.1.0.dev3`, Linux/macOS and the pinned [compatibility matrix](compatibility.md). Use [installation](quickstart.md) and the [service/connector guide](service-and-connectors.md) first. All shipped company examples remain monitoring-only; no calibrated enforcement profile is supplied.

## Establish a known deployment

Record the installed package version and artifact SHA-256, exact policy/configuration hashes from validation, host versions, enabled stages, provider route/model allowlist, trusted evidence sources, and timeout/failure settings. Keep the executable, bundle, config and hook registration protected from agents. Deploy distinct secrets per service principal. Connector tokens authenticate the calling integration; they do not authenticate the human whose request is being evaluated.

Logs exclude raw content, arguments, facts, credentials and exception bodies, but IDs/hashes and policy identifiers still need access control and a retention choice. Preview prints source text; do not capture it in routine shared logs. Review host/ingress logging separately. Hosted evaluation transmits applicable policy text and content externally when explicitly enabled. Installing the service locally does not change that data flow.

`GET /healthz` and `/readyz` indicate process/configuration readiness. They do not spend tokens, contact Jev, or establish accuracy. No automatic provider retry, route fallback, database, live reload or approval queue exists. Treat provider errors, overload and explicit failure bypasses as separate metrics from policy violations. Record real host outcomes separately from requested enforcement; an evaluator response cannot prove an action was stopped.

## Upgrade and roll back

1. Preserve the previous exact package artifact, complete policy folder and configuration, protected hook/gateway files, and evidence hashes. Build a fresh virtual environment for the new artifact; never replace a running environment piecemeal.
2. Validate the candidate bundle/configuration and reproduce the offline demo plus relevant connector scenarios. Upgrade hooks with the service when using config/3 results; `0.1.0.dev3` clients accept result/2 and result/3.
3. Start the candidate on a separate protected loopback port and check readiness and authentication. A policy/configuration error must prevent startup. Exercise synthetic allow/deny/error cases on the actual selected host before shifting traffic. Readiness alone is insufficient.
4. Point the protected connector configuration to the validated instance, restart the affected host where required, and confirm both coverage and actual enforcement. Observe latency, provider errors and user false blocks. Monitor mode assesses decisions without requesting a policy block; protocol failures still have their explicit configured behavior.
5. If checks regress, restore the previous package environment **and its matching whole bundle/configuration**, reconnect the hosts, and repeat the smoke checks. Do not mix thresholds or config/3 settings with an incompatible old client. Retain the failed candidate evidence for diagnosis.

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
