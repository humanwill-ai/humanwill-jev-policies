# Contributing

This is an experimental developer preview for company-defined policy evaluation.
Start with the [README](README.md), [current status](docs/preview-status.md) and
[policy authoring guide](docs/policy-authoring.md).

Use synthetic, shareable reproductions in issues and pull requests. Do not upload
company policies, customer prompts, proprietary code, credentials, account logs
or sensitive vulnerability details. Follow [SECURITY.md](SECURITY.md) for potential
vulnerabilities. Ask about substantial scope changes before implementing them.

## Development checks

Use Python 3.11 or 3.14 on a supported Linux/macOS environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install --no-deps --no-build-isolation -e .
ruff check src tests evals scripts
ruff format --check src tests evals scripts
python -m unittest discover -s tests
```

Preserve separation between model judgments, trusted facts, decisions and actual
host enforcement. Add meaningful tests for behavioral changes. Metadata-off,
missing evidence, unsupported content, failures and host bypasses must stay
explicit. Do not silently convert uncertainty into permission.

Version changes to policy meanings, evaluation cases and protocols. Preserve frozen
historical inputs and results; create a new campaign when behavior changes. Tests
used for tuning are not an independent holdout. Report false blocks, missed
violations and abstentions separately. Live evaluations require explicit synthetic
data-egress and spending authorization; offline checks require no provider key.

Before this first release, maintainers reserve GitHub Actions for the final
candidate. Use local validation and avoid interim workflow dispatches or
CI-triggering pushes/PR updates. Publication, deployments and billing changes
remain separately authorized actions.

## Rights and attribution

Contributions intentionally submitted for inclusion are under Apache-2.0 as
provided by section 5 of [LICENSE](LICENSE), unless explicitly stated otherwise.
Contributors retain ownership; this project requires no copyright assignment or
separate CLA. Submit only material you have the rights to contribute, including
employer authorization where applicable. Identify third-party material and retain
its original license/notices. See [license scope](LICENSING.md).

For pull requests, explain the problem, resulting behavior, validation and any
remaining limitations. Do not claim broader host coverage or enterprise readiness
than the supplied evidence establishes.
