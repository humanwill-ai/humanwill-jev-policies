# Actual-effect question and tool-context diagnosis

2026-09-28. The owner requested review and fixes for the remaining nine legitimate
evaluation errors. This experiment separates a common wording change from adding
neutral descriptions of command effects. It does not change company policy or
require the company to author internal evaluation questions.

## Diagnosis and proposed correction

The saved answers do not expose Jev's internal reasoning. These are testable
hypotheses, not established causes:

| Cases | Likely distinction lost | Correction |
| --- | --- | --- |
| Local base64 and tar (2) | Protected material versus its transmission | Ask about actual effects; do not infer a subsequent upload. |
| rsync, Kubernetes, PostgreSQL, Terraform and Ansible previews (5) | Describing a destructive change versus performing it | Supply precise tool semantics separately from the policy judgment. |
| Printed download command and response warning (2) | Mentioning/prohibiting versus executing/instructing | Make the shared question stage-aware and consider quoting, negation and compound actions. |

The candidate also includes the previously prepared distinction between no relevant
action and missing information about a relevant action. Policies, labels, requests,
confidence gates and failure handling remain unchanged.

## Exact experiment

- `evals/step6/effect-question-v1/question.json` contains the complete new common
  task and criteria. The original policy bodies and evaluator instruction boundary
  remain in every payload.
- `question_only`: that wording, with the same context as focused-policy-v1,
  including its existing git-apply note.
- `question_and_context`: identical wording plus 17 event-bound tool descriptions,
  covering eight of the nine target cases, eight violation controls and a second
  literal-print example. The natural-language warning gets no extra description.
- Both arms evaluate all 175 approved events / 272 policy outcomes, requiring
  148 calls each (296 total). Alternate arm order by case index; no retries or
  selective reruns. Compare all results with saved focused-policy-v1 and each other.
- Active gates remain applicable 0.80, not_applicable 0.70 and
  insufficient_evidence 0.80. No probability normalization or validation relaxation.
- Preserve all missing-script/manifest unknowns, positive controls, generic/advanced
  scope assignments and original labels. Report failures and regressions even if
  the target nine improve.

The existing $5 authorization covers these synthetic Jev/OpenRouter calls.
Pre-run ledger: 1,808 settled step6 calls, $0.108620282 cumulative, $4.891379718
remaining, zero unknown charges. Use the existing lock/ledger and Keychain helper;
never persist credentials. Raw payloads/responses stay in ignored local artifacts.

Hashes of input files, evaluator/runner source and prior artifacts are frozen in
`protocol.json`. Local composition tests inspect all 175 events under all three
payload conditions; mutation tests reject a context note reused for altered
arguments. These tests validate construction, not semantic accuracy.

## Basis for tool descriptions

Reviewed official documentation on 2026-09-28; descriptions assume the normal
documented executable behavior already declared by the frozen synthetic fixtures:

- Local encoding changes representation; archive creation writes an archive.
  Whether those bytes then leave the machine depends on the supplied operation.
  [GNU base64](https://www.gnu.org/software/coreutils/manual/html_node/base64-invocation.html),
  [GNU tar](https://www.gnu.org/s/tar/manual/html_section/create.html).
- rsync dry-run previews changes; without it, deletion synchronization can remove
  destination files. [rsync manual](https://download.samba.org/pub/rsync/rsync.1).
- Kubernetes client dry-run does not submit the deletion for execution. This does
  not claim that every client operation is offline or free of reads/authentication.
  [kubectl delete](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_delete/).
- PostgreSQL EXPLAIN plans; ANALYZE executes the supplied statement as well.
  [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/current/sql-explain.html).
- Terraform plan does not apply proposed resource destruction; destroy does.
  Planning may read remote state or invoke provider/data-source code, so this is
  not a general no-side-effects guarantee.
  [Terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan),
  [Terraform destroy](https://developer.hashicorp.com/terraform/cli/commands/destroy).
- Ansible's built-in file module supports check mode, predicting the target change
  without modifying it. This is not a universal guarantee for arbitrary modules.
  [Ansible file module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/file_module.html).
- Single quotes preserve literal shell text. Command substitution executes the
  nested command even when its output is printed. The positive control retains
  that execution despite a misleading trailing comment.
  [Bash manual](https://www.gnu.org/software/bash/manual/bashref.html).

## Interpretation and production boundary

One observation per arm cannot separate stochastic variation from treatment
effects; the old-question baseline is recorded, not freshly repeated. This is
development diagnosis on a repeatedly inspected dataset, not an independent
holdout or calibrated-confidence result. Improved confidence is not proof of
Jev's internal reasoning.

Descriptions contain no expected labels, authorization values or source approval
verdicts. They are operator-authored fixture context bound to an exact event, not
trusted user claims or a newly implemented command parser. They show what usable
tool context could provide. A production connector needs a verified structured
tool contract to make comparable claims; a raw shell string alone does not supply
that guarantee. Advanced-command cases remain diagnostics outside initial release
acceptance. No runtime template promotion, publication or deployment is part of
this experiment.

Run from the frozen clean commit:

```bash
.venv/bin/python -m evals.step6.effect_question_live \
  --original artifacts/quality/direct-policy-live-v1 \
  --baseline artifacts/quality/focused-policy-live-v1 \
  --output artifacts/quality/effect-question-live-v1 \
  --allow-external \
  --keychain-helper /Users/sergio/Documents/humanwill-benchmark/humanwill/keychain.py
```
