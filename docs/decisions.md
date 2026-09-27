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
| Live budget / quality targets | Open | Agree before paid runs / customer enforcement respectively |
| Public release objective | Decided by owner | Plan a first release suitable for public GitHub publication; visibility remains private during preparation |
| Release label / artifacts | Proposed | `v0.1.0a1` public preview, source/wheel/checksums and evidence; see public-release roadmap |
| Project license | Awaiting owner choice | Proposed Apache-2.0 for original code/docs/examples; preserve licenses of reused material |

## Requirement update: 2026-09-27

The owner expanded the initial two-integration suggestion to three mandatory connector families, specified Markdown policy folders and IDs, and selected OpenRouter for development. These supersede the initial choice between Agentgateway and VS Code as a second integration. The enterprise focus and relationship to HumanWill Benchmark are now explicit.

Follow-up: metadata must be optional and switchable, including user/group information. Metadata-dependent policies still need authoritative evidence; turning the feature off cannot establish authorization. The owner also requires checks at the stages governed by a policy. The proposed release now includes non-streaming gateway response checks, superseding the earlier response deferral; unavailable stages remain explicit limitations. See [metadata and stage design](optional-metadata.md).

Publication planning: the owner requested steps toward a confident public first release. The [public-release roadmap](public-release-plan.md) adds real-runtime evidence, semantic evaluation, packaging, licensing, and a public-content review. Private alpha validation becomes preparation for the proposed public preview. Publication itself awaits a completed, reviewable candidate and owner go-ahead.

## Next concrete work

Steps 1–2 of the [public-release roadmap](public-release-plan.md) are implemented: authoring/configuration contracts, package/CLI, loader, IDs/digests, preview, tests, and CI. See the [foundation report](foundation-report.md). The roadmap now uses one-based numbering to match the requested steps; these were previously rows 0–1. No model calls, service, or connectors were implemented in this increment.

Next: Step 3 / M2, beginning with mock evaluation and deterministic decisions. Establish how semantic applicability and metadata predicates combine before enabling the provider transports; do not interpret a valid evaluation-profile configuration as measured accuracy.

Foundation decisions: package/CLI `humanwill-policies`, import `humanwill_policies`, version `0.1.0.dev0`; explicit include lists and one policy per file; reject all symlinks under the root; bounded restricted YAML; exact source and normalized configuration hashes; monitoring defaults and required explicit policy bindings. Freeze authoring format v1 and candidate request/result fixtures with versioned changes. Candidate host versions are recorded but untested; final VS Code Copilot extension build remains an integration-stage choice.

## Additional requirements and ideas

Append dated requirements here and update the plan when they change scope.
