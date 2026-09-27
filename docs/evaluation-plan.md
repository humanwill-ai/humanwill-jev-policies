# Evaluation plan

Development comparisons complete; release evaluation open · 2026-09-27

The current [release-gate audit](step6-release-gates.md) recomputes the clarified-policy Jev results against approved targets and provides a [36-case editable label-review packet](step6-review-candidates-v1.md). The packet is a pre-review calibration tranche, not an independent holdout. Packaging and offline operational checks can proceed in parallel; labels, independent sampling and live end-to-end latency remain open.

The [public-release roadmap](public-release-plan.md) specifies the initial held-out sample proposal and report/publication gates. The owner approved the initial per-policy targets before live development measurements: 95% interval upper bounds ≤5% for false blocks and missed violations, ≤5% errors on fully specified cases, p95 added latency ≤2 seconds, and evaluator API cost ≤$1 per 1,000 cases. Held-out evaluation still requires reviewed labels and independent scenario families.

## Begin with policies and labels

Review the [test policy definitions](test-policies.md) with the owner before building the dataset. The owner selected project-code/design/documentation protection to replace the customer-communication candidate and confirmed that approved systems are permitted. The other two candidates use the proposed boundaries for the initial development run; detailed labels remain subject to review:

| Candidate | Legitimate near-neighbor | Violation / evidence needed |
| --- | --- | --- |
| Protect project source code and technical material (`EVAL-SW-001`) | Share a patch through an explicitly approved private repository or AI route | Project snippets, designs or documentation disclosed to an unapproved destination; trusted destination approval required |
| Restrict confidential exports to approved destinations | Explain export procedures using synthetic data | Classified content sent externally; destination and classification from trusted systems |
| Restrict destructive production actions | Read-only investigation or deletion in an authorized disposable sandbox | Destructive command against production; environment and authorization verified independently |

For each policy, define scope, exceptions, required evidence, unknown handling, and intended host action. Do not replace company rules with broad provider moderation defaults. If required trusted evidence is unavailable, label the case unknown/insufficient evidence rather than guessing from the user's claim. For the owner-clarified software rule, a completed lookup that finds no explicit approval for the actual onward destination/operation is a violation, including unknown or unspecified destinations. A failed lookup is an evaluation error. Coding help inside the configured approved model conversation is allowed; the approved model does not authorize onward sharing.

Build a small development set first, then a separately held-out set sized to the agreed error tolerance. Include benign/violation pairs, ambiguous cases, languages used by customers, long histories, missing attachments, spoofed metadata, and malformed/unsupported inputs. Record label rationale and adjudicate disagreements with a second human reviewer. Keep related templates and paraphrases in the same split to reduce leakage. Synthetic examples alone do not establish customer performance.

## Comparison and measurement

Compare deterministic rules, Jev, and a reasonable chat-model judge with the same available evidence. The development comparison already used Gemini as the alternative; no further Gemini tuning is required to prepare the Jev release.  Tune each on development data, freeze its rubric/thresholds/model, and evaluate held-out cases. Keep semantic judgments separate from exact authorization and destination checks.

- **False-block rate:** legitimate examples blocked / all legitimate examples.
- **Missed-violation rate:** violating examples allowed / all violating examples. Report downstream violations that actually proceeded separately, including bypasses.
- Report review/abstention, evaluation-error, unsupported-content, and uninspected rates separately. Include every example in the outcome table; do not hide errors by dropping them from a denominator or treating them as correct judgments.
- Break down results by policy, integration, language, context size, and adversarial slice. Include sample counts and confidence intervals; zero observed errors in a small set is weak evidence.
- Measure added end-to-end p50/p95/p99 latency, evaluator time, cold/warm behavior, concurrency, rate limits, retries, and cache-off versus cache-on operation.
- Count billed input, all evaluation calls/retries, hosting/networking, maintenance, labeling, and user/reviewer effort. Report cost per 1,000 evaluated requests with workload and assumptions.
- Repeat a subset to characterize judgment variability and calibrate any confidence-based decision policy. No universal threshold is assumed.

