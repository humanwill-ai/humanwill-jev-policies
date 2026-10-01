# Final candidate GitHub validation

2026-10-01 · experimental developer preview `0.1.0a1` · still private.

The owner authorized the postponed hosted checks. One batched push of candidate
`5b1786bf0e24e8cd6203badf808653e8682716cb` triggered the two existing workflows.
All seven jobs passed on their first attempt; no duplicate dispatch, rerun, paid
model call, billing change, deployment or publication was performed.

| Validation | Result |
| --- | --- |
| [Core matrix](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/36823008685) | Ubuntu 24.04/macOS 15 × Python 3.11/3.14: all four jobs pass, 254 tests each, lint/format, exact wheel/source installs, demo, service/contracts and load/recovery |
| [Pinned hosts](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/36823008686) | Agentgateway 1.5.0: 22/22; LiteLLM 1.102.1: 22/22; Copilot CLI 1.0.88: 6/6 |
| Container | Linux build and non-root, network-disabled offline demo pass |
| Python runtime audit | `pip-audit` of the pinned runtime requirements found no known vulnerabilities |
| Exposure review delta | Git history, both new run logs, inventory and extracted release assets: no Gitleaks secret matches |

The host harnesses install a wheel and run outside the checkout. They verify
allow/deny, monitoring, unavailable services, error/timeout behavior and documented
coverage/bypass scenarios with controlled synthetic model/evaluator responses.
CLI prompt assessment and timeout/disabled-hook bypass remain explicit limits.
They do not establish live Jev accuracy or every host/configuration combination.

The fresh [VS Code Local 14-scenario acceptance](evidence/preview-vscode-local-2026-09-30.json)
remains applicable: runtime source under `src/` is unchanged since its `d6897c7`
candidate. The editor is not exercised by unattended GitHub CI.

## Exact retained packages and image inventory

The Ubuntu/Python 3.14 job retained the exact verified packages and reports in
[the candidate artifact](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/36823008685/artifacts/11143428748),
with 14-day retention. Copies are preserved locally under `artifacts/final-ci`.
These bytes identify the CI snapshot; documentation-only result recording after
that commit does not replace the source archive or claim a second CI run.

| File | SHA-256 |
| --- | --- |
| `humanwill_policies-0.1.0a1-py3-none-any.whl` | `f823c4abec9aba86730d3a4a5d1385e84ee5c5d379fcd96314ce222b82ee2068` |
| `humanwill_policies-0.1.0a1.tar.gz` | `fb4b684c2b32bf65f781fcb5f3b50f75f1285f187ebc68aad9d06f0d0d343606` |

The wheel contains all 20 expected project/dependency license files. The image
inventory records 105 Debian packages, 21 installed Python distributions (including
the application and base-image packaging tools), all their available license texts,
the Python license and Debian common licenses. Every listed package has a retained
copyright/license record. Base digest:
`python@sha256:a36c24f9cbdf4fd0f52d67f0823eeac19c2028c637cecc392d97f980d4fec56b`.
Built image: `sha256:816458ff985ec5c3fbf929e49f1ee62686b68eddfdfa0890fea66ae97d1814b7`.

This is an inventory, not a complete license-compliance or OS vulnerability audit.
The dependency audit covers the application lock, not every base-image package.
No container image is being distributed; the preview includes a build recipe.
Service-operation evidence remains in the job logs; its JSON was not included in
the artifact because the configured upload path differs from the harness output.

See [machine-readable evidence](evidence/final-ci-2026-10-01.json) for job URLs,
scenarios, artifact metadata, inventory hash and exact installation results.

## Publication boundary

The postponed engineering checks are complete. Final publication still requires
owner approval of the concrete public candidate, Apache-2.0 scope, release assets
and the identity/path exposure described in [the public review](public-preparation-report.md).
The repository remains private; no tag or GitHub release has been created. Read-only
settings review found read-only default workflow permissions, no workflow PR-review
approval and an unprotected `main`; no access/security setting was changed.

Publish as an **experimental developer preview**, with monitoring defaults and
documented optional enforcement. Independent holdout validation and the original
statistical enforcement-readiness targets remain open. The tuned development pack
and host integration checks do not establish enterprise readiness.
