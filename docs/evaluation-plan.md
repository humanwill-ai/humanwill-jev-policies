# Evaluation plan

Proposed, not yet run · 2026-09-27

## Begin with policies and labels

Select three rules with a prospective user. Illustrative candidates, not adopted company policies:

| Candidate | Legitimate near-neighbor | Violation / evidence needed |
| --- | --- | --- |
| Restrict confidential exports to approved destinations | Explain export procedures using synthetic data | Classified content sent externally; destination and classification from trusted systems |
| Restrict destructive production actions | Read-only investigation or deletion in an authorized disposable sandbox | Destructive command against production; environment and authorization verified independently |
| Restrict abusive operational assistance | Defensive analysis, quoted malicious text, and authorized research | Concrete assistance violating the company's defined rule; intent judgments separated from authorization facts |

For each policy, define scope, exceptions, required evidence, unknown handling, and intended host action. Do not replace company rules with broad provider moderation defaults. If trusted evidence is absent, label the case unknown/insufficient evidence rather than guessing from the user's claim.

Build a small development set first, then a separately held-out set sized to the agreed error tolerance. Include benign/violation pairs, ambiguous cases, languages used by customers, long histories, missing attachments, spoofed metadata, and malformed/unsupported inputs. Record label rationale and adjudicate disagreements with a second human reviewer. Keep related templates and paraphrases in the same split to reduce leakage. Synthetic examples alone do not establish customer performance.

## Comparison and measurement

Compare deterministic rules, Jev, and a reasonable chat-model judge with the same available evidence. Select the alternative after data-egress and budget decisions. Tune each on development data, freeze its rubric/thresholds/model, and evaluate held-out cases. Keep semantic judgments separate from exact authorization and destination checks.

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

Initially use offline fixtures and synthetic content. OpenRouter is the selected development/test route; direct TypeSafe is also a release requirement. Do not submit private customer examples without authorization. Hosted flow is host → connector → our service → OpenRouter → TypeSafe → our service → host, or directly to TypeSafe. Both rule text and evaluated content may be transmitted. Check evaluator-destination authorization before sending content: a hosted evaluator cannot prevent the disclosure that occurs in its own request. Document every logging/telemetry recipient too. Default logs should contain IDs, versions, coverage, timings, and outcomes rather than raw prompts or secrets.

## Gates

1. **Discovery alongside engineering:** identify concrete recurring pain and users willing to validate examples; perform a bounded reuse review during the offline foundation. This need not block M1 in the release plan.
2. **Offline quality:** agree per-policy error/latency/cost tolerances in advance; held-out results, including uncertainty and attacks, must support the intended action.
3. **Connector conformance:** demonstrate coverage, identity provenance, actual enforcement, and the host's failure behavior on pinned versions. Reject unsupported policy/connector combinations explicitly.
4. **Monitoring pilot:** with authorized data flow, measure representative traffic without blocking; keep assessment and actual outcome distinct.
5. **Limited enforcement:** only for policies meeting agreed gates, with rollback and monitoring. A bypassable/fail-open host cannot be presented as a mandatory security boundary.

No numerical launch thresholds, pilot permission, paid API budget, or production rollout is approved yet.
