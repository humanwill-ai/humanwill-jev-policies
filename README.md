# Humanwill Jev Policies

Company-authored Markdown policies for AI gateways and coding agents. A companion to [HumanWill Benchmark](https://github.com/humanwill-ai/humanwill-benchmark), which studies harmful refusals and usefulness. This project aims to help companies apply their own rules; an adapter allow cannot force a downstream model to answer.

**Implemented: offline foundation, `0.1.0.dev0`.** Load nested policy folders, validate stable IDs and deployment settings, calculate reproducible hashes, and preview effective policies. No Jev evaluation, HTTP service, runtime connectors, or enforcement exists yet. The repository remains private; the planned public preview is `v0.1.0a1` after the [release gates](docs/public-release-plan.md) pass.

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
```

Installation downloads dependencies. The installed commands run offline without credentials. Use a new destination for `init-demo`; it refuses to overwrite existing files. The demo enables one content-only policy in monitor mode, keeps metadata off, and explicitly disables two rules needing trusted facts. It performs no assessment or enforcement. Preview includes policy text; keep its output private when using private rules.

A policy folder starts with `policies.md`. Collections explicitly include Markdown files or nested collections. Each policy has a stable ID, version, title, stages, and a Markdown rule body. See the [authoring/configuration contract](docs/contracts.md), [examples](examples/policies/policies.md), and exportable schemas:

```sh
humanwill-policies validate examples/policies --json
humanwill-policies schema request
```

## Planned first release

All required integrations remain pending:

- LiteLLM and Agentgateway: text request and non-streaming response checks.
- Copilot VS Code Local: submitted-prompt and pre-tool checks.
- Copilot CLI: prompt assessment and pre-tool checks; no prompt-blocking claim.
- Jev through OpenRouter for development/testing and direct TypeSafe.

Optional metadata will combine verified identity, groups, classifications, and destinations with semantic judgments. Configuration validation already rejects metadata-dependent enforcement when required sources are disabled. Actual source verification and decision logic are future work. User assertions of permission never establish authorization.

Self-hosting the future service will not make hosted Jev evaluation local. Measure false blocks, missed violations, host bypasses, latency, and cost before making enforcement claims. Customer demand and enterprise suitability remain unvalidated.

## Develop

```sh
python -m pip install -r requirements-dev.txt
python -m pip install --no-deps --no-build-isolation -e .
ruff check src tests
ruff format --check src tests
python -m unittest discover -s tests -v
python -m build --no-isolation
```

CI tests Python 3.11/3.14 on Ubuntu/macOS, builds the source distribution and wheel, and installs/runs the demo outside the checkout. Runtime dependency auditing is separate from semantic accuracy or a security review. See [foundation evidence](docs/foundation-report.md) and [compatibility/reuse findings](docs/compatibility.md).

## Project documents

- [Project brief](docs/project-brief.md), [decisions](docs/decisions.md), and [release roadmap](docs/public-release-plan.md).
- [Technical release design](docs/release-plan.md) and [optional metadata](docs/optional-metadata.md).
- [Research](docs/research.md) and [evaluation plan](docs/evaluation-plan.md).

No project content has been submitted to an evaluation provider. Project licensing is still an owner decision before public publication.
