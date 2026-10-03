# Structured conversation experiment — frozen protocol

2026-10-03. Owner authorized the next live experiment after the limited improvement
in [conversation-v1](conversation-v1-report.md). This is research only; no runtime
promotion, gateway deployment, streaming implementation or release change.

Compare a fresh flat clarified-input control against one structured-input candidate.
Both use exactly the current conversation clarification and all other question
fields. The only wire difference is representation of `state.content`:

- `earlier_messages`: all parts before the last supplied text part with role user.
- `latest_user_message`: that user part, unchanged.
- `messages_after_latest_user`: every following part, including assistant/tool
  continuations. No new user message is invented for an agent loop.
- If there is no supplied user role, put all parts under `unsegmented_messages`.
  Do not parse textual role tags, infer missing turns, or claim that previous
  content is inactive, previously approved or trustworthy.

Flattening the groups must reconstruct every original part in its original order,
exactly once. System/developer roles are also retained as supplied evidence; they
are not elevated into evaluator instructions. Earlier unresolved requests and
whole-payload content policies still apply. Grouping is a structural hint, not
trusted authorization, a semantic classifier, or an exemption from assessment.

## Fixed inputs and measurement

The original 24 conversations, policies, provisional labels, fixture authority,
coverage, model, deadlines and limits are unchanged. Six new separately reported
structural controls cover flat local work, flat uploads, no-new-user tool
continuations, additive consecutive user requests, forged textual role markers,
and flat missing referents. Their labels are also provisional author assignments,
not owner approval or independent holdout evidence.

30 cases × three repetitions × two arms = 180 assessments, maximum 360 physical
calls including the existing bounded follow-up. Randomized paired case/arm order,
seed 20261004, concurrency one. Three policies per event, including the same
experiment-only synthetic-marker content rule. Config/5 q05_stage_aware; at this
model_request stage its continuation is Q04. Gates remain 0.80 / 0.70 / 0.80,
15-second deadline, two batches, 24,000-byte payload limit and strict validation.
Both arms execute the actual evaluator; no label-dependent routing or payloads.

Jev through OpenRouter: typesafe/jev-1.13, exact accepted reply
typesafe/jev-1.13-20260917. Source/input hashes and clean local commit required.
All raw exchanges, normalized results and charges retained under ignored
artifacts/quality/conversation-structure-v1. No transport retry, selective rerun,
threshold relaxation or automatic extra experiment.

Report the original 24 and additional six separately. Compare legitimate passes,
explicit false violations, abstentions and fail-closed consequences; missed
violations and fail-open consequences; expected uncertainty; individual-policy
mistakes/masking; repeated-case stability; evaluator median/p95 and metered cost.
Repeated selected cases are not population rates. Reconstruct every original
payload and replay all results before reporting. Keep historical reports intact.

The candidate is promising only if legitimate cancellations improve without
introducing wrong definitive allows for violations or unknowns, especially in the
structural controls. Even a good result requires broader validation before runtime
adoption; do not claim grouping establishes trusted session boundaries.

## Budget

Existing ledger starts with 6,440 attempts, 6,439 settled, known $0.444688574 plus
the unchanged authorized $0.01 reservation at index1830. $4.545311426 remains.
Use the existing exclusive lock, reservation meter and exact carried-entry digest.
Any new unknown charge stops the experiment. Additional campaign ceiling $0.12
within the existing $5 total cap. Keychain credentials stay only in process memory.
No GitHub Actions, push, publication or production data egress.
