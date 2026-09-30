# Current developer preview status

Updated 2026-09-30. Candidate **`0.1.0a1`**, still private and unpublished.
This page supersedes older milestone/count summaries; dated experiment reports
and decision history remain preserved.

## Release-preparation steps requested by the owner

1. **Final full-pack measurement complete.** Three fresh passes of the final
   170-case pack: 509/510 exact event outcomes, one unexpected abstention among
   474 definite observations (0.21%), no wrong definitive event/policy judgments.
   All 36 expected uncertain observations remain uncertain. Ten additional
   individual-policy errors are masked by correct blocks from another policy.
   [Full report](preview-final-v1-report.md),
   [machine-readable summary](../evals/step6/preview-final-v1/results-summary.json).
2. **Local artifact, connector and latency checks completed within available
   environments; fresh host gaps remain explicit.** Both Python versions and
   wheel/source installs pass; actual LiteLLM and CLI host scenarios pass.
   Fresh VS Code Local acceptance now passes all 14 scenarios after fixing an
   overly long test-profile path; the original unsuccessful attempt is preserved. Agentgateway Linux and container runtime retain
   earlier evidence because this machine has neither that Linux runtime nor Docker.
   See [verification detail](preview-verification.md). Live profile latency p95:
   about 1.8 seconds added through LiteLLM and 1 second for hook processes. The
   placeholder response workload produced 37 visible evaluation errors; see
   [latency results and limits](preview-latency-v1-report.md).
3. **Current documentation consolidated.** README, quickstart, operations,
   connector guide, authoring guidance and this index describe the candidate.
   Historical experiments remain dated evidence rather than current setup advice.

No deployment, public visibility change, GitHub push or additional Actions run was
performed for this preparation. API spending remains inside the authorized $5.

## What ships

- Folder-based Markdown policies, recursive explicit includes, stable IDs/versions,
  immutable hashes and offline validation/preview.
- Shared evaluator and deterministic decision logic, OpenRouter/direct Jev
  adapters, authenticated HTTP service, LiteLLM/Agentgateway and Local/CLI hooks.
- Optional trusted metadata and explicit policy binding; monitoring defaults and
  configurable failure handling.
- Config/5 policy-text evaluation and opt-in bounded follow-ups, including
  `q05_stage_aware`. Legacy configuration behavior remains available.
- Offline demo, schemas, synthetic examples, review page, installable wheel/source
  archive, operations and evaluation evidence.

The selected development profile uses gates 0.80/0.70/0.80 and final policy bundle
`evals/step6/policies-sources-v4`. It is not the implicit default. Policy authoring
examples and the content-only metadata-off demo are distinct from the four-policy
research configuration. No production identity/source/destination resolver ships.

## Read next

| Need | Current reference |
| --- | --- |
| Install and exercise locally | [Quickstart](quickstart.md) |
| Write policies and bind trusted facts | [Author guide](policy-authoring.md), [metadata](optional-metadata.md) |
| Understand questions and abstentions | [Config/5](direct-policy-evaluation.md), [bounded follow-up](bounded-policy-followup.md) |
| Connect a gateway or agent | [Connector guide](service-and-connectors.md), [compatibility](compatibility.md) |
| Operate, monitor and roll back | [Operations](operations.md), [security considerations](operations.md#security-considerations) |
| Inspect the 170 approved cases | [Review instructions](case-review.md), [local HTML](case-review.html) |
| Assess measured quality and latency | [Pack report](preview-final-v1-report.md), [latency report](preview-latency-v1-report.md) |
| Review build/install/host evidence | [Candidate verification](preview-verification.md) |
| Understand project and publication decisions | [Brief](project-brief.md), [history](decisions.md), [publication roadmap](public-release-plan.md) |

## Before publishing

Choose the license and maintainer/security contact; complete contribution/security
policies, notices/dependency inventory and public-content/history review; resolve
or explicitly bound the remaining fresh-host evidence; finalize and verify the
publication artifacts; then obtain owner approval for the concrete public release.
The candidate is prepared locally, not uploaded or published. Packaging may need
rebuilding after licensing and other publication material is added.

Independent holdout validation and original statistical enforcement-readiness
criteria remain separate open qualification work. Do not delay all public learning
until enterprise qualification, but describe this release accurately as an
**experimental developer preview** with monitoring defaults, visible limitations
and optional enforcement chosen by the operator. It is not a security guarantee or
an enterprise-ready control, and the tuned pack's rate is not a production forecast.
