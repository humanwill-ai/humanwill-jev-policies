# Public-release preparation — step 4

2026-09-30 · unpublished `0.1.0a1` candidate · local/read-only preparation.
No GitHub Actions job, push, tag, release, deployment or visibility change occurred.

## License and project guidance

HumanWill Benchmark's framework license was verified as Apache-2.0 from its local
LICENSE and the repository license API (Git blob `d645695673349e3947e8e5ae42332d0ac3164cd7`).
Its separately licensed CC BY 4.0 question/report material was not imported.
Following the owner's proposal to match the software license, this project's
original software, documentation and synthetic examples are prepared under
Apache-2.0. The LICENSE text matches the official Apache text, ignoring only
surrounding whitespace. See [license scope](../LICENSING.md) and [NOTICE](../NOTICE).
Company-authored inputs are not relicensed by running the service; third-party
material and provider outputs retain their applicable rights/terms.

Added [contribution guidance](../CONTRIBUTING.md) and [security reporting](../SECURITY.md).
The owner supplied **sergio@humanwill.ai** as the private reporting address.
No test email was sent, mailbox access was not verified and no response-time SLA
is promised. The GitHub private-reporting API returned 404 for the current private
repository; the chosen email route does not depend on enabling that feature.

## Dependency notices and packaging

- Inventory of all **16 pinned Python runtime dependencies**, using exact installed
  versions from requirements.txt and their preserved license texts. See
  [notices](../THIRD_PARTY_NOTICES.md), [license hashes](evidence/runtime-licenses.json)
  and [CycloneDX 1.6 inventory](evidence/runtime-sbom.cdx.json).
- Inventory validates against the official CycloneDX 1.6 JSON schema. It is a
  flattened runtime inventory, not a complete transitive dependency graph, host
  inventory or operating-system/container SBOM.
- Wheel metadata declares `License-Expression: Apache-2.0`; its 20 license/notice
  files include the four project files and 16 dependency license texts. The source
  archive also includes SECURITY.md, CONTRIBUTING.md, notices, inventory and JSON
  evidence reports. Developer artifacts/credentials are excluded.
- Wheel/source fresh-install verification exercises the offline demo, schemas,
  service/hook contracts, selected follow-up paths, startup/authentication,
  no-egress, invalid configuration rejection and rollback. Local exact-byte reports
  and checksums are under `artifacts/packaging/public-prep`.

Runtime dependencies are unchanged from the candidate whose local audit reported
no known vulnerabilities on this date. Adding license metadata does not rerun or
extend semantic accuracy tests. Jev/provider service terms and optional host
licenses remain separate. The final container inventory and base-image review
will be produced during the deferred final Actions validation.

## Publication-exposure review

Baseline source: `c5bd45168d2ecb31834c4c070d2f568a4f382ed2`, plus the prepared release
materials. Read-only fetch confirmed two remote branch refs (`main` and
`work/service-gateway-hooks`). Both are covered by the local all-ref scan. Local
agent checkpoint refs were included too; they are not intended publication refs.
Do not use a mirror push as the publication mechanism.

| Surface reviewed | Scope | Result |
| --- | --- | --- |
| Reachable Git history | 94 commits / 1,440 objects across all local refs at baseline | Gitleaks: zero secret matches |
| Current source snapshot | 342 tracked baseline files plus new release materials | Gitleaks: zero secret matches |
| Earlier Git path inventory | Credential/private/artifact path patterns across reachable history | No matching committed credential/private artifact paths |
| Existing Actions logs | All 72 existing runs; all 72 log archives downloaded | Gitleaks: zero secret matches |
| Actions uploaded artifacts | API inventory | Zero artifacts |
| Issues, pull requests, releases | All-state/paginated API inventory | Zero of each |
| Prepared source artifact | Extracted source archive and contents | Gitleaks: zero secret matches; ignored local artifacts excluded |

Gitleaks version **8.30.1**, official Darwin x64 release archive verified against
its published checksum. Scans use built-in rules and redacted reports; scanner
inputs/results and downloaded logs stay ignored in `artifacts/public-review`.
No private source or logs were submitted to an external scanning service. Existing
workflow permissions are read-only and actions are pinned; no workflow was executed
or billing/branch/security setting changed during this review.

The repository inventory contains source, documentation, synthetic fixtures and
measured development evidence. Inspection focused on sensitive paths, credentials,
review exports, embedded review data, provenance and public claims. This was not
an independent security audit or exhaustive human review of every historical line.
A zero-match secret scan cannot prove that all sensitive content is absent.

## Explicit exposure and remaining release checks

One author/committer identity is present in the reachable history. Four frozen
historical protocol documents contain the developer's absolute filesystem paths:
`direct-policy-live-v1-protocol.md`, `effect-question-v1-protocol.md`,
`focused-policy-v1-protocol.md` and `patch-diagnostics-v1-protocol.md`. These are
metadata/path disclosures, not detected credentials. They were retained rather
than rewriting frozen evidence or Git history. Publication approval should include
this ordinary identity/path exposure; anonymizing only HEAD would not remove it
from history. Local detailed identity information remains in the ignored review
folder. Linked private/local artifact references are provenance, not public asset
availability promises.

Before publication:

1. Assemble the final candidate after owner review of license/scope and the
   publication materials; build matching final artifacts/checksums.
2. Use the existing Actions infrastructure immediately before release for the
   current candidate, including Linux Agentgateway and the container. Do not spend
   Actions allowance on interim preparation runs.
3. Review the final image's system/dependency inventory and notices. Recheck any
   new Git commits/refs, logs, uploaded assets or discussion content since this
   baseline. Do not infer final-image security from a Python-only inventory.
4. Review final repository security/access settings and the concrete visibility
   change, including existing Actions history and author metadata. Obtain the
   owner's publication approval, then publish and verify anonymous access.

No independent holdout or enterprise enforcement qualification is established by
licensing, secret scans or packaging. The release remains an experimental developer
preview with the [documented host/semantic limitations](preview-status.md).
