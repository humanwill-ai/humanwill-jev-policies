# Context-only evaluation preparation

2026-09-28 · preparation record; the [live comparison is now complete](context-live-v1-report.md)

The frozen files retain their pre-measurement status for provenance. The details
below describe preparation; the dated live report supersedes pending-run wording.

The owner requested clearer context while leaving everything else unchanged.
This experiment adds `state.assessment_context` to Jev's input for the existing
175 accepted events. It does not change policy text, scope questions, event text,
expected labels, active policies, trusted permission facts, the 0.80 confidence
threshold, model selection, monitoring mode or decision composition. The seven
removed cases stay excluded. The original [first live run](reviewed-live-v1-report.md)
and all its frozen inputs remain intact.

## What Jev will receive

| Context | Example | Source |
| --- | --- | --- |
| Assessment point | A proposed tool call, before execution | Existing event stage |
| Tool contract | `shell` executes its command argument; `send_document` sends a referenced document | Synthetic tool definitions and original review assumptions |
| Resource information | The vendor URL returns an ordinary documentation page for reading | Existing accepted fixture description |
| Origin lookup | Resolved Git/package origins and operations, or an unavailable lookup | Existing synthetic source descriptors |
| Missing material | `/srv/shipping.yaml` has not been supplied; its definitions and image references are unknown | Existing accepted fixture description |

All 175 cases have an explicit assessment point. Tool calls have a tool contract;
139 cases carry the existing software-origin lookup context, and 13 have additional
resource observations. The observations are in a separately editable
[context file](../evals/step6/context-v1/observations.json), with per-case provenance.
The [complete prepared contexts](../evals/step6/context-v1/contexts.json) are bound
to the exact original request hashes. A [snapshot](../evals/step6/context-v1/snapshot.json)
records the preparation code, observation and context hashes without replacing
the original evaluation protocol.

Expected answers, review rationale, reviewer notes, classification, authorization
booleans and catalog matches are not copied into model context. Resource endpoints
and operations describe what an event involves; deterministic code still checks
whether they are approved. A missing script or manifest remains missing. We do
not add invented script bodies, tell Jev that a command is harmless/destructive,
or expand flags into precomputed policy verdicts.

The original scope questions still instruct Jev to treat state as evidence, not
instructions or permission. The new field stays separate from event text: it is
not appended to an assistant response or disguised as a user message. The
experiment's operator-owned fixtures supply it; requester-supplied metadata does
not populate it. The wrapper does not authenticate arbitrary callers or implement
a production context resolver.

## Review and use

Open [the case-review page](case-review.html) locally. Each accepted case shows:

1. Its original event.
2. The additional context, in readable form and exact JSON.
3. The unchanged expected result and policy text.
4. The actual stage-specific scope questions used by the evaluator.

The page preserves all existing approvals, notes, removals and local edits. Its
labels remain the original reviewed labels. The context panel is clearly marked
as prepared and not yet measured; it does not retroactively become part of the
previous approval or live run. Exports include the context-preview hash separately
from the original review fingerprint. Removed cases have no new context panel.

Validate the preparation or inspect one case without API calls:

```sh
.venv/bin/python -m evals.step6.question_context
.venv/bin/python -m evals.step6.question_context \
  --case holdout-v1-prod-kube-replace-force
```

The opt-in `ContextBackend` in `evals/step6/question_context.py` wraps an evaluator
backend for the next experiment. Load its records through `load_contexts()` and
bind the chosen record to the original request. The wrapper adds only the context
field. It enforces the existing payload-size limit before the delegate can reserve
money or make a call; it requires explicit context-egress authorization for an
external backend. Existing source evidence, model questions and the evaluator are
reused unchanged. The original live runner continues to reproduce the original
inputs; it does not silently switch to the new context. No shipped service or
connector behavior changes in this increment.

## Verification and interpretation

Offline checks compare original versus enriched provider payloads across all 175
cases and require exact equality after removing `assessment_context`. Scripted
semantic answers produce identical decisions for all 175 events. Tests also cover
changed-event rejection, missing material, independence from labels/review prose/
permission facts/wire metadata, and byte-limit/egress failures before delegate calls.
These checks establish isolation and composition, not improved Jev accuracy.

This is development on already observed cases. Any improvement in a future run
would measure the benefit of additional context on this set; it would not be an
independent holdout result or proof that a production connector can obtain those
facts. In particular, document type and local-script descriptions are synthetic
fixture observations, not new inspections of real resources. Production collection
of equivalent context remains separate integration work.

Next: run the complete context-only comparison when requested, preserving the
baseline and all failures. Keep thresholds, policies and questions unchanged for
that comparison. No API charges were incurred by this preparation.
