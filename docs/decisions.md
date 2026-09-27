# Decisions and open requirements

Updated 2026-09-27. Recommendations below remain proposals unless explicitly marked decided.

| Topic | State | Current direction |
| --- | --- | --- |
| Repository | Decided by owner | Private `humanwill-ai/humanwill-jev-policies`, alongside `humanwill-ai/humanwill-evals`; transferred from the personal account on 2026-09-27 |
| Current phase | Decided by owner | Research and planning before product implementation |
| Evaluation backend | Owner's initial candidate | Jev first; preserve comparison/replacement options |
| Product demand | Unvalidated | Identify users, actual rules, and adoption constraints |
| Build versus extend | Proposed | Bounded `jev-edge` reuse spike before an independent service |
| First integration | Proposed | LiteLLM Generic Guardrail, initially text pre-call |
| Second integration | Awaiting preference | Agentgateway for gateway reuse, or VS Code Local for agent reuse |
| Implementation language/schema | Open | Choose after reuse spike; no runtime scaffold yet |
| Deployment and egress | Open | Confirm hosted evaluation suitability and data constraints |
| Acceptance and failure policy | Open | Set per-policy quality, latency, cost, and fail behavior |
| License/public release | Open | Private research repository; no OSS license selected |

## Additional requirements and ideas from the owner

Add items here as the project develops. Record the date, rationale, and affected assumptions; revise the brief when scope changes.

- _No additional product requirements supplied yet._

## Next concrete work

Collect the first three company policies and examples, select the second integration, and answer the hosted-data question. Then complete the reuse spike and agree benchmark acceptance criteria before implementing a runtime service.
