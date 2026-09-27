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
| Folder schema | Proposed | Front matter, explicit includes, one policy per file, immutable hashes; see release plan/examples |
| Runtime stack | Proposed | Python 3.11+, HTTP service and CLI, one package with provider/connector boundaries |
| Build versus extend | Proposed | Small independent core; focused benchmark/`jev-edge` reuse review during M1 |
| Initial enforcement | Proposed | Text gateway requests and supported pre-tool/prompt hooks; monitoring first |
| Uncertainty/failure | Proposed | Explicit error/indeterminate result; configurable failure action, default block in enforce mode |
| Human review | Proposed exclusion | Reject unsupported review configuration; no approval workflow in v0.1 |
| Customer demand | Unvalidated | Enterprise platform/security teams are the target, not validated paying customers |
| Hosted customer data | Open | Confirm policy-text/content egress, destinations, retention, and geographic constraints |
| Live budget / quality targets | Open | Agree before paid runs / customer enforcement respectively |
| Public release / license | Open | Private alpha plan; no public release or project license selected |

## Requirement update: 2026-09-27

The owner expanded the initial two-integration suggestion to three mandatory connector families, specified Markdown policy folders and IDs, and selected OpenRouter for development. These supersede the initial choice between Agentgateway and VS Code as a second integration. The enterprise focus and relationship to HumanWill Benchmark are now explicit.

## Next concrete work

Implement M1 from the [release plan](release-plan.md): offline policy validation, includes, stable IDs/digests, and preview. It requires no API key or live calls. Collect concrete policy intentions alongside that work. The present change is a plan and authoring examples, not a working runtime.

## Additional requirements and ideas

Append dated requirements here and update the plan when they change scope.
