# Small tool-classification probe — 2026-09-30

Owner requested a small live diagnostic on known failing tool requests. Freeze ten
previously failing tool-action cases plus six controls, two repetitions, all from
the unchanged owner-reviewed pack. Controls include an explicit upload violation,
a read-only action, a prompt merely discussing a command, and three expected
unknowns. Same policy bodies, neutral context, trusted metadata, Q05 primary,
.80/.70/.80 gates, same-choice acceptance rule and strict response validation.
These targeted cases cannot estimate general abstention or establish a release gate.

Each event gets a fresh shared Q05 primary. A separate policy-free Jev choice batch
classifies execution intent and immediate operation category using only that event
and its already supplied neutral context. It returns no free-form generated tool
names or authorization facts. Tool names and exact arguments remain available from
the original event. No manual command parser or test labels supply the model's
classification. Labels used to diagnose classifier accuracy are newly authored,
provisional, and never sent to Jev.

Compare three randomized continuations only when the primary has eligible
low-confidence applicable/not_applicable answers under evaluation_error:

1. Current full-batch Q04.
2. A fixed question explicitly about actual proposed tool use and its arguments.
3. That same tool question, selected only when Jev confidently identifies proposed
   execution. Add its confidently identified operation category as an explicitly
   untrusted hypothesis; retain every policy and the original event. If execution
   intent is uncertain or not execution, fall back to Q04. Unknown/low-confidence
   operation categories add no hypothesis. Classifier gates are fixed at .70 with
   a unique maximum, an experimental setting rather than a calibrated guarantee.

This extra wording control separates possible classification benefit from merely
asking a more direct tool question. The classifier is also called on settled
controls solely to audit its errors. A hypothetical runtime would call it only on
eligible abstentions. Report those diagnostic costs separately from cascade costs.
No accepted decision is overwritten. Missing-metadata errors, malformed primary
answers, raw insufficient_evidence and errors masked by a block are not refined.
All secondary accepted choices must agree with the primary and meet its unchanged
gate; trusted checks still determine allow/block. Classification is never permission.

Each policy follow-up arm has one call. The classified arm therefore has up to two
extra calls (classification plus policy reassessment), compared with one for Q04.
Its measured cost and latency include both, within the same total 15-second event
budget; other experimental branches' wall time is excluded. Preserve full original
question batches. A classifier/secondary validation failure or exhausted deadline
is recorded; do not retry transport failures. Stop immediately on any new unknown
charge, carrying only the exact historical index1830 reservation.

At most 160 physical calls: 16 events × 2 passes × (primary + classifier + three
conditional reassessments). Additional ceiling $0.10 within the existing $5 cap;
no new spending permission is needed. Freeze protocol/source and initial ledger
hash before calls. No runtime changes, new policy, deployment or push.

Report event and individual-policy outcomes, accepted judgments, expected unknowns,
conflicts, malformed responses, confidence changes, classification mistakes, timing
and actual usage. Compare recovery on the same primary abstentions, report every
selected case, and do not reword or selectively rerun after seeing results. A useful
signal would be repeatable additional recoveries over both controls without new
wrong accepted outcomes; otherwise stop and explain the negative or inconclusive
result. Even a positive result only justifies broader prospective validation.
