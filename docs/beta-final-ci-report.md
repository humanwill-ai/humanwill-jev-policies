# Public Beta candidate: final CI and release packet

2026-10-04. **All seven jobs passed on their first run** at exact source
`90cf4629e8b9cd10bd1a9db6155204a6b8d1ec5f`. One consolidated branch push and one
dispatch per existing workflow; no duplicate runs, paid API calls in CI, billing
changes or deployment. The beta tag/release has **not** been published.

- [Core workflow](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/37184031519):
  Ubuntu 24.04/macOS 15 × Python 3.11/3.14. Each runs 328 tests with six optional
  gRPC skips, Ruff, exact wheel/source installation outside the checkout and
  service recovery/load checks. The Ubuntu 3.14 job also builds and exercises the
  offline container and audits pinned runtime dependencies; no known vulnerabilities
  were reported for that lock at the time. This is not an audit of every optional
  host dependency or the complete OS image.
- [Installed-host workflow](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/37184032861):
  LiteLLM 1.102.1, Agentgateway 1.5.0 and Copilot CLI 1.0.88, each using a built
  wheel with copied harnesses outside the source checkout.

| Actual host | Passing coverage |
| --- | --- |
| LiteLLM | 22 text, 26 structured-proposal, 18 MCP scenarios; four additional installed MCP callback tests |
| Agentgateway | 22 text, 26 relay/proposal, 22 MCP scenarios; six additional gRPC wire tests |
| Copilot CLI | Six prompt/tool/timeout/disabled-hook scenarios |
| VS Code Local, local macOS | Fresh 14-scenario acceptance on 1.139.1 / Copilot Chat 0.67.0; [evidence](evidence/beta-vscode-local.json) |

Host fixtures use synthetic evaluator answers; they establish routing/enforcement
contracts, not model accuracy. [Separate live Jev evidence](beta-tools-live-v1-report.md)
covers the LiteLLM proposal/MCP paths and their small-sample timing limits.

## Exact artifacts and review

The [machine-readable record](evidence/beta-final-ci.json) identifies jobs, package
hashes, container image/base digests and scope. All uploaded host wheels/reports,
core packages, image inventory and CI logs were downloaded and retained locally
under ignored `artifacts/beta-v020`. Artifact expiration on GitHub does not remove
those local copies.

The selected CI wheel's contents are identical to the wheel validated locally on
both Python versions. The earlier live/VS Code wheel differs only in its README
package description and corresponding wheel RECORD; runtime package bytes match.
The exact CI source archive is retained alongside the wheel. No artifact was
rebuilt after CI and substituted under its hash.

Gitleaks found no credentials in the new CI logs or host artifacts. Its three
source/history matches are verified SHA-256 hashes of a synthetic policy file
named `secret.md`, not keys. The source archive contains no ignored private
workflow datasets, local artifacts, environments or Git directory. Scanning cannot
prove the absence of every sensitive datum; these checks complement the content
and path review. No private logs were sent to an external scanning service.

Seven concrete attachments are staged in `artifacts/beta-v020/release-assets`:
wheel, source archive, `SHA256SUMS`, exact-artifact verification, container inventory,
a newly generated version-correct runtime SBOM, and the release manifest.
The source archive's older `docs/evidence/runtime-sbom.cdx.json` remains historical;
the new attachment names `0.2.0b1` and inventories the unchanged 16-package runtime
lock. Optional hosts and OS packages have separate scope; the container inventory
retains its installed package/license data. Release prose is staged in
`artifacts/beta-v020/RELEASE_NOTES.md`.

## Publication boundary

The tested candidate is ready to present as **0.2 Public Beta for controlled
company pilots**, with a GitHub prerelease flag and monitoring defaults. Independent
holdout/statistical enforcement qualification and real pilot experience remain
open. This is not a stable 1.0 or enterprise-readiness claim.

Source and preparation documentation have been pushed to the work branch. The
existing `v0.1.0a1` release and assets are unchanged. Final publication should use
the manifest's tested source and exact assets; if publication changes package
contents, build and verify the new artifacts and record that distinction. No merge,
tag, release creation or asset publication is performed by this preparation step.
