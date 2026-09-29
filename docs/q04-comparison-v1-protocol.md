# Q04 batch versus isolation experiment

Owner authorized this follow-up on 2026-09-29. Compare two continuations of a shared
fresh Q05 primary: Q04 with the full original question batch, and Q04 with each
unresolved policy separately. No content classifier or runtime implementation change.

Run three passes of the unchanged 175 owner-reviewed events, plus 24 new synthetic
workflows (12 allow, 8 block, 4 uncertain). The new cases and labels are model-authored,
frozen before measurement, pending owner review. They are prospective development
checks, not independent holdout or release evidence. Report their results separately.
The new events use disclosure/source policies throughout, with production enabled
for tool events that exercise service/local workflows. No document-policy expansion.
All model questions sent by the original evaluator remain present in the batch arm;
positive trusted predicates may already have short-circuited some policies.

Keep policies, existing context, model, strict response validation and .80/.70/.80
gates unchanged. Only runtime low-confidence applicable/not_applicable answers under
an overall evaluation_error are eligible. Accept only same-choice, threshold-qualified,
unique-maximum secondary answers. Preserve accepted primary judgments and trusted
metadata checks; recompute using the real evaluator. Do not retry raw insufficient
answers, missing metadata, malformed primary replies, or errors masked by a block.
No labels, expected policy IDs or outcome-aware routing enter provider payloads.

Q04 wording is identical in both arms. The isolated arm removes other questions,
not event/context fields. At most two follow-up calls per arm, within the original
15-second total assessment budget. More eligible policies remain unresolved if the
call budget is exhausted. A malformed follow-up leaves its affected primary answers
unchanged. No retries around errors. Randomize branch order using the frozen seed.
Report single-question primary batches separately: both arms then send identical
payloads, so differences reflect response variability, not isolation.

Freeze inputs and source in a clean local commit before calls. Use the existing
$5 ledger, at most $0.50 additional accounted spending, retaining only the previously
authorized historical $0.01 unknown reservation at index1830. Stop on any new unknown
charge. Physical exchanges meter all costs; recomposed result usage is primary only.
No additional campaign, runtime promotion, push, or publication after this experiment.

Report unexpected abstention on 163 decidable reviewed cases per pass, expected
unknown preservation, wrong definitive event AND policy decisions, legitimate versus
violation error counts, paired recoveries, latency, cost, and the separate fresh cohort.
The candidate goal remains at most eight unexpected errors per reviewed pass with no
wrong definitive judgments or loss of required uncertainty. Repeated cases are not
independent samples of production prevalence. A small fresh pack cannot establish a
5% quality bound. Audit every follow-up transformation and replay composition offline.
