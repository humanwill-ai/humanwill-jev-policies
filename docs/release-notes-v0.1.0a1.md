# HumanWill Jev Policies v0.1.0a1 — experimental developer preview

**Draft release notes. Publication requires owner approval.**

Bring company-authored Markdown policies to AI gateways and coding agents through
a shared evaluation service. This first preview uses Jev for semantic judgments
and deterministic code for policy decisions and optional trusted authorization
facts. Examples start in monitoring mode; enforcement and error fallback are
explicit operator choices.

## Included

- Markdown policy folders with explicit recursive includes, stable policy IDs and
  versions, validation and immutable bundle hashes.
- Authenticated HTTP service and connectors for LiteLLM and Agentgateway text
  requests/non-streaming responses, plus separate VS Code Local and Copilot CLI
  hook profiles.
- Direct TypeSafe and OpenRouter transports. OpenRouter has live synthetic test
  evidence; direct TypeSafe has contract tests, without a required live smoke run.
- Independently switchable trusted metadata, configurable confidence thresholds,
  and explicit assessment, error and enforcement outcomes.
- Optional stage-aware follow-up: Q05 first, then at most one additional question
  for eligible low-confidence assessments. Tool-action events use tool-specific
  wording; other stages use Q04. Sequential follow-ups remain the selected
  development profile after the multi-question batching experiment.
- Offline demo, policy-authoring and connector guides, synthetic review cases,
  wheel/source packages, dependency notices and runtime inventory.

## Start locally

Download the attached wheel and source archive and verify them with the attached
`SHA256SUMS`. Use Python 3.11–3.14 on Linux or macOS. For locked dependencies,
extract the source archive and run from its root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Supply the path to the downloaded wheel:
python -m pip install --no-deps /path/to/humanwill_policies-0.1.0a1-py3-none-any.whl
humanwill-policies init-demo ./demo
humanwill-policies evaluate ./demo --config ./demo/config.yaml \
  --request ./demo/request.json --mock-answers ./demo/mock-answers.json --json
```

Dependency installation needs network access; the demo uses scripted answers and
needs no API key. See the [quickstart](https://github.com/humanwill-ai/humanwill-jev-policies/blob/v0.1.0a1/docs/quickstart.md)
and [connector guide](https://github.com/humanwill-ai/humanwill-jev-policies/blob/v0.1.0a1/docs/service-and-connectors.md)
for live setup. These tag links become available on publication.

## Evidence and limitations

The final development pack matched expected combined outcomes in 509/510
observations across three passes of 170 distinct cases. All 246 known-violation
observations produced block assessments. This was a tuned development pack with
known difficult cases removed, not an independent holdout or a production
enforcement success rate. Independent statistical qualification remains open.

Controlled warm LiteLLM measurements added a median 378 ms for prompt-only checks
and 733 ms for prompt plus a meaningful code-review response; p95 was 470 ms and
1,454 ms respectively. These synthetic workloads used live Jev through OpenRouter
and a mocked downstream model. Follow-ups, additional stages and provider/network
conditions affect latency. See the
[README](https://github.com/humanwill-ai/humanwill-jev-policies/blob/v0.1.0a1/README.md)
for the complete measurement scope, uncertain response workloads and reports.

Pinned host validation covers LiteLLM 1.102.1, Agentgateway 1.5.0, Copilot CLI
1.0.88 and VS Code Local 1.139.1/Copilot Chat 0.67.0. Linux/macOS core checks and
installed-package checks passed. Consult the
[compatibility table](https://github.com/humanwill-ai/humanwill-jev-policies/blob/v0.1.0a1/docs/compatibility.md)
before relying on another version or configuration.

This is one layer of defense, not an enterprise-qualified security boundary.
Jev remains susceptible to prompt injection. Hook timeouts, disabled hooks and
host configuration can bypass enforcement. Copilot CLI prompt hooks assess but
cannot block prompts. Prompt checks do not establish safety of later responses or
actions. Hosted Jev receives the covered content and policy text; self-hosting this
service does not make evaluation local. Production identity, destination and
software-source resolvers are not included. Streaming/multimodal inspection,
universal Copilot interception and Windows support are outside this preview.

## License and feedback

Original software, documentation and synthetic examples use Apache-2.0; third-party
and company-input rights remain separate. See LICENSE, LICENSING.md and
THIRD_PARTY_NOTICES.md. Report vulnerabilities privately to **sergio@humanwill.ai**.
Use repository issues for reproducible non-sensitive bugs and integration feedback;
do not post credentials or company content. No response-time SLA is promised.

This release is planned for GitHub only. No PyPI package or container image is
being published as part of this preview.
