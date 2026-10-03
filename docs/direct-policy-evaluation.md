# Evaluate the actual company policy

Config/5 makes the Markdown policy body the semantic rule sent to Jev. The adapter
supplies one reusable evaluation template; the company does not write a second
natural-language question for each policy. This is an opt-in implementation. Its [first live comparison](direct-policy-live-v1-report.md)
regressed; it is not an accuracy improvement. Historical configurations and results
remain reproducible at their recorded revisions.

## Runtime flow

Unreleased config/5 model-request questions include a
[conversation-scope clarification](conversation-inspection.md): interpret active
work using the full supplied history, without exempting historical content or
trusting embedded blocking/approval claims. The [live comparison](conversation-v1-report.md)
shows a partial improvement with substantial remaining abstention; the historical
single-event measurements below do not establish conversation accuracy.

1. A connector supplies the developer's prompt, model request, proposed action or
   outgoing response, with its inspected coverage.
2. The adapter loads the applicable Markdown policies and deployment bindings.
3. For each rule needing semantic evaluation, it combines the full loaded Markdown
   body, policy ID/version/title, stage and the common template into a Jev question.
   The event goes in the separate `state` input. No second model rewrites the policy.
4. Jev returns a structured judgment. Code applies confidence gates and, where
   required, verified metadata predicates before making the decision.
5. The connector translates that decision into its supported host behavior.
   Copilot CLI submitted-prompt hooks remain assessment-only.

The same template serves every policy ID and every company. Stage descriptions
are shared adapter code, not case-specific hints. Editing a policy body changes
both the question and configuration digest. Collection prose is organizational;
only each loaded policy's own body is the rule. Explicit collection includes load
other policies, not text substitution into one rule.

## Three binding strategies

| Strategy | Jev's job | Code's job |
| --- | --- | --- |
| `semantic` | Assess the full rule: compliant, violation or insufficient evidence | Apply thresholds and failure handling |
| `scoped_predicates` | Determine from the actual policy whether its conditional restriction applies | Check all declared trusted permission predicates when applicable |
| `predicates` | No model call | Evaluate configured conditions and trusted predicates |

A scoped rule must represent **governed behavior requires these trusted conditions**.
The operator must bind all permission requirements. Split independently governed
clauses into separate policy IDs; attaching a predicate does not automatically
translate an arbitrary handbook into executable checks. Positive predicate short
circuiting is optional and is valid only when those predicates completely satisfy
the conditional permission rule. When enabled, it can skip Jev entirely.

For example, the Markdown rule may say only verified finance staff can approve
payments. The adapter asks whether the supplied event is governed by that rule;
code checks authenticated group membership. Jev sees the declared metadata field
names, not the actual trusted facts or predicate values. A user's claim to be in
finance supplies no authorization. Missing required facts remain an error when
the rule applies.

Metadata remains independently optional. Content-only semantic rules work with it
disabled. Identity, source, destination and classification checks require protected
configuration or an authenticated resolver. This change does not supply a production
source resolver or discover permissions from natural language.

## Try and inspect it offline

```sh
humanwill-policies init-demo demo
humanwill-policies preview demo --config demo/config-policy-text.yaml --stage prompt --json
humanwill-policies evaluate demo --config demo/config-policy-text.yaml \
  --request demo/request.json --mock-answers demo/mock-answers.json --json
humanwill-policies schema config-v5
humanwill-policies schema result-v4
```

`preview` includes `evaluation_questions` with exactly the templates the evaluator
constructs. Disabled policies may also have templates in preview; their status
still determines whether they run. Pure deterministic rules have no questions.
The actual batch also depends on request stage, enabled policies and shortcuts.
The demo uses scripted answers and makes no external API calls.

Config/5 removes `scope` and `scope_by_stage` and rejects them rather than silently
ignoring old text. Start from config/4, remove those fields, and change `format` to
`humanwill.config/5`. When migrating config/3, also replace legacy confidence
settings with the three global `outcome_thresholds`. All default to 0.80.
Reassess rule-to-predicate bindings and evaluate fresh model answers before enabling
enforcement. Config/5 emits `humanwill.result/4` with rubric `humanwill.policy/1`;
upgrade hook clients with the service. Old config/result formats keep their behavior.

All model-bound policies use their full loaded bodies: oversized batches fail
explicitly, without truncating the rule. The shared template treats event content
as evidence rather than instructions to the evaluator; this is no guarantee of
prompt-injection resistance. Hosted evaluation sends policy text and inspected
content externally through the selected provider, under the existing egress controls.
Preview output also contains policy text.

## Evaluation status

`evals/step6/direct-policy-v1/config.yaml` uses the four existing synthetic policies,
unchanged labels, monitor modes, trusted predicates, model and 0.80 gates. It
supersedes the hand-written source-question candidate as the next proposed live
experiment, while preserving that candidate and its historical snapshot.

Offline checks compare decision plumbing over all 175 accepted events using scripted
scope answers and the frozen context sidecar. They do not measure Jev interpretation.
The fixture context wrapper remains an evaluation tool, not automatic production
context enrichment. Next: freeze a new live protocol and obtain fresh Jev answers
for the full pack, reporting regressions and latency/cost as well as improvements.
Stored-answer replay cannot measure this change. Existing live reports concern the
older questions and do not qualify this template for enforcement.

Local verification on 2026-09-28: 198 offline tests pass on Python 3.14;
seven focused template tests and 14 service tests also pass on Python 3.11.
Ruff passes. Wheel and source installations outside the checkout pass the new
schema/demo checks, all connector contract tests and service startup/rollback
checks. This is adapter contract evidence, not a fresh test of the actual host
applications. No provider calls were made; the $5 ledger remains unchanged.

The subsequent authorized [full-pack live run](direct-policy-live-v1-report.md) matched 142/175 outcomes versus 166/175 previously. Keep this template experimental; no thresholds or policies were changed in response.

## Active development thresholds — 2026-09-28

The owner applied the proposed settings after the recorded-answer review:

```yaml
outcome_thresholds:
  applicable: 0.80
  not_applicable: 0.70
  insufficient_evidence: 0.80
```

Use `evals/step6/direct-policy-v2/config.yaml` for the active synthetic development
configuration. The packaged `demo/config-policy-text.yaml` uses the same explicit
thresholds. The frozen v1 configuration and prior measured results remain unchanged;
the historical runner still targets v1. Loader defaults for omitted thresholds
remain 0.80, so select the explicit current configuration. Both examples remain
monitor-only. No test, replay or provider call was run when applying this change,
as requested. The previous offline replay identifies 23 legitimate events still
failing; review them one by one before further tuning.

The subsequent [focused-question full-pack experiment](focused-policy-v1-report.md) improved151→156 matches at the active gates and reduced legitimate fail-closed blocks23→14, but introduced8 regressions. It remains an evaluation-only candidate; the service's shared template was not replaced.

A further [clarified scope-question candidate](clarified-question-and-error-review.md) distinguishes no covered action from missing information about a potentially relevant action. It is saved as focused-policy-v2 with an opt-in research wrapper; no new live evaluation or runtime promotion has occurred.
