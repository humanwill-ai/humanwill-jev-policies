# Decisions and open requirements

Updated 2026-09-27. Owner requirements and proposed implementation choices are separate.

| Topic | State | Current direction |
| --- | --- | --- |
| Repository | Decided by owner | Private `humanwill-ai/humanwill-jev-policies`, alongside `humanwill-ai/humanwill-evals` |
| Project relationship | Decided by owner | Companion to `humanwill-benchmark`, applying company-driven policies to agents |
| Policy ownership | Decided by owner | Users/companies supply their own policy sets |
| Policy authoring | Decided by owner | Markdown folder, main file references same-folder/subfolder files, stable ID for each policy |
| First-release connectors | Decided by owner | LiteLLM, Agentgateway, and Copilot hooks; all three required |
| Jev access | Decided by owner | Direct TypeSafe and OpenRouter; OpenRouter for development/testing |
| Copilot runtime(s) | Decided by owner | Both VS Code Local and Copilot CLI, with distinct contracts |
| Contextual metadata | Decided by owner | Optional; easy enable/disable; combine trusted facts with semantic judgments, never accept claimed authorization as proof |
| Metadata defaults | Adopted for foundation | Off by default; independent source configuration; content-only policies still work; explicit treatment of dependent rules |
| Stage coverage | Decided by owner | Generated-answer and action policies require checks at those stages |
| Folder schema | Implemented v1 | Front matter, explicit includes, one policy per file, immutable hashes; see release plan/examples |
| Runtime stack | Foundation implemented; service proposed | Python 3.11–3.14 offline package/CLI on Linux/macOS; HTTP/provider/connector modules remain pending |
| Build versus extend | Adopted after bounded review | Original independent core; no upstream code/text copied; see compatibility/reuse review |
| Initial enforcement | Proposed | Text gateway requests and non-streaming responses, plus supported pre-tool/prompt hooks; monitoring first |
| Uncertainty/failure | Proposed | Explicit error/indeterminate result; configurable failure action, default block in enforce mode |
| Human review | Proposed exclusion | Reject unsupported review configuration; no approval workflow in v0.1 |
| Customer demand | Unvalidated | Enterprise platform/security teams are the target, not validated paying customers |
| Hosted customer data | Open | Confirm policy-text/content egress, destinations, retention, and geographic constraints |
| Live budget / quality targets | Smoke budget approved; quality targets open | Owner authorized up to $5 total for synthetic OpenRouter/direct smoke tests; semantic acceptance targets remain unapproved |
| Public release objective | Decided by owner | Plan a first release suitable for public GitHub publication; visibility remains private during preparation |
| Release label / artifacts | Proposed | `v0.1.0a1` public preview, source/wheel/checksums and evidence; see public-release roadmap |
| Project license | Awaiting owner choice | Proposed Apache-2.0 for original code/docs/examples; preserve licenses of reused material |

## Requirement update: 2026-09-27

The owner expanded the initial two-integration suggestion to three mandatory connector families, specified Markdown policy folders and IDs, and selected OpenRouter for development. These supersede the initial choice between Agentgateway and VS Code as a second integration. The enterprise focus and relationship to HumanWill Benchmark are now explicit.

Follow-up: metadata must be optional and switchable, including user/group information. Metadata-dependent policies still need authoritative evidence; turning the feature off cannot establish authorization. The owner also requires checks at the stages governed by a policy. The proposed release now includes non-streaming gateway response checks, superseding the earlier response deferral; unavailable stages remain explicit limitations. See [metadata and stage design](optional-metadata.md).

Publication planning: the owner requested steps toward a confident public first release. The [public-release roadmap](public-release-plan.md) adds real-runtime evidence, semantic evaluation, packaging, licensing, and a public-content review. Private alpha validation becomes preparation for the proposed public preview. Publication itself awaits a completed, reviewable candidate and owner go-ahead.

## Next concrete work

Steps 1–2 of the [public-release roadmap](public-release-plan.md) are implemented: authoring/configuration contracts, package/CLI, loader, IDs/digests, preview, tests, and CI. See the [foundation report](foundation-report.md). The roadmap now uses one-based numbering to match the requested steps; these were previously rows 0–1. No model calls, service, or connectors were implemented in this increment.

Step 3 software is now implemented: mock/backend abstraction, deterministic and scoped predicates, strict Jev adapters, bounded batching/deadlines, and an assessment CLI. Its OpenRouter live smoke passed using Keychain; the direct TypeSafe live smoke is optional for v0.1 per owner decision. The owner approved a $5 total synthetic smoke cap. See [core contracts](evaluation-core.md) and [evidence](evaluation-core-report.md). Do not interpret a valid evaluation-profile configuration as measured accuracy.

Foundation decisions: package/CLI `humanwill-policies`, import `humanwill_policies`, version `0.1.0.dev0`; explicit include lists and one policy per file; reject all symlinks under the root; bounded restricted YAML; exact source and normalized configuration hashes; monitoring defaults and required explicit policy bindings. Freeze authoring format v1 and candidate request/result fixtures with versioned changes. Candidate host versions are recorded but untested; final VS Code Copilot extension build remains an integration-stage choice.

## Additional requirements and ideas

Append dated requirements here and update the plan when they change scope.

## Step 3 decisions — 2026-09-27

- Preserve original v1 shapes; use config/2 for explicit strategies, deterministic applicability conditions, limits, and returned-model allowlists; emit result/2 with probability evidence, simulation marker, and batch usage. Markdown and request/1 remain stable.
- Combine facts through `predicates` or `scoped_predicates`; no model-derived authorization. Optional `when` conditions avoid applying confidential-document constraints to known-public material. Unknown facts stay errors.
- Keep trusted evidence and evaluator disclosure authorization in a separate in-process embedding interface. No payload flag, raw header, or CLI metadata file establishes trust. Actual authentication adapters remain future integration work.
- Default to complete declared coverage, no retries/fallback, bounded sequential batches, an overall deadline, and immediate overload errors. Mock runs never request enforcement.
- Core transport code covers both providers in step 3, superseding the earlier M3 placement of direct TypeSafe. The OpenRouter live smoke passed; direct TypeSafe live smoke is optional for v0.1 per owner decision. The $5 total synthetic smoke budget has provider-reported spend of $0.000024696 for one request. OpenRouter was already stored in macOS Keychain; the earlier environment-only credential check was incomplete. See [smoke evidence](smoke-2026-09-27.md).

## Steps 4–5 authorization — 2026-09-27

The owner explicitly waived direct TypeSafe's separate live smoke as a first-release requirement and authorized service/gateway and both Copilot-profile implementation. Retain direct TypeSafe transport and contract tests; OpenRouter remains the live development route. This does not authorize public publication.

Use Starlette + Uvicorn for the small HTTP layer, retaining the existing JSON Schema contracts instead of adding a second model/schema layer. The core stays independent. Optional metadata enrichment is a trusted in-process resolver; default service deployments do not promote client metadata to facts.

## Step 4–5 implementation status

Authenticated service, LiteLLM/Agentgateway adapters and both Copilot command profiles are implemented. Gateway, CLI and VS Code Local host tests pass with synthetic controlled evaluators/downstream effects. After completing Copilot sign-in, Local prompt stop and pre-tool denial were observed with working allow controls. Both Copilot runtimes can bypass checks on host timeouts or disabled hooks. See [integration report](integration-report.md). No new paid API calls, public visibility change or deployment occurred.
