# Write and test company policies

Policy files express the company's rule. Deployment configuration selects stages, monitoring/enforcement, metadata sources and evaluation behavior. Keep configuration and installed hooks outside agent-writable locations. Markdown alone cannot authenticate identity or enforce a rule.

## A small policy folder

Use `policies.md` as the entry point. References must be explicit `includes`; ordinary Markdown links do not load policies:

```text
company-policies/
  policies.md
  engineering/
    policies.md
    source-disclosure.md
```

Root `policies.md`:

```markdown
---
kind: collection
id: COMPANY
version: "1"
includes: [engineering/policies.md]
---
Company rules.
```

`engineering/policies.md`:

```markdown
---
kind: collection
id: ENGINEERING
version: "1"
includes: [source-disclosure.md]
---
Engineering rules.
```

`engineering/source-disclosure.md`:

```markdown
---
kind: policy
id: ENG-SOURCE-001
version: "1"
title: Protect project source and documentation
stages: [prompt, model_request, tool_action, response]
---
Use of project source code, code fragments, designs and related documentation
within the company-approved coding model is permitted for coding work.
Do not upload or share those materials onward unless the actual destination
and operation are explicitly approved. An unknown or unlisted onward target
is unapproved. Already-public project material is not exempt.
```

This illustrates authoring, not a production destination verifier. Its approved-model and onward-operation facts must come from trusted deployment configuration or an authenticated resolver, never a prompt's claim. The current evaluation fixture authority is synthetic and is not a resolver for arbitrary production destinations. Use the [approved boundary](software-policy-boundary-tests.md) when designing corresponding labels and stage checks.

Each rule has one stable ID. Increment its quoted version when meaning changes; also version the collection for a reviewed update. Keep permissions and exceptions within the applicable rule—file order does not create priority or overrides. The source and bundle hashes also change on textual edits and provide exact provenance. They are fingerprints, not signatures.

## Bind every policy explicitly

Start new semantic rules in monitoring mode:

```yaml
format: humanwill.config/5
metadata:
  enabled: false
policies:
  ENG-SOURCE-001:
    enabled: true
    mode: monitor
    strategy: semantic
```

This minimal binding validates syntax but cannot establish trusted destination approval. For the software policy above, design the scoped predicates and authority integration before claiming it implements the full rule. See [config/3](decision-v3.md) and [metadata integration](optional-metadata.md). Use content-only rules that need no authorization facts when metadata is disabled. Explicitly disable dependent rules or retain them in monitor mode with visible uncertainty; disabling metadata never grants permission. The normal `serve` CLI has no enterprise identity/directory/destination resolver. Embedding `create_app` with an authenticated async evidence resolver is the current extension point.

Validate both files together:

```sh
humanwill-policies validate company-policies --config policies.yaml --json
humanwill-policies preview company-policies --config policies.yaml --json
```

Every loaded policy needs a binding, including disabled policies. Unknown fields, duplicate IDs, cycles, links escaping the root, symlinks and unsupported settings fail explicitly. Use [schemas and format limits](contracts.md) for exact constraints.

## Make the rule measurable

For each governed stage, write legitimate cases, violations, approved exceptions, and genuinely missing evidence. For software sharing, ordinary code review through the configured approved coding model is legitimate; onward upload to an unknown destination is a violation; a failed trusted lookup or unavailable relevant content is an evaluation error. Give expected semantic scope and trusted facts separate labels.

Include near-neighbors: printing a dangerous command for discussion differs from executing it; a supplied statement of approval differs from authenticated permission. Retain adversarial evaluator tests without adding the removed standalone instruction-integrity policy. Group related scenario variants before splitting development and held-out data. Human reviewers should adjudicate ambiguous labels before model evaluation.

Measure false blocks and missed violations separately, report indeterminate/errors and coverage gaps, and freeze policy/configuration/model/threshold versions before held-out evaluation. Start in monitor mode; a syntactically valid `evaluation_profile` does not prove calibration. Enable enforcement only for a profile with suitable measured evidence and explicit failure behavior. Unsupported review actions are rejected because no approval workflow exists.

Config/4 supports [three global outcome thresholds](outcome-thresholds.md), shared
across policies. It rejects legacy per-policy confidence settings; failure handling
remains separate. All three default to 0.80 until deliberately configured.

A prompt check covers the submitted surface, not later files, retrieval, tool results or output. Enable response and pre-tool checks where the rule governs those stages; see the [connector coverage table](compatibility.md) and [operations](operations.md).

For new policy-text evaluation, use [config/5 and the shared template](direct-policy-evaluation.md). The actual Markdown body is sent to Jev; no separately authored `scope` question is required. Trusted-data bindings remain explicit. Preview shows the generated questions.
