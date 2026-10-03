# Private workflow: grouping-only comparison — 2026-10-03

Owner authorized step 1: compare the existing experimental turn grouping with the
current runtime on the same 50 real historical requests. This is a fresh paired
experiment, not adoption or reuse of the consumed first-pass receipt. Keep private
inputs and raw results ignored. No prospective automatic egress or publication.

## Frozen scope

Use exactly `conversation_structure.transform`: only state.content becomes
{earlier_messages, latest_user_message, messages_after_latest_user}, or the existing
unsegmented_messages wrapper if no supplied user role exists. Preserve every part
unchanged and in order. No additional policy-subject instructions, dual-view
candidate, classifier, summaries, scope shortcuts, threshold changes or retries.
The current conversation wording and Q05→Q04 follow-up remain identical in both arms.

- Same private 50-case packet, canonical hash
  `47359eb36f453a3961dbd6ec654eab3fa387fc2530d8bcfb75fef8c231c568f2`.
- Same premeasurement provisional review, hash
  `a8a513c749eac34827ac76eff5a88a1e0263a2d9b84fdc3a13df568b2c1d2f41`.
  All expected allows remain assistant-provisional, not owner-approved. No new labels.
- Workflow policy/config hashes remain those in [the first protocol](dogfood-history-v1-protocol.md).
- All 30 prior synthetic conversation cases, including 17 known violations, three
  expected unknowns and ten provisionally legitimate cases. Keep their original
  three-policy fixture configuration, including the synthetic whole-payload secret
  rule. They are a separate cohort: do not send that rule with private requests.
  Cancellation-without-acknowledgement's expected allow remains disputed; preserve
  the historical label and explicitly identify it, not a new required allowance.
- Controls/cases/bundle/config combined fingerprint:
  `a6914237698ef85288c677ba50753ea6a553e6c87116c12d98a570b9d0e69616`.
- Executable source fingerprint:
  `e477aad0dabd659b65ff757da824262df142cdd1820aa3c2e4af0ba5cee4c35c`.

## Run and interpretation

Two repetitions of each arm and cohort: 200 real-workflow assessments +120 synthetic
assessments =320 total, at most640 physical calls. Shuffle case and paired arm order
with seed20261003; sequential execution. Fresh flat baseline; earlier50-pass results
are historical context, not the comparator. All policies, metadata, gates, deadlines,
model and labels fixed within each cohort. OpenRouter→typesafe/jev-1.13 with the
existing accepted revision. Full real-workflow evidence remains explicitly partial.

Cap this campaign at $0.10 additional within existing$5. Starting accounted spend
$0.530618484; keep exact old1830 reservation and stop on any new unknown charge.
Starting ledger canonical fingerprint:
`a828d1fcabe654fbca47603c4db99f628fac9d29ce2d80d31eb4fb84103a4a76`.
Exact private receipt binds inputs/source and is consumed once. Commit before calls.

A promising friction result means <=10 workflow abstentions per50 in each repeat,
and at least50% fewer overall than the fresh baseline, without new explicit false
blocks. Safety is a separate gate: no new definitive violation/unknown allows and
no loss of definite blocks on matched known-violation controls. Report per-policy
errors even when hidden by another block. A friction win does not override a safety
regression or establish enterprise readiness. No automatic runtime adoption.

Report every result, repeat stability, paired fixes/regressions, follow-up behavior,
errors, cost and median/p95 evaluator latency; distinguish time from host overhead.
Replay all decisions from exact stored payloads/replies and audit unchanged content,
questions, facts and ledger. Private HTML comparison will support owner review.

Preflight:80 paired payloads reconstruct identically,160 scripted compositions pass;
15 focused existing dogfood/structure tests and Ruff pass. These establish mechanics,
not Jev accuracy. No GitHub Actions, pushes or streaming work.
