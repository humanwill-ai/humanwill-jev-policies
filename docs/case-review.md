# Review cases in your browser

Open `docs/case-review.html` directly in a browser. On macOS, from the checkout:

```sh
open docs/case-review.html
```

No server, installation, account, or API key is needed. The page embeds the frozen
updated packet (93 active cases and seven recorded removals) (original named policy plus source policy), 46 source-policy cases, previously approved 36-case packet,
and exact four policy texts.
There are no external scripts, fonts, analytics, model calls, or executed test
commands. This is an internal evaluation-label review aid, not a runtime approval
workflow for agents.

1. Use **Approved sources · 46** or **Updated 93**, optionally filtering by policy or status. Compare each
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

The owner supplied the completed review on September 28. All 175 active cases
are accepted; seven are removed, with no pending corrections. The page now
embeds that sanitized approval/removal record, so a fresh browser shows the
accepted baseline. Local edits still take precedence and can be exported for a
future version; the frozen evaluated dataset is not changed by browser edits.
The original 36-case JSON retains its pre-review metadata and dated September 27
approval. See the [accepted protocol](reviewed-live-v1-protocol.md) and
[first live results](reviewed-live-v1-report.md). Approval of labels does not
establish statistical accuracy or close other release gates.

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

The page imports exports and browser progress from both prior versions. Reviews
of the original 100 are archived, visible on each revised case and exported as
`archived_reviews`; they cannot approve the new combined checks. Reviews of the
unchanged 46 and 36 packets remain active. See [the 100-case revision](holdout-sources-v2-review.md). Export format fingerprints now include the
source catalog. Four source cases include combined-policy results; approval
accepts those stated results too, and correction notes can name a secondary policy.

The 182-case extension was browser-checked on 2026-09-28 for source catalog display,
combined-policy results, legacy storage migration, legacy JSON imports,
packet-scoped bulk approval, existing review controls and responsive layout.
All checks passed in an isolated profile; synthetic QA approvals were cleared.

The active packet view now shows the combined result prominently. Its scope
control refers to EVAL-SRC-001; approval accepts both listed policy judgments.
The generator validates the revised packet against its own snapshot.

## Remove a case

Select **Remove from review** on any case. A reason in the notes field is optional.
The case immediately disappears from the active list and no longer counts toward
approval progress or bulk approval. Choose **Undo last removal** immediately, or
select **Removed** in the status filter and use **Restore to review** later.
Restoring returns the prior review status and notes; removal is not approval.

Removals persist in the browser and round-trip through JSON export/import. The
export includes a `removals` list and each removed case's explicit `removed`
status, plus active case counts. Share the export to apply your selections to the
repository; the offline page itself cannot rewrite dataset files. Historical
labels and any prior owner approval remain evidence, even when a case is removed
from the active review.

On 2026-09-28 the owner removed `holdout-v1-sw-git-fetch` as too vague. It is absent
from the active dataset's `cases` list, retained in `removed_cases` as a dated
removal record, and visible only through Removed in the page. The active packet
has 99 cases (181 active cases across all three packets). Saved approvals and
notes for all other unchanged cases migrate without requiring review again;
importing an older file cannot silently undo this owner-requested removal.

Removal controls were browser-tested on 2026-09-28: immediate undo, restoration
through the Removed filter, reload persistence, export/import, exclusion from
bulk approval and denominators, unchanged-review migration, and prevention of
accidental resurrection from older exports. Targeted 99-case composition and
snapshot checks pass; no model calls were made.

September 28 acceptance update: an isolated Chrome check verified all 175 recorded
approvals, seven removals, 93/46/36 active packet counts, export/import round trip,
remove/undo, and desktop/mobile layout with no JavaScript errors. The exported
accepted baseline also passes the strict Python review importer. These UI checks
do not constitute another human review. No raw owner export or personal notes
are embedded in the page.
