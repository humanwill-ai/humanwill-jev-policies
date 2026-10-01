# HumanWill Jev Policies

Apply company-authored Markdown policies to AI requests, responses and proposed
tool actions through a shared service. Jev supplies semantic judgments; the adapter
combines them with deterministic rules and, when enabled, trusted metadata.

**Experimental developer preview candidate: `0.1.0a1`.** This repository is being
prepared for its first public release. It is not an enterprise-qualified policy
control. Examples default to monitoring; enforcement and error fallback are explicit
operator choices. See [current release status](docs/preview-status.md) and
[final development-pack evidence](docs/preview-final-v1-report.md).

This is a companion to [HumanWill Benchmark](https://github.com/humanwill-ai/humanwill-benchmark):
the benchmark studies model behavior; this project lets companies supply their own
policies. Allowing a request here cannot force a downstream model to answer.

## Try the offline demo

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

Config/5 sends the actual Markdown rule with a reusable evaluation question.
Optional `policy_assessment: q05_stage_aware` starts with Q05 and permits one bounded
follow-up for eligible low-confidence scope judgments. At `tool_action` it asks
about the actual proposed tool and arguments; elsewhere it uses Q04. It does not
classify tools from prose, select policies using test labels, or retry every error.
A follow-up must agree with the first scope choice and pass the configured gate.
Unresolved results remain `evaluation_error`, handled by the configured fallback.
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

## Develop

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
current profile unless explicitly stated. Final public-content review, release checks and publication approval remain
before public distribution; no release is published yet.

## License and contributions

Original software, documentation and synthetic examples use [Apache-2.0](LICENSE),
matching HumanWill Benchmark's software license. Company-authored policies and
inputs retain their existing rights; benchmark content and dependencies retain
their separate terms. See [license scope](LICENSING.md),
[third-party notices](THIRD_PARTY_NOTICES.md), [contributing](CONTRIBUTING.md) and
[private security reporting](SECURITY.md).
