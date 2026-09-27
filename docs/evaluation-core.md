# Evaluation core — step 3

Implemented in `0.1.0.dev1`. The reusable Python core and CLI assess normalized events using deterministic predicates, scripted mocks, or an explicit Jev route. It does not install hooks, serve HTTP, or execute/block a host operation. Transport contract tests pass against synthetic HTTP fixtures; the [OpenRouter live smoke passed](smoke-2026-09-27.md) using the existing Keychain credential. Direct TypeSafe still needs a credential. The owner approved a $5 total synthetic smoke cap. No semantic accuracy or enterprise-readiness claim follows from these tests.

## Run the offline example

Install using the README, then create a **new** demo directory:

```sh
humanwill-policies init-demo ./demo-core
humanwill-policies evaluate ./demo-core --config ./demo-core/config.yaml \
  --request ./demo-core/request.json --mock-answers ./demo-core/mock-answers.json --json
```

The answers file is a deliberately scripted provider-shaped map keyed by policy ID. It does not classify the text. Missing answers produce an error; a mock never requests host enforcement, even with enforcing bindings. Changing the request does not change a scripted answer. Use this to test decision plumbing, not policy quality.

`evaluate` always prints a JSON result. Exit codes: 0 = allow assessment, 3 = violation assessment, 4 = evaluation error; 2 = invalid input/configuration/options. A monitored violation still exits 3. Exit status is **not a hook response or a command to block**: connectors must interpret assessment, mode, failure behavior, and supported host capabilities separately. Validation failures provide no policy decision and must never be treated as allow.

## Versioned contracts

The Markdown format and `humanwill.request/1` remain unchanged. Original `config/1` and `result/1` validators remain available. New runtime configurations use **`humanwill.config/2`**, and evaluation emits **`humanwill.result/2`**; export them with `schema config-v2` and `schema result-v2`. This preserves the earlier frozen shapes.

Every v2 binding declares `strategy`:

| Strategy | What determines the result |
| --- | --- |
| `semantic` | One Choice question assesses the Markdown rule. Required metadata/predicates are rejected; use an explicit predicate strategy for authorization. |
| `predicates` | Code requires all declared predicates to pass. Optional `when` predicates determine applicability first. No model call is needed. |
| `scoped_predicates` | A Choice question assesses only the explicit `scope` text. If applicable, code checks all required facts and predicates; if outside scope, the rule is not applicable. Unknown scope is an error. |

For `predicates`, absent `when` means the constraints apply to every event at the policy's declared stages. Do not use that form for “finance staff may approve payments” when other tool actions share the stage: use a narrow semantic scope or authoritative deterministic applicability facts. For confidential-document rules, `when: documents.classification equals confidential` avoids applying the destination restriction to known-public material. Missing classification is unknown, never public. The packaged demo illustrates these choices but keeps metadata-dependent rules disabled.

`requires_metadata` must include every predicate/condition field; the loader does not infer it from prose. Conditions run before other required facts: a verified false condition establishes non-applicability without demanding irrelevant destination information. Otherwise all required facts must be available. This first implementation uses conjunctions only; no OR/negation language or cross-document joins. For multiple documents, an authoritative host should supply correctly aggregated facts, or assess documents separately and combine every required result; arbitrary per-document assertions must not be flattened into a misleading single value.

`equals`, `contains`, `in`, and `exists` use exact JSON values. Membership is list membership, never a substring. A verified complete empty group list is a negative fact; an absent/null/incomplete list is unknown. Mismatched scalar types and container/scalar comparisons are errors, including in applicability conditions; malformed classifications must not become non-applicability. Boolean `true` does not equal number `1`.

Default `require_complete_coverage: true` makes incomplete declared event coverage an error. An operator can explicitly choose false for a bounded assessment and must retain/report the omissions. It never expands inspection to undisclosed attachments/history. Output `coverage` repeats the validated connector declaration; per-policy status and errors state whether evaluation actually happened. No policies applicable means allow with every excluded/disabled rule visible, not a claim that the content passed a judge.

Semantic/scoped enforcement still requires an evaluation profile and matching configured model. `monitor_min_confidence` defaults to **0.8 as an uncalibrated development setting**; an enforcing profile supplies its own threshold. Below-threshold answers, tied winners, and `insufficient_evidence` yield errors. Full returned distributions and confidence are retained. This tests shape and policy logic, not whether confidence predicts correctness. Deterministic-only rules do not require a model calibration profile.

## Trusted evidence and evaluator disclosure

Wire-request `metadata` is never authoritative and is never forwarded to Jev. The core does no identity/directory enrichment. A trusted embedding verifier may supply a separate `EvidenceContext.from_verified(request, facts)` containing field/value, configured source, subject/document reference, timezone-bearing observation time, and `complete: true`. **That constructor does not authenticate facts.** The embedding application must first authenticate the source, bind identity/document versions/destinations to the actual event, and establish completeness. There is no HTTP endpoint that accepts this context and no CLI flag for declaring input facts trusted.

