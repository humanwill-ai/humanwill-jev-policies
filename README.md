# Humanwill Jev Policies

Company-authored Markdown policies for AI gateways and coding agents. A companion to [HumanWill Benchmark](https://github.com/humanwill-ai/humanwill-benchmark), which studies harmful refusals and usefulness. This project aims to help companies apply their own rules; an adapter allow cannot force a downstream model to answer.

**Implemented: service and connectors, `0.1.0.dev3`.** Markdown policy bundles, deterministic/semantic evaluation, direct/OpenRouter Jev adapters, an authenticated HTTP service, LiteLLM/Agentgateway adapters, and separate Copilot Local/CLI hooks. Real gateway, Copilot CLI and VS Code Local enforcement tests pass on the pinned versions; see [integration evidence](docs/integration-report.md). OpenRouter live smoke passed; direct TypeSafe live smoke is optional for v0.1. The repository remains private, with public preview `v0.1.0a1` awaiting the [release gates](docs/public-release-plan.md).

The [latest owner-reviewed Jev run](docs/reviewed-live-v1-report.md) covers 175
accepted cases and four policies, including approved software sources. It matched
161 combined outcomes; no known violation was allowed overall, but ten legitimate
cases returned errors that would block under fail-closed enforcement. One
source-policy unknown was incorrectly allowed within an event that another policy
kept indeterminate. The semantic release gate remains open.

The current measured bundle is `evals/step6/policies-sources-v1`, configured by
`config-sources-v1.yaml`. Earlier three-policy and Gemini comparisons remain
historical evidence; Jev remains the first release backend. The standalone
instruction-integrity rule remains removed. All shipped configurations remain
in monitor mode; no calibrated enforcement profile is available.

The [config/3 development extension](docs/decision-v3.md) adds opt-in decisions from verified predicates and stage-specific semantic questions, with separate per-model uncertainty analysis. Config/2 remains available for baseline reproduction.

## Try it locally

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

Installation downloads dependencies. Validation, preview, and mock evaluation run offline without credentials. Use a new destination for `init-demo`; it refuses to overwrite existing files. The demo enables one content-only policy in monitor mode, keeps metadata off, and explicitly disables two rules needing trusted facts. The mock uses scripted answers, reports `simulated: true`, and performs no host enforcement. Preview includes policy text; keep its output private when using private rules.

A policy folder starts with `policies.md`. Collections explicitly include Markdown files or nested collections. Each policy has a stable ID, version, title, stages, and a Markdown rule body. See the [authoring/configuration contract](docs/contracts.md), [examples](examples/policies/policies.md), and exportable schemas:

```sh
humanwill-policies validate examples/policies --json
humanwill-policies schema request
```

Step 7 installation/operation checks pass, including all seven CI jobs and the offline container demo; see [packaging evidence](docs/packaging-report.md). The [step 6 gate audit](docs/step6-release-gates.md) and [36-case review packet](docs/step6-review-candidates-v1.md) identify the remaining quality work.

For label review, open [the offline review page](docs/case-review.html) locally in
your browser: the accepted 93 updated cases (original policy plus source policy), 46 approved-source cases, and the previously approved 36, with policies,
approval/correction/removal controls, saved progress, and JSON export. See
[review instructions](docs/case-review.md). GitHub displays HTML source; download
or open the checked-out file to use it.

For installation from exact built artifacts and the local container recipe, use
the [quickstart](docs/quickstart.md). The [policy-author guide](docs/policy-authoring.md)
explains Markdown bundles and trusted facts; the [operations guide](docs/operations.md)
covers upgrades, rollback and troubleshooting.

The new [approved software sources policy](docs/approved-software-sources.md) adds
a separate operator-managed inbound allowlist. Its four-policy bundle and review
cases have completed owner review and a first live Jev run; production origin
resolution and semantic release qualification remain pending.

## First-release support

Implemented profiles and remaining evidence:

- LiteLLM and Agentgateway: text request and non-streaming response checks.
- Copilot VS Code Local: submitted-prompt and pre-tool controls verified on the pinned runtime; host timeouts and disabled hooks bypass checks.
- Copilot CLI: prompt assessment and pre-tool checks; no prompt-blocking claim.
- Jev through OpenRouter for development/testing and direct TypeSafe: adapters implemented; OpenRouter live smoke passed; direct TypeSafe has contract tests, with live smoke optional.

Optional metadata combines separately verified facts with deterministic predicates and semantic scope. The core checks source mappings, event binding, completeness, and freshness; the embedding application must authenticate those facts. Wire-request metadata and user assertions never establish authorization. Metadata is off in the default demo.

Hosted evaluation can send active rule/scope text and event content outside your environment. It requires explicit disclosure authorization; self-hosting the service will not make Jev local. Measure false blocks, missed violations, host bypasses, latency, and cost before making enforcement claims. Customer demand and enterprise suitability remain unvalidated.

See [service setup, gateway configurations and hook installation/removal](docs/service-and-connectors.md). Example policies default to monitoring; hosted evaluation requires explicit disclosure opt-in.

## Develop

```sh
python -m pip install -r requirements-dev.txt
python -m pip install --no-deps --no-build-isolation -e .
ruff check src tests
ruff format --check src tests
python -m unittest discover -s tests -v
python -m build --no-isolation
```

CI tests Python 3.11/3.14 on Ubuntu/macOS, builds the source distribution and wheel, and installs/runs the demo outside the checkout. Runtime dependency auditing is separate from semantic accuracy or a security review. See [evaluation-core behavior](docs/evaluation-core.md), [step 3 evidence](docs/evaluation-core-report.md), [foundation evidence](docs/foundation-report.md), and [compatibility/reuse findings](docs/compatibility.md).

## Project documents

- [Project brief](docs/project-brief.md), [decisions](docs/decisions.md), and [release roadmap](docs/public-release-plan.md).
- [Technical release design](docs/release-plan.md) and [optional metadata](docs/optional-metadata.md).
- [Research](docs/research.md) and [evaluation plan](docs/evaluation-plan.md).

OpenRouter transport smoke and synthetic development evaluations are recorded in the linked reports. See the [smoke procedure](docs/provider-smoke.md) for credential-safe reproduction. Project licensing is still an owner decision before public publication.
