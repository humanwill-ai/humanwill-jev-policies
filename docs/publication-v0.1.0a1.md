# First public release — v0.1.0a1

Published 2026-10-01 after the owner approved the concrete release candidate,
Apache-2.0 scope, six assets and recorded identity/path exposure.

- [Public repository](https://github.com/humanwill-ai/humanwill-jev-policies)
- [Experimental developer prerelease](https://github.com/humanwill-ai/humanwill-jev-policies/releases/tag/v0.1.0a1)
- Immutable target for this release: `3f086c0ec102b202d8150cf42739baf1ad62047e`.
- [Machine-readable publication verification](evidence/publication-v0.1.0a1.json).

The tag and six approved assets are published: wheel, source distribution,
SHA256SUMS, runtime CycloneDX inventory, dependency license inventory and release
evidence. The release body matches the approved notes with only the draft marker
removed. The source snapshot retains its prepublication wording as provenance;
later documentation on main records publication without moving the tag or
replacing the approved asset bytes.

## Verification and provenance

Anonymous access to the repository and release page passed. All six assets were
downloaded without authentication and matched the approved local bytes; all five
listed SHA-256 checksums passed. An anonymous shallow clone of the release tag
resolved to the exact approved commit. In a new Python 3.11 environment outside
the checkout, installation of locked dependencies from that clone and the
downloaded wheel passed `pip check`, policy validation and the offline scripted
demo (`allow`, `simulated: true`). No provider calls were made.

Before publication, both exact wheel/source packages passed fresh installation,
demo, service/hook, stage-aware follow-up and operational checks on Python 3.11
and 3.14. All 260 offline tests, lint and formatting passed. The wheel's 43 runtime
files match the [hosted-tested candidate](final-ci-report.md) byte for byte; only
METADATA and RECORD changed to carry the updated README. Runtime, dependency locks,
container recipe and workflows remained unchanged. Existing host/CI evidence is
retained; no new hosted run is claimed for the repackaged assets.

Full-history, source and extracted-package scans found no Gitleaks matches. The
74 existing Actions runs and one uploaded artifact matched the reviewed inventory.
The owner approved exposure of retained commit identity, the four historical local
path documents, source-archive owner metadata, both remote branches and Actions
history. This is targeted review and pattern scanning, not an independent audit.

GitHub reports the repository public. Post-change inspection found no repository
rulesets and an unprotected main branch; workflow permissions remain read-only,
with workflow PR approval disabled. The API also reports Dependabot security
updates, secret scanning and secret-scanning push protection disabled. No
protection, billing or other security settings were changed. Repository security
configuration can be addressed separately.

This is a GitHub prerelease only: no PyPI upload, container-registry publication,
deployment or announcement was performed. CI was skipped for the release-note and
publication-record commits to preserve Actions allowance. No paid model calls were
needed; the existing evaluation ledger is unchanged.

## Qualification remains separate

Monitoring examples and explicit enforcement/error settings remain unchanged.
Independent holdout validation, the original statistical enforcement-readiness
targets and production resolver coverage remain open. Public availability does
not establish enterprise readiness or immunity to prompt injection and host
bypasses. See the README security and performance sections before adoption.
