# HumanWill Jev Policies

**Turn company policies into runtime checks.**

**“Help me review this code. Don’t upload it to an unapproved destination.”**

Your AI provider’s safeguards don’t know your company’s rules. HumanWill Jev
Policies lets you write those rules in Markdown and check AI activity against them
through LiteLLM, Agentgateway, and supported GitHub Copilot hooks.

Powered by Jev’s semantic evaluation, it adds a company-controlled security layer
to your **software development lifecycle (SDLC)**—with **378 ms median added
latency for prompt checks in our controlled tests**. Start by monitoring, then
enable blocking where supported.

**0.2 Public Beta (`0.2.0b1`) — for controlled company pilots.**
The beta adds optional non-streaming tool-proposal inspection and MCP
pre-execution enforcement through LiteLLM and Agentgateway. It keeps monitoring
defaults and explicit failure handling; it is not an enterprise-qualified control.
See [beta scope, upgrade and validation](docs/public-beta-v020.md).

Install [v0.2.0b1](https://github.com/humanwill-ai/humanwill-jev-policies/releases/tag/v0.2.0b1)
using the walkthrough below or the [release artifacts](docs/public-beta-v020.md#install-or-upgrade).
Coverage varies by connector; use alongside other security controls. The quoted
latency and [170-case results](docs/preview-final-v1-report.md) belong to the earlier
text-policy workload, not a fresh beta/tool/MCP qualification.

This is a companion to [HumanWill Benchmark](https://github.com/humanwill-ai/humanwill-benchmark):
the benchmark studies model behavior; this project lets companies supply their own
policies. Allowing a request here cannot force a downstream model to answer.

## What's new in 0.2 Public Beta

- **Non-streaming structured tool-call inspection:** check proposed tool names
  and arguments before returning them to the agent, through
  [LiteLLM or the Agentgateway relay](docs/structured-tool-calls.md).
- **MCP pre-execution enforcement for LiteLLM and Agentgateway:** check actual
  tool invocations before forwarding them to the MCP server. See
  [LiteLLM setup](docs/mcp-pre-execution.md) and
  [Agentgateway setup](docs/agentgateway-mcp.md).

Both features require explicit configuration. See the [full changelog](CHANGELOG.md)
for the other beta changes.

### TODO: streaming support

- [ ] Add streaming support in a future release, with inspection of streamed
  tool calls and policy-governed responses before releasing restricted content.
  Validate buffering, cancellation and latency trade-offs. Streaming is **not
  supported in this beta**; see the [planned work](docs/next-action-plan.md#3-streaming-with-tested-buffering-and-blocking).

## Use with your AI tools

Run HumanWill as a policy service next to your gateway or coding agent. Your host
sends the covered content to the service; the service evaluates your policies with
Jev and returns a decision. The host applies that decision where enforcement is
supported. Jev is the evaluator, not a replacement for your coding model.

See **[Architecture and request flows](docs/architecture.md)** for numbered diagrams
of LiteLLM, Agentgateway and Copilot, including model requests/responses, MCP
execution and the policy checks at each boundary.
The guide displays PNG diagrams directly on GitHub, with editable Mermaid source
in expandable sections.

### 1. Install the released version

Use Python 3.11–3.14 on Linux or macOS. The preview is available on GitHub, not PyPI.
This installs the released source and includes the connector templates:

```sh
git clone --branch v0.2.0b1 --depth 1 https://github.com/humanwill-ai/humanwill-jev-policies.git
cd humanwill-jev-policies
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install --no-deps .
humanwill-policies --version
```

Prefer a release wheel? Follow [artifact installation](docs/quickstart.md).
You do not need the development dependencies or HumanWill Benchmark.

### 2. Write your policies

Create a separate folder for your company rules:

```sh
mkdir -p ../company-policies
```

Save this as `../company-policies/policies.md`:

```markdown
---
kind: collection
id: COMPANY
version: "1"
includes: [credential-logging.md]
---
Company development policies.
```

Save this as `../company-policies/credential-logging.md`:

```markdown
---
kind: policy
id: ENG-LOG-001
version: "1"
title: Keep credentials out of application logs
stages: [prompt, model_request, tool_action, response]
---
Do not add code that writes passwords, API keys or access tokens to application
logs. Reviewing existing code to identify or remove such logging is permitted.
```

This is a content-only starting example, not a prevalidated company policy.
Add more files through `includes`, including collections in subfolders. Each rule
needs a stable ID and a configuration entry. See [policy authoring](docs/policy-authoring.md).

### 3. Configure Jev and start the service

Save `../company-policies/config.yaml` with the matching policy ID:

```yaml
format: humanwill.config/5
metadata:
  enabled: false
provider:
  transport: openrouter
  model: typesafe/jev-1.13
  accepted_models: [typesafe/jev-1.13-20260917]
  api_key_env: OPENROUTER_API_KEY
policies:
  ENG-LOG-001:
    enabled: true
    strategy: semantic
    mode: monitor
    on_error: block
```

Supply `OPENROUTER_API_KEY` through your local environment or secret manager.
The model identifiers above are the tested release profile; unexpected returned
models are rejected. [Direct TypeSafe configuration](docs/service-and-connectors.md#run-the-service)
is also supported. Live checks use your provider account and incur API charges.

Copy the service template:

```sh
cp examples/connectors/service.yaml ../company-policies/service.yaml
```

In that copy, keep only the `principals` for the integrations you will use. Set
each retained principal's `token_env` variable to a different random secret of
at least 32 ASCII characters, and supply the same token to its gateway or hook.
These tokens authenticate connectors; they are separate from the Jev API key.
For example, if you keep only `litellm`, generate its token in the service shell:

```sh
export HUMANWILL_LITELLM_TOKEN="$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

Set `allow_external_evaluation: true` in `service.yaml` only after approving the
data flow: **active policy text and inspected content are sent to hosted Jev
through OpenRouter**. Protect these files from agent edits and keep secrets out
of source control. Then run:

```sh
humanwill-policies validate ../company-policies --config ../company-policies/config.yaml
humanwill-policies serve ../company-policies \
  --config ../company-policies/config.yaml \
  --service-config ../company-policies/service.yaml \
  --host 127.0.0.1 --port 8088
```

Keep this process running. In another terminal, `curl http://127.0.0.1:8088/readyz`
checks local readiness; it does not test the provider or policy accuracy.

### 4. Connect your gateway or coding agent

Choose the matching setup below. The host process must receive its connector token
in its environment. The examples assume host and service share a machine;
containers or remote hosts need reachable addresses and a protected network/TLS setup.

| Integration | Setup | What to send through it |
| --- | --- | --- |
| **LiteLLM 1.102.1** | Install HumanWill in the LiteLLM environment too. Copy [litellm.yaml](examples/connectors/litellm.yaml), set your coding model and its credential, `LITELLM_MASTER_KEY`, and `HUMANWILL_LITELLM_TOKEN`. Keep both the profile callback and guardrail configuration. Start with `litellm --config /path/to/litellm.yaml --port 4000`. [Full setup](docs/service-and-connectors.md#configure-the-gateways). | Point your application's chat-completions client to `http://127.0.0.1:4000/v1`. Use text messages and `stream: false`; the text profile rejects structured tools and streaming. The beta offers a separate [tool profile](docs/structured-tool-calls.md) and [MCP binding](docs/mcp-pre-execution.md). |
| **Agentgateway 1.5.0** | Copy [agentgateway.yaml](examples/connectors/agentgateway.yaml). Replace the synthetic upstream/model with your provider configuration and both token placeholders with the service principal's token. Preserve both webhooks, the request-profile expression and fail-closed settings. Start with `agentgateway -f /path/to/agentgateway.yaml`. [Full setup](docs/service-and-connectors.md#configure-the-gateways). | Route text, non-streaming chat requests through the configured listener (example port `3000`). The sample upstream on port `9000` is a placeholder, not a supplied model service. The beta adds a [tool relay](docs/structured-tool-calls.md) and [MCP execution binding](docs/agentgateway-mcp.md). |
| **VS Code Local** | Merge the [Local hook template](examples/connectors/vscode-local.json) into your project's `.github/hooks/humanwill.json`. Replace the executable with the absolute path to `.venv/bin/humanwill-policies`; supply `HUMANWILL_LOCAL_TOKEN` to VS Code. Sign in to Copilot, enable `chat.useHooks`, trust the workspace and select the Local agent runtime. [Full setup](docs/service-and-connectors.md#install-and-remove-copilot-hooks). | Use Copilot in that workspace. Submitted prompts and proposed tool actions are checked; host timeouts and disabled hooks can bypass enforcement. |
| **Copilot CLI** | Use the separate [CLI hook template](examples/connectors/copilot-cli.json), replace the executable path and supply `HUMANWILL_CLI_TOKEN` to the CLI. Configure folder trust. Do not combine the Local and CLI templates as if their contracts were interchangeable. [Full setup](docs/service-and-connectors.md#install-and-remove-copilot-hooks). | Start Copilot CLI in the configured project. Prompt checks are assessment-only; pre-tool checks can deny actions. Host timeouts and disabled hooks can bypass enforcement. |

See [tested host versions](docs/compatibility.md) before using other versions.
For a copyable LiteLLM request and end-to-end verification, see
[check your installation](docs/service-and-connectors.md#check-your-installation).

### 5. Review decisions, then choose enforcement

The starter policy uses **monitoring**: policy assessments are logged but do not
block otherwise supported requests. Protocol errors can still block under the
connector's separate failure settings. Try a legitimate request such as
“Review this code for credential logging” and a violating one such as “Add a log
statement that records every user's password.” Inspect the service's JSON audit
output for decisions and errors, not just whether the host continued.

Before enabling blocking, evaluate representative examples of your own policies,
set an explicit error fallback, and verify actual host behavior. Enforcement needs
`mode: enforce` **and an `evaluation_profile`**, not just a mode switch. Follow the
[monitoring-to-enforcement procedure](docs/service-and-connectors.md#enable-enforcement).
Restart the service after policy/configuration changes to load the new bundle.

Rules involving employee groups, approved destinations or document classifications
also need a [trusted metadata integration](docs/optional-metadata.md). Metadata is
optional, but the basic service does not supply an identity/destination resolver;
a prompt claiming approval is not proof. Start with content-only policies when
you do not yet have that integration.

## Try the offline demo instead

Use Python 3.11–3.14 on Linux or macOS, from this checkout:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install --no-deps .
humanwill-policies init-demo ./demo
humanwill-policies validate ./demo --config ./demo/config.yaml
humanwill-policies preview ./demo --config ./demo/config.yaml
humanwill-policies evaluate ./demo --config ./demo/config.yaml \
  --request ./demo/request.json --mock-answers ./demo/mock-answers.json --json
```

Installation downloads dependencies. The demo itself runs offline with scripted
answers and no credentials. It enables one content-only monitoring rule, keeps
metadata off, and explicitly disables rules needing trusted facts. Use a fresh
destination for `init-demo`. See [exact-artifact installation](docs/quickstart.md).

## Policies and runtime flow

A `policies.md` collection explicitly includes Markdown policies or nested
collections within one folder. Each policy has a stable ID, version, title, stages
and rule text. The service loads an immutable bundle; callers cannot replace its
policies, thresholds or permissions. See [policy authoring](docs/policy-authoring.md).

Config/5 sends the covered request, response or proposed action alongside the
actual Markdown policies and reusable evaluation questions. Our selected
development profile, optional `policy_assessment: q05_stage_aware`, uses a
**first assessment followed by at most one additional Jev call when needed**:

1. **Assess with Q05**, the general question about whether the supplied operation
   falls within a policy's restrictions. Trusted authorization checks remain in
   deterministic code.
2. **Follow up only on eligible low-confidence answers** that leave the combined
   result as `evaluation_error`. For a connector-reported `tool_action`, ask more
   directly about the proposed tool and its arguments. For other stages, use Q04,
   an alternative general wording. The policies and supplied content stay the same;
   the adapter does not ask Jev to select a smaller policy set or infer tool use
   from a prompt mentioning a tool.
3. **Accept the follow-up only if it agrees with the original scope choice and
   meets the configured confidence threshold.** Already accepted answers stay
   unchanged. Unresolved results remain `evaluation_error`, handled by the
   configured allow/block fallback and monitoring mode.

This is not a retry for every error: explicit `insufficient_evidence`, missing
trusted facts, malformed primary replies and transport failures are not eligible.
The extra call shares the original deadline and resource limits. Follow-ups are
opt-in; omitting the profile retains the standard single-assessment behavior.
See [the exact questions and limits](docs/bounded-policy-followup.md).

Metadata is independently switchable. When enabled, a trusted application resolver
must provide identity, approvals or classifications. Prompt claims and model guesses
never establish authorization. The included approved-software-source catalog and
matcher are research/reference fixtures, **not a production dependency, redirect or
artifact-provenance resolver**. See [optional metadata](docs/optional-metadata.md)
and [approved sources](docs/approved-software-sources.md).

## Connector scope

| Connector | Supported inspection | Important boundary |
| --- | --- | --- |
| LiteLLM | Text model requests and non-streaming responses | Requires the documented guardrail and text-profile callback; no streaming, images or tool-call transport in this profile |
| Agentgateway | Text request/response webhooks | Requires the supplied authenticated profile and CEL configuration |
| VS Code Local | Submitted prompts and proposed tool actions | Host timeouts, disabled hooks and workspace configuration can bypass checks |
| Copilot CLI | Submitted-prompt assessment and pre-tool checks | Prompt-hook output cannot block; host timeouts and disabled hooks can bypass tool checks |

Use [connector setup and removal](docs/service-and-connectors.md),
[pinned compatibility and evidence](docs/compatibility.md), and
[operations and rollback](docs/operations.md). These are specific tested profiles,
not universal interception of Copilot or every gateway payload.

## Security considerations

**Use this service as one layer of defense.** Policy violations can still pass
through because of model mistakes, prompt injection, missing context, unchecked
stages, host bypasses or an error fallback configured to allow. Combine policy
evaluation with independently enforced access controls, least-privilege tool
permissions, sandboxing, approved network destinations and approval requirements
for sensitive actions. Checking a prompt does not establish that later tool actions
or generated responses are safe; check those stages where supported.

In our [final development-pack evaluation](docs/preview-final-v1-report.md),
**509/510 outcomes matched expectations (99.8%)** across three passes of 170
distinct cases. All **246 known-violation observations** produced a block decision;
none was incorrectly allowed. These were assessments in monitoring mode, not
measurements of actual host blocking or a production enforcement success rate.
There were 36 expected uncertain outcomes and one unexpected abstention on a
legitimate request. An allow-on-error fallback permits uncertain requests; a
block-on-error fallback can stop legitimate work. The pack was used for tuning,
known difficult cases were removed, and repeated passes are not independent
examples. These results do not establish the rate of violations that would escape
in deployment; validate your own policies, traffic and failure settings.

**Jev is not immune to prompt injection.** TypeSafe's official
[Jev 1.13 guidance on adversarial content](https://docs.typesafe.ai/model-jaggedness/jev-1.13#adversarial-content)
explains that supplied state is not treated as hostile by default and that injected
instructions, misleading framing or content arguing for its own classification
can influence the answer (verified 2026-10-01). Typed output does not make the
judgment trustworthy by itself. Keep policy/configuration and trusted authorization
facts outside requester control, and test adversarial inputs as well as legitimate
workflows.

Before relying on **Visual Studio Code Local agent hook enforcement**, read the
[hook security considerations](docs/operations.md#security-considerations): host
timeouts, disabled or removed hooks, and workspace configuration can permit
continuation even when the adapter is configured to block errors. Copilot CLI has
a separate contract: its prompt hook is assessment-only, and its tool hooks also
have timeout/disabled-hook bypasses. Neither is a tamper-proof security boundary.

Jev is available through OpenRouter and direct TypeSafe. OpenRouter has live
synthetic evidence; direct TypeSafe has transport contract tests, with its separate
live smoke optional for this release. Hosted evaluation sends active policy text
and covered content outside your environment and requires explicit egress opt-in.
Self-hosting this service does not make hosted Jev local.

## Evaluation and limits

The active reviewed pack has **170 distinct cases**: 89 updated workflow cases,
46 approved-source cases and 35 previously approved cases. Policies are in
`evals/step6/policies-sources-v4`; the authoritative dataset pointer is
`evals/step6/release/active-pack.json`. Open the
[offline review page](docs/case-review.html) locally to inspect policies, context,
labels and recorded removals. [Review instructions](docs/case-review.md) explain
saved progress and export.

The [final report](docs/preview-final-v1-report.md) uses three fresh passes with the
same final policies and optional stage-aware profile. Repetitions measure stability,
not independent sample size. This pack was used for tuning, and known difficult
cases were removed by the owner; it is not an independent holdout. Original
statistical enforcement targets remain unqualified. Report false blocks, missed
violations and abstentions separately, including fallback consequences.

This service is not a shell security scanner, a full workflow observer, or a
complete defense against prompt injection. It sees only the stages and content its
connector supplies. Customer demand and enterprise suitability remain unvalidated.

## Performance and request latency

**Typical added latency in our test:** approximately **0.38 seconds** for prompt
checks, or **0.73 seconds** for prompt-and-response checks on the code-review
workload. These are median timings from our
[controlled 2026-10-01 comparison](docs/latency-paths-v1-report.md) with the current
four-policy profile. Checking the response adds another sequential evaluation;
a follow-up can add a third. Detailed measurements, including slower-request
timings (p95), are below.

| Warm gateway path | Samples | Jev calls per request | Median added delay | p95 added delay |
| --- | ---: | ---: | ---: | ---: |
| Prompt-only, meaningful code-review and warning workloads | 24 | 1 | 378 ms | 470 ms |
| Prompt + response, local code review without follow-up | 12 | 2 | 733 ms | 1,454 ms |
| Prompt + response, warning workload with a natural follow-up | 10 | 3 | 1,106 ms | 1,168 ms |

p95 means 95% of samples were at or below that duration. These are test observations,
not guaranteed service levels. Small samples and network
variation make tail estimates coarse: the lower p95 in the follow-up row does not
mean an extra call is faster. Timings use real LiteLLM 1.102.1, live Jev through
OpenRouter, serial requests, 128–12,000-character synthetic inputs, monitoring and
`q05_stage_aware`. Added delay subtracts matched baseline request timings; downstream
generation was mocked. The report includes all arms, errors and cold requests.

The warning response returned `evaluation_error` on all 13 attempts (including the
initial request): 11 low-confidence outcomes and two malformed model replies.
Its follow-ups did not resolve the uncertainty. The separately tested historical
placeholder also remained uncertain, with p95 added delay of 1,725 ms. This helps
explain the earlier roughly 1.8-second result; it is not the cost of every request
or evidence of successful response enforcement. Prompt-only checks cover less
than prompt-and-response checks, so select stages according to the policy's needs.

[Earlier hook measurements](docs/preview-latency-v1-report.md) were roughly
0.8–0.9 seconds median and up to 1.0 second p95 per hook execution, including
Python startup but excluding IDE/CLI scheduling. An agent turn can incur repeated
checks. Actual latency depends on workload, provider/network conditions and
follow-ups; production capacity and Agentgateway live-provider latency remain
unmeasured.

### Why we keep follow-up questions sequential

We also tested sending **Q05 and Q04 together, plus the tool-specific question for
tool-action events**, in the initial request. This would make alternative answers
available without a second API call. In our [2026-10-01 experiment](docs/fanout-v1-report.md),
however, it did not provide a compelling improvement:

| Measurement | Current sequential approach | Questions together |
| --- | ---: | ---: |
| Median evaluator latency | 356 ms | 375 ms |
| p95 evaluator latency | 518 ms | 498 ms |
| Total evaluator API cost | $0.0205 | $0.0454 |

Each approach evaluated the same **188 distinct cases twice (376 observations)**:
170 reviewed development cases and 18 new cases with provisional labels. These
are evaluator timings, including deterministic cases, not gateway added-delay
measurements from the table above. Batching reduced overall p95 by about 4%, but
slightly increased median latency and cost about **2.2 times as much**. It also
failed our separate quality gates. We therefore retain the current approach:
request an alternative question only when an eligible assessment needs it.
This result concerns the tested design and workload, not every possible batching
strategy; full results and limitations are in the linked report.

## Contribute to development

The commands below are for contributors changing the project, not for installing
or using the policy service. Run them from a source checkout in a virtual environment.

```sh
python -m pip install -r requirements-dev.txt
python -m pip install --no-deps --no-build-isolation -e .
ruff check src tests evals scripts
ruff format --check src tests evals scripts
python -m unittest discover -s tests
python -m build --no-isolation
```

Current guides and evidence are indexed in [release status](docs/preview-status.md).
Earlier dated reports preserve the development history and do not describe the
current profile unless explicitly stated. See the [publication record](docs/publication-v0.1.0a1.md)
for the exact release commit, assets and post-publication verification.

## License and contributions

Original software, documentation and synthetic examples use [Apache-2.0](LICENSE),
matching HumanWill Benchmark's software license. Company-authored policies and
inputs retain their existing rights; benchmark content and dependencies retain
their separate terms. See [license scope](LICENSING.md),
[third-party notices](THIRD_PARTY_NOTICES.md), [contributing](CONTRIBUTING.md) and
[private security reporting](SECURITY.md).