## Attack and connector tests

Attempt direct evaluator manipulation and indirect injection in retrieved text, repository files, history, and tool outputs. Include quoted attacks in benign work, role/metadata spoofing, encoding, distractor context, and malicious text arguing for its own classification. Preserve a held-out attack set after tuning.

For each pinned host version/configuration, test allow/block, malformed answers, missing question IDs, unknown policies, missing trusted metadata, unsupported review, oversize payloads, unavailable service, slow evaluator, rate limiting, cancellation, disabled hooks, and direct bypass routes. Verify whether the backend model was called or tool actually executed using a controlled mock downstream and host logs. Do not infer enforcement solely from our service's returned decision.

Test metadata as an optional feature: content-only requests with metadata absent/off, no enrichment calls or metadata forwarded when off, independent source enablement, explicit disabled policy bindings, and configuration rejection for enforcing policies whose required sources are disabled. At runtime distinguish absent/untrusted/stale facts from a verified negative fact (for example, a complete group list without finance). Include spoofed group claims and classification/destination mismatches. Verify the switch never disables connector authentication.

Test each governed stage independently: an allowed prompt can yield a disallowed answer or tool action. For planned non-streaming response enforcement, assert that no generated content is delivered before the verdict. For actions, assert no controlled side effect before the pre-tool decision. Route changes and argument/document changes must not reuse an obsolete authorization. Reject unsupported-stage enforcement bindings and report post-execution observations as audit, not prevention.

Initially use offline fixtures and synthetic content. OpenRouter is the selected development/test route; direct TypeSafe is also a release requirement. Do not submit private customer examples without authorization. Hosted flow is host → connector → our service → OpenRouter → TypeSafe → our service → host, or directly to TypeSafe. Both rule text and evaluated content may be transmitted. Check evaluator-destination authorization before sending content: a hosted evaluator cannot prevent the disclosure that occurs in its own request. Document every logging/telemetry recipient too. Default logs should contain IDs, versions, coverage, timings, and outcomes rather than raw prompts or secrets.

## Gates

1. **Discovery alongside engineering:** identify concrete recurring pain and users willing to validate examples; perform a bounded reuse review during the offline foundation. This need not block M1 in the release plan.
2. **Offline quality:** agree per-policy error/latency/cost tolerances in advance; held-out results, including uncertainty and attacks, must support the intended action.
3. **Connector conformance:** demonstrate coverage, identity provenance, actual enforcement, and the host's failure behavior on pinned versions. Reject unsupported policy/connector combinations explicitly.
4. **Monitoring pilot:** with authorized data flow, measure representative traffic without blocking; keep assessment and actual outcome distinct.
5. **Limited enforcement:** only for policies meeting agreed gates, with rollback and monitoring. A bypassable/fail-open host cannot be presented as a mandatory security boundary.

The owner authorized synthetic step 6 OpenRouter evaluations within the remaining original $5 total budget and the initial targets above. No customer pilot, production rollout or public publication is authorized. See [the development suite](../evals/step6/README.md) and [label review](step6-label-review.md).

## Initial development evidence

See the [dated baseline report](evaluation-development-report.md) for the first 60-case comparison, threshold replay and repeat checks, and the [config/3 follow-up](evaluation-v3-report.md) for revised runs plus 36 matched attack/control cases and separate model/policy calibration diagnostics. Neither semantic configuration supports an enforcement claim. Review [draft labels](step6-label-review.md) before tuning and freezing the held-out protocol.

## Current gate preparation

`python -m evals.step6.gates --candidate` validates the candidate/configuration/bundle/source snapshot and structural checks without calling a provider. Repeated `--run` arguments audit compatible development artifacts, showing per-policy confidence upper bounds, specified errors, core/provider latency and evaluator API cost. The tool never establishes human review from editable metadata or reports these development runs as a passed release gate. See [remaining steps and current observations](step6-release-gates.md).
