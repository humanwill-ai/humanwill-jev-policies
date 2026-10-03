# HumanWill real-workflow pilot

Updated 2026-10-03: the owner authorized the exact historical real-data replay.
**Completed: 30/50 allow, 20/50 evaluation_error, no blocks**, using premeasurement
assistant-provisional expectations. See the [full report](dogfood-history-v1-report.md)
and private `artifacts/dogfood-v1/history-live-v1/results.html`. This is retrospective
monitoring, not active enforcement or a released Codex connector.
Streaming is postponed to a future release by owner instruction.


Latest follow-up: [grouping-only comparison](dogfood-grouping-v1-report.md) is complete.
Two fresh passes per arm on the unchanged packet:42% flat versus28% grouped
abstention, with a repeated synthetic historical-secret block→error regression.
Grouping remains experimental. Private comparison page:
`artifacts/dogfood-v1/grouping-live-v1/comparison.html`. New415calls cost$0.052238172;
current accounted spend$0.582856656, remaining$4.417143344. No new unknown charges.
Earlier single-pass evidence and its consumed receipt are preserved below.


Latest policy-target comparison: [report](dogfood-views-v1-report.md). Fresh flat /
grouped / explicit-target arms yield 40% /30% /35% workflow abstention across two
passes; the candidate restores historical-secret blocks but remains experimental.
Private `artifacts/dogfood-v1/views-live-v1/comparison.html` contains the full results.
609 new settled calls cost $0.082725846; accounted total $0.665582502, remaining
$4.334417498 including the preserved historical reserve. No runtime adoption.


Latest compact-target comparison: [report](dogfood-compact-v1-report.md). Compact /
grouping / dual-view workflow abstention is27% /28% /36% across two fresh passes.
Compact keeps all34 known-violation blocks and avoids the dual size rejection; still
experimental with15 distinct unresolved requests. Private comparison:
`artifacts/dogfood-v1/compact-live-v1/comparison.html`.583 new settled calls cost
$0.080854536; current accounted$0.746437038, remaining$4.253562962. No runtime adoption.

## Current owner review

Case008 is resolved as governed preparation, not an unconditional allow. See the
[clarification and version4 policy](disclosure-preparation-boundary.md). A separate
review overlay records the owner decision; all historical pages and labels remain
frozen. Case015 is reviewed as ambiguous intent with defensible abstention;026 is
owner-confirmed allow under its complete trusted operation approval. Twelve other
distinct cases remain. Runtime settings are unchanged. See the
[review progress](dogfood-case-review.md). No live rerun.

## Historical packet

The local review page is `artifacts/dogfood-v1/history/review.html` and its exact
packet is `artifacts/dogfood-v1/history/packet.json`. Both are ignored by Git and
contain real project conversations; do not publish them. The packet contains the
last 50 native user-text messages before the pilot discussion, from October 1–3.
Selection is chronological, not based on evaluator outcomes.

Each case preserves a contiguous suffix of up to five visible user/final-assistant
messages, bounded at 10,000 content bytes. The current prompt is never silently
truncated. Earlier text outside that suffix, commentary, tools/results, attachments,
system/developer instructions and compaction summaries are excluded. Unknown
transcript message shapes are skipped rather than guessed. The installed client
records final answers as `phase: final_answer`; that observed spelling and `final`
are supported. A discarded preparation draft omitted assistant answers; the
corrected packet below is the sole active review input, with no prior reviews or
API calls to migrate.

**This is a bounded conversation replay, not the historical model wire request.**
Every historical event records incomplete coverage and exclusions. Short references
such as “do it” can still be unresolved when essential context falls outside the
window. The monitor-only profile permits assessing this partial evidence; it does
not establish whole-conversation compliance. Results must be reported separately
from the synthetic pack and from prompt-only prospective monitoring.

Active packet canonical SHA-256:
`47359eb36f453a3961dbd6ec654eab3fa387fc2530d8bcfb75fef8c231c568f2`.

Open the local HTML page, choose allow/block/evaluation_error, mark each case
approved or exclude it, and export `humanwill-dogfood-reviewed.json`. Owner labels remain pending. A separate frozen assistant-provisional review was
used for the authorized run; it does not change this original pending packet.
Jev answers are now available, so further label review is postmeasurement. Exporting reviews makes no
network request and does not authorize sending the data externally.

## Policy configuration and authority

`evals/dogfood/config.yaml` uses unchanged EVAL-SW-001 v3 and EVAL-SRC-001 v3,
monitoring mode, current config/5 Q05→Q04 behavior at model_request, and unchanged
0.80/0.70/0.80 gates. It does not adopt the research dual-view candidate, add the
synthetic secret marker, or claim document/production-policy coverage.

The known coding route is approved for this scoped pilot. User/group metadata is
not required for ordinary coding assistance. Proposed operator scope permits
publishing this project to its existing `humanwill-ai/humanwill-jev-policies`
repository, consistent with the owner's prior instructions. Approved software
sources remain a pending owner decision; never assume all GitHub/PyPI resources
are approved merely because a developer can access them.

