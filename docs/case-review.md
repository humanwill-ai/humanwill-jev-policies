# Review cases in your browser

Open `docs/case-review.html` directly in a browser. On macOS, from the checkout:

```sh
open docs/case-review.html
```

No server, installation, account, or API key is needed. The page embeds the frozen
100-case packet, 46 new source-policy cases, previously approved 36-case packet,
and exact four policy texts.
There are no external scripts, fonts, analytics, model calls, or executed test
commands. This is an internal evaluation-label review aid, not a runtime approval
workflow for agents.

1. Use **Approved sources · 46** or **New 100 cases**, optionally filtering by policy or status. Compare each
   event and trusted evidence with the policy beside it. The expected result is
   a proposed test label, not a measured model answer.
2. Select **Approve expected result**, or enter a reason, choose a proposed result
   and semantic scope if needed, and select **Flag correction**. Notes save as you
   type; proposed dropdown changes are recorded when you flag the correction.
   Approval always accepts the original result and scope. Move-to-next is optional.
3. **Previously approved 36** preserves the owner's September 27 approval. You can
   reconfirm a case or flag a correction without changing the historical record.
4. **Export review** downloads a JSON file. Give that file to Codex (or put it in
   the ignored `artifacts/` folder and share its path) to record approvals and
   apply agreed corrections to a versioned dataset before evaluation. Nothing in
   the page edits source datasets or opens the live-run gate automatically.

The bottom-of-page bulk action accepts pending labels in the selected packet after
confirmation, including cases hidden by filters; it never overwrites flagged corrections.

Progress is saved in local browser storage, keyed to both dataset fingerprints
and the policy source hashes. Browser storage can be cleared, and behavior for
local files varies by browser; export regular backups. **Import review** restores
an export after confirmation and rejects a different dataset/policy fingerprint.
Keep reviewer names and personal notes in local exports, out of Git. The export's
`reviews` map contains explicit local changes; `packets` includes all original
labels and historical approval provenance for readability. This local tool does
not authenticate a reviewer or provide a tamper-proof signature.

The 100-case and new source-case labels remain pending until actually reviewed. The 36-case source
JSON retains its original pre-review metadata; its dated owner approval is
recorded in [the review packet](step6-review-candidates-v1.md). Reviewing either
packet does not establish statistical accuracy or close other release gates.

## Maintenance and validation

Edit `scripts/review/page.html`, `style.css`, and `app.js`, then regenerate:

```sh
.venv/bin/python scripts/build_review.py
```

The generator verifies the original 100-case dataset against its protocol hash,
the source packet/catalog/matcher against its own snapshot, and the previous
packet against its approved dataset hash. It embeds event content as escaped
JSON and displays case/policy text using text nodes. A restrictive page policy
blocks network connections and external resources. The generated HTML and its
source templates are included in the source distribution.

Browser verification on 2026-09-28 used Chrome 153 in a separate temporary profile:
all 136 cases, individual approval, correction reasons, reload persistence,
bulk approval preserving corrections, historical approval, policy/search filters,
export/import round trip, rejection of mismatched imports, and desktop/mobile
layout. No JavaScript runtime errors occurred. Test progress was cleared after
verification; no human approval was recorded by these checks.

The extended page migrates local progress and imports exports from the original
136-case page. Original approvals apply only to those unchanged cases; the 46 new
source-policy cases start pending. Export format fingerprints now include the
source catalog. Four source cases include combined-policy results; approval
accepts those stated results too, and correction notes can name a secondary policy.

The 182-case extension was browser-checked on 2026-09-28 for source catalog display,
combined-policy results, legacy storage migration, legacy JSON imports,
packet-scoped bulk approval, existing review controls and responsive layout.
All checks passed in an isolated profile; synthetic QA approvals were cleared.
