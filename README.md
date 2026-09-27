# Humanwill Jev Policies

Company-authored Markdown policies for AI gateways and coding agents. A companion to [HumanWill Benchmark](https://github.com/humanwill-ai/humanwill-benchmark), which studies harmful refusals and usefulness. This project aims to help companies apply their own rules; an adapter allow cannot force a downstream model to answer.

**Implemented: service and connectors, `0.1.0.dev3`.** Markdown policy bundles, deterministic/semantic evaluation, direct/OpenRouter Jev adapters, an authenticated HTTP service, LiteLLM/Agentgateway adapters, and separate Copilot Local/CLI hooks. Real gateway, Copilot CLI and VS Code Local enforcement tests pass on the pinned versions; see [integration evidence](docs/integration-report.md). OpenRouter live smoke passed; direct TypeSafe live smoke is optional for v0.1. The repository remains private, with public preview `v0.1.0a1` awaiting the [release gates](docs/public-release-plan.md).

Step 6’s [initial quality comparison](docs/evaluation-development-report.md) found false blocks and injection-related misses. The [config/3 follow-up](docs/evaluation-v3-report.md) improved original-set false blocks, but injection failures remain. The owner subsequently [clarified the approved-model versus onward-sharing boundary](docs/software-policy-boundary-tests.md); the historical unknown-origin label does not represent that workflow. The 96 development cases per evaluator use draft labels; no calibrated enforcement profile or held-out accuracy claim is available.

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

## Planned first release

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

One authorized synthetic OpenRouter call passed using the existing Keychain credential; see the [smoke evidence](docs/smoke-2026-09-27.md) and [procedure](docs/provider-smoke.md). Project licensing is still an owner decision before public publication.
