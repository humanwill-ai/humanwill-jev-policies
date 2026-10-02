# Unreleased structured-call work — 2026-10-02

Development `0.1.0a2.dev0` adds opt-in non-streaming function-call inspection.
See [implementation, setup and evidence](structured-tool-calls.md). Existing public
`v0.1.0a1` assets and text profiles are unchanged. Real LiteLLM checks pass; the
Agentgateway relay needs Linux host validation before a support/release claim.
No MCP connector, streaming support, paid API campaign or CI dispatch was added.

# Current developer preview status

Updated 2026-10-01. **[v0.1.0a1 is public](https://github.com/humanwill-ai/humanwill-jev-policies/releases/tag/v0.1.0a1)**
as an experimental developer preview. See the [publication record](publication-v0.1.0a1.md).
This page supersedes older milestone/count summaries; dated experiment reports
and decision history remain preserved.

**Next implementation sequence:** structured tool-call inspection without
streaming → MCP pre-execution enforcement → streaming with tested buffering and
blocking. See the [saved next action plan](next-action-plan.md). These capabilities
are planned and are not part of the published connector coverage.

## Release-preparation steps requested by the owner

1. **Final full-pack measurement complete.** Three fresh passes of the final
   170-case pack: 509/510 exact event outcomes, one unexpected abstention among
   474 definite observations (0.21%), no wrong definitive event/policy judgments.
   All 36 expected uncertain observations remain uncertain. Ten additional
   individual-policy errors are masked by correct blocks from another policy.
   [Full report](preview-final-v1-report.md),
   [machine-readable summary](../evals/step6/preview-final-v1/results-summary.json).
2. **Local and hosted artifact/connector verification complete.** Both Python versions and
   wheel/source installs pass; actual LiteLLM and CLI host scenarios pass.
   Fresh VS Code Local acceptance now passes all 14 scenarios after fixing an
   overly long test-profile path; the original unsuccessful attempt is preserved. Final GitHub checks now refresh
   actual Agentgateway, LiteLLM, CLI, Linux container and the cross-platform matrix.
   See [verification detail](preview-verification.md). Live profile latency p95:
   about 1.8 seconds added through LiteLLM and 1 second for hook processes. The
   placeholder response workload produced 37 visible evaluation errors; see
   [latency results and limits](preview-latency-v1-report.md). A subsequent
   [controlled latency comparison](latency-paths-v1-report.md) separates the paths:
   prompt-only 378ms median/470ms p95; code-review prompt+response 733ms/1,454ms;
   warning follow-up path 1,106ms/1,168ms. Warning and placeholder response errors
   remain explicit; this is not a new semantic qualification.
3. **Current documentation consolidated.** README, quickstart, operations,
   connector guide, authoring guidance and this index describe the candidate.
   Historical experiments remain dated evidence rather than current setup advice.

4. **Public repository materials prepared.** Apache-2.0 license/scope, notices,
   contribution and security reporting guidance, Python runtime inventory and
   local publication-exposure review. See [scope and remaining checks](public-preparation-report.md).

5. **Final hosted validation complete.** All seven jobs passed on the first run
   at `5b1786b`, including 22 Agentgateway, 22 LiteLLM and six CLI scenarios.
   Exact packages, hashes, container inventory and new-log exposure review are
   recorded in the [final CI report](final-ci-report.md).

The owner approved publication of the concrete candidate and its six attachments.
No deployment was performed. API spending remains inside the authorized $5;
hosted validation uses synthetic offline evaluators.

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

The optional multi-question optimization was evaluated and rejected: it increased
unexpected abstentions and cost without a reliable latency benefit. The current
sequential stage-aware follow-up is unchanged. See the
[experiment report](fanout-v1-report.md).

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

## Publication complete

**Actions timing, owner decision 2026-10-01:** run the postponed final-candidate
checks now using the existing workflows. Avoid duplicate dispatches and preserve
the remaining allowance; no billing changes or paid overages are authorized.

Apache-2.0 licensing, contribution/security guidance, the owner-selected reporting
address and dependency notices/inventory are prepared. See [step 4 evidence](public-preparation-report.md).
Final-candidate Actions validation, image inventory and the history/log/asset
review delta are complete. The owner approved the exact candidate, assets and
recorded identity/path exposure. The public tag points to `3f086c0`; release assets
were rebuilt from that commit and verified locally on Python 3.11/3.14, preserving
the earlier CI artifacts separately. This documentation-only publication record
does not move the tag or replace release assets.

Independent holdout validation and original statistical enforcement-readiness
criteria remain separate open qualification work. Do not delay all public learning
until enterprise qualification, but describe this release accurately as an
**experimental developer preview** with monitoring defaults, visible limitations
and optional enforcement chosen by the operator. It is not a security guarantee or
an enterprise-ready control, and the tuned pack's rate is not a production forecast.