The pilot does not implement automatic destination/package/dependency resolution.
For historical cases, event-bound onward/source approval facts must come from
operator configuration and the actual operation, with an evidence note. In this run
the assistant mapped six project-publication operations to the existing owner-approved
repository; this did not infer approval from prompt claims or provisional labels. Unknown remains null. These facts are separate from expected labels
and never extracted from prompt claims or Jev answers. A correctly recognized
restricted operation with unavailable facts can produce missing_trusted_metadata;
report that separately from semantic low-confidence errors.

## Local collection of the next 100 prompts

A local-only `.codex/hooks.json` is installed and excluded through Git's local
exclude file. It calls the standalone capture script asynchronously. Settings
restrict collection to this project directory and the current session ID, with a
hard maximum of 100 unique prompt/turn events. Other sessions/projects are ignored.
The hook captures submitted text only, including the host-supplied user role;
it does not read files, transcripts, tool results or model requests. It makes no
network call, returns no model context, requests no block and exits successfully
on capture failure. Raw events and status are stored with private permissions under
`artifacts/dogfood-v1/future`.

Current status: **installed, actual client invocation not yet observed**. Script
invocation tests pass; they are not proof the running editor loaded or trusted it.
Official documentation requires review/trust of new non-managed hook definitions.
Use the host's hook review UI, or `/hooks` in Codex CLI, to review the exact command.
No hook-trust bypass or trust-store modification was performed. A reload/new turn
may be needed; confirm an actual `last-hook-status.json` with `captured` and a new
`dogfood-future-*.json` before calling collection active. If this host cannot load
it, diagnose that before promising prospective coverage.

Capture is currently **not continuous Jev assessment**. Hosted monitoring activation
will follow the agreed real-data scope, approved-source decision and local callback
acceptance. Each future prompt must remain visibly recorded as captured_not_evaluated
until an actual assessment exists. Do not report captures as policy successes.

To stop capture, remove only the HumanWill handler from `.codex/hooks.json` (or
remove that file if it still contains only this pilot), then confirm the host
reloaded its configuration. Retain or delete the private artifacts separately.

## Real-data egress gate and budget

The owner subsequently authorized one exact historical pass, capped at $0.10. The
active receipt binds the assistant-provisional review and all frozen inputs; it has
been consumed once. Total new cost was $0.008785896 for 69 settled calls. Current
accounted total is $0.530618484, including the unchanged $0.01 historical reserve;
$4.469381516 remains. Future captures are not authorized for automatic egress by
this historical receipt. The paragraphs below describe the original preparation.


The prior spending permission was for synthetic evaluations. The agreed pilot
plan calls for reviewing the actual data scope before hosted real-data evaluation.
The inactive local `egress-receipt.template.json` proposes at most **$0.10 additional**
for one historical pass within the existing $5 total ceiling. It binds the exact
original packet, exported review with explicit label provenance, operator scope, policy/configuration hashes
and executable source fingerprint. It needs explicit owner real-data authorization
before activation; changing input or configuration invalidates that receipt.

The runner `python -m evals.dogfood.evaluate --help` verifies this receipt and all
reviews before retrieving the Keychain credential or creating a provider backend.
It refuses edited original requests, incomplete reviews, duplicate case IDs,
unsupported facts and reuse of a consumed approval. Exclusions remain in the review
record. Only policies and normalized event content go to OpenRouter/TypeSafe;
review notes, labels and verified fact values are not sent as evaluator state.
Raw provider exchanges remain local and ignored. Monitoring decisions do not block
work. No retries have been added to the runtime.

Accounting uses the existing `artifacts/quality/spending.json` lock, reserves each
call, preserves historical unresolved index1830's $0.01 and stops on any new unknown
charge. At preparation, known spend was $0.511832588; accounted $0.521832588; remaining
$4.478167412. The completed run and current accounting are recorded above. No CI,
push or publication was performed.

## Verification and limits

Eight focused offline tests pass (including provisional-label provenance): transcript provenance/future-context exclusion,
review immutability, exact egress gating, unavailable trusted facts, capture
scope/deduplication/limits, non-blocking command behavior and HTML text escaping.
Ruff and JavaScript syntax checks pass. The local Gitleaks scan finds no matches
in the active packet/page; this is a secret-pattern check, not a guarantee that
all content is public or appropriate for third-party processing. Browser automation
was unavailable, so the page has not had a visual browser acceptance check.

Current observations and labels will describe one project's workflow, not
enterprise demand, independent holdout qualification, or adversarial detection
rates. Keep the synthetic violation tests. Freeze the pilot configuration before
measurement; do not tune questions against these same observations and present
them as unseen validation.

## Source

Reviewed 2026-10-03 against installed `codex-cli 0.155.0-alpha.16.3` and the current
[official hook documentation](https://learn.chatgpt.com/docs/hooks): project-local
configuration, trust review, asynchronous command handlers, UserPromptSubmit and
transcript instability. Documentation is not runtime acceptance of this editor.