The core verifies the exact request digest, configured source, unique field, completeness, non-null value, and freshness. Reusing evidence after content, action arguments, destination, or coverage changes fails. Facts are checked again before returning a decision, including after a model call. The default age limit is 300 seconds with at most 5 seconds of forward clock skew. The future host must re-evaluate if the operation changes or the decision becomes stale before execution. Digests are bindings/integrity fingerprints, not cryptographic authentication of a source.

With metadata off, content-only rules continue, there is no resolver call, and raw metadata is neither used nor sent. Enabled sources remain independent. Semantic scope sees only event content and its scope rubric; it cannot supply permission. Source authentication adapters and real host provenance tests belong to step 4/5.

A **separate `EgressPermit`**, provided by the trusted embedding application, must authorize disclosing the exact event and policy bundle to the selected transport before the core makes a hosted call. It binds request digest, bundle digest, and route. Obtain it through approved deployment/data-classification rules before evaluation; do not derive it from a user claim or Jev's answer. Company policies evaluated by hosted Jev cannot retroactively protect the disclosure in that call. Monitoring does not waive the egress requirement. Python callers that can construct this object are inside the trusted process boundary.

For local, operator-controlled testing, `--backend configured --allow-external` explicitly grants that disclosure for the selected files. This flag is not an enterprise authorization mechanism and must never be set by untrusted request data. Provider keys are read only for an attempted hosted call; no credentials are stored in bundle/configuration digests.

## Providers, batching, and errors

| Route | Fixed endpoint | Example requested / accepted returned model |
| --- | --- | --- |
| OpenRouter | `https://openrouter.ai/api/alpha/decisions` | `typesafe/jev-1.13` / `typesafe/jev-1.13-20260917` |
| Direct TypeSafe | `https://api.typesafe.ai/v1/systemone` | `jev-1.13.0` / `jev-1.13.0` |

These example identities come from the current official [OpenRouter reference](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request) and [TypeSafe reference](https://docs.typesafe.ai/api), reviewed 2026-09-27. The OpenRouter identity was confirmed by the recorded smoke call; the direct TypeSafe identity remains untested here. OpenRouter's route is alpha. Requests use typed `state`/`questions`, not chat completions. Different routes may produce different judgments.

Configure `provider.transport`, `model`, `accepted_models` (exact allowlist), and `api_key_env`. Never broadly match returned models by prefix or silently accept a provider alias change. Choose/update accepted versions deliberately and re-evaluate calibration; existing profile fields alone do not prove calibration. Each batch records the returned model and available token/cost fields. Missing usage fields and failed calls have unknown values, **not zero cost**. The configured model is also recorded when a call fails.

Every answer ID must match its batch. Choice type/labels, finite probabilities in [0,1], sum within 1e-6 of one, highest-probability winner, and confidence are validated. Missing/extra answers or malformed evidence fail the whole batch. A failed batch stops further sends; pending policies become errors. Completed violations and all errors remain visible. Provider response prose/error bodies are not returned or logged.

The rubric is `humanwill.choice/1`. Event text lives in untrusted state; trusted rule/scope text lives in question instructions. This separation is **not proof of prompt-injection resistance**. Direct/indirect injection and semantic accuracy require the planned labeled live evaluation.

Runtime defaults, configurable under `evaluation`:

| Setting | Default | Allowed range |
| --- | ---: | ---: |
| `timeout_ms` | 5,000 | 1–60,000 |
| `max_batch_bytes` | 24,000 | 512–262,144 |
| `max_response_bytes` | 262,144 | 512–1,048,576 |
| `questions_per_batch` | 16 | 1–64 |
| `max_batches` | 8 | 1–64 |
| `max_in_flight` | 4 | 1–32 |
| `metadata_max_age_seconds` | 300 | 1–86,400 |

Every batch is planned before sending; oversized events/rules and excessive batch counts fail without truncation. Byte limits are not provider token-count guarantees. Sequential batches share one deadline. One reusable evaluator instance per event loop bounds concurrent provider work; overload returns an error immediately rather than retaining an unbounded queue. The HTTP client has per-operation timeouts inside the total async deadline, disables ambient proxy configuration, verifies TLS, and does not follow redirects, decompress responses, retry, or switch providers. Caller cancellation propagates and cancels cooperative I/O; a server may still bill work it already received. The implemented service additionally bounds incoming HTTP bodies and request admission before parsing; see [service reference](service-and-connectors.md).

## Assessment and requested action

Any established violation makes the aggregate assessment `block`; otherwise any error makes it `evaluation_error`; otherwise it is `allow`. Monitoring policies participate in assessment but do not request enforcement. For enforcing policies, violations request block; errors use explicit `on_error` (default block). Explicit fail-open requests allow while retaining an error assessment. A violation in one rule cannot erase an error in another.

Mock results are always `simulated: true` and request no enforcement. Real-backend results request only a host action; `enforcement.actual` is `unconfirmed` until a connector can establish what happened. Deterministic-only evaluation needs no hosted call, but mock mode still marks the entire run simulated. No executable/tool side effect happens inside this core.

## Config/3 development extension

Version `0.1.0.dev3` adds opt-in trusted-predicate short circuiting and per-stage scope questions while preserving config/2 behavior. See [config/3 semantics and migration](decision-v3.md). This produces result/3; upgrade hook clients together with the service.
