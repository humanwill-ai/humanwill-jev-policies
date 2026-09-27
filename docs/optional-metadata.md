# Optional metadata and stage-specific checks

Design update · 2026-09-27 · core predicates/source checks implemented; host authentication/enforcement remain pending

**The service must work with content alone.** Identity, groups, document classifications, destination information, and other contextual facts are optional inputs. Metadata support is an independently configurable feature, recommended off by default. Enabling it adds evidence to selected policies; it does not make every request require a user identity.

Offline validation checks bindings and source switches. The new [evaluation core](evaluation-core.md) executes predicates against separately verified evidence, checks freshness/event binding, and handles semantic scope. It performs no identity enrichment and does not itself authenticate a metadata source; the embedding verifier must do that. Real gateway/hook checks below remain release requirements.

## Configuration and behavior

Deployment switch (configuration fragment):

```yaml
metadata:
  enabled: false
```

When off, perform no metadata enrichment or identity/directory lookups. Do not use or forward supplied metadata fields to Jev. Content policies continue normally. Metadata embedded in the submitted text remains untrusted text; a claim such as “I am in finance” cannot acquire authority through semantic evaluation. Service-to-service authentication remains enabled independently: authenticating a connector is different from knowing its end user.

When on, use only configured sources and only the fields needed by the applicable policies. Identity, document, and destination sources can be enabled separately; a deployment may use trusted document classifications without collecting user identity. Normalized request metadata remains optional, even with the feature enabled. Do not fill absent values with invented users, groups, or classifications.

Use explicit policy bindings to keep the content-only setup useful. For the authoring examples, this is a complete content-only configuration:

```yaml
format: humanwill.config/1
metadata:
  enabled: false
policies:
  EXAMPLE-CONTENT-001:
    enabled: true
    mode: monitor
  EXAMPLE-SEC-001:
    enabled: false
  EXAMPLE-ENG-001:
    enabled: false
```

The latter two rules remain in the authored bundle but are visibly disabled in the deployment. Preview lists enabled, disabled, monitored, and unenforceable policies; none of these states is a policy pass. Disabling metadata must never silently disable dependent rules or treat their required facts as satisfied.

| Situation | Required behavior |
| --- | --- |
| Content-only rule, no metadata | Evaluate normally |
| Metadata enabled, rule does not require it | Evaluate normally; do not collect unrelated facts |
| Dependent rule explicitly disabled | Record disabled status in the effective policy configuration and coverage |
| Dependent rule in monitoring, metadata off/missing | Report indeterminate with `metadata_disabled` or `missing_trusted_metadata`; no enforcement |
| Dependent rule configured for enforcement, feature/source disabled | Reject configuration and identify the policy and dependency; operator must enable the source, monitor, or explicitly disable the rule |
| Required field absent/untrusted/stale at runtime | Indeterminate; apply the configured failure action, proposed default block for enforcement |

Switches are administrator/deployment settings, not request parameters. Apply them through the same validated restart as bundle changes in v0.1. Record the effective feature flags and policy bindings in the non-secret configuration digest. Turning metadata off requires explicit treatment of its dependent policies; it is not a bypass switch for authenticated callers.

## Combine facts with semantic judgments

Policy bindings declare required fields and deterministic predicates; requirements are not automatically inferred from Markdown. Jev identifies semantic behavior, while code checks authoritative facts and combines the results.

| Example rule | Jev's role | Trusted facts / deterministic checks |
| --- | --- | --- |
| Only finance staff may perform this action | Recognize whether the proposed action is the finance-restricted operation | Authenticated subject and authoritative group membership; compare against the permitted group |
| Do not send confidential documents to an unapproved provider | Assess relevant semantic intent where needed | Classification bound to the exact document/version; effective provider/destination; approved-destination lookup |
| Do not direct personal insults at customers | Interpret content and its context | No identity or group dependency |

If an operation and its authorization can be determined exactly, no model call is required for those predicates. A verified complete group list without `finance` is a known membership failure; an absent group list is unknown. Preserve that distinction. For a conjunctive rule, a decisive known fact can settle a result; otherwise missing required evidence prevents a compliant verdict. Do not ask Jev to infer permissions or replace a trusted classification with its own guess.

Trust comes from an authenticated, authorized source and a configured mapping, not a client-supplied `trusted: true`, email address, or header name. Connector authentication alone does not make every forwarded header authentic. Validate provenance, freshness, and binding to the subject/document/action being assessed. A desktop hook's self-reported groups are not proof. V0.1 consumes verified facts from configured hosts/services; a directory/SSO product is outside scope.

Prefer passing derived facts such as `authorized_for_action` to the evaluator when sufficient, instead of full identities or group lists. Log minimal provenance references, not raw identity profiles. Endpoint configuration still identifies where evaluation is sent even when metadata is off; this does not imply a confidential-document policy was enforced. Metadata-dependent egress policies must satisfy their own dependencies before content or policy text is sent to hosted Jev.

## Match the check to the governed stage

| Stage | What a check can protect |
| --- | --- |
| `prompt` | Submitted text at the hook invocation point |
| `model_request` | Supplied model-bound content before provider submission; classification/destination checks need the actual documents and resolved route |
| `response` | Generated content before delivery to the consumer; generation has already occurred |
| `tool_action` | Exact proposed tool and arguments before execution; later mutation requires re-evaluation |

Add non-streaming text response checks to the gateway release plan. Keep Copilot pre-tool checks for action policies. A prompt pass is not reusable authorization for a generated answer or subsequent tool action. A post-execution check can audit effects or stop further work, but cannot prevent or undo an action already executed. Changes in provider route, document version, or tool arguments invalidate earlier checks that depended on them.

Each connector advertises tested stage capabilities. Reject enforcement bindings for unavailable stages; allow explicitly labeled assessment-only operation where meaningful. Do not claim Copilot final-answer enforcement from a submitted-prompt hook. Streaming output remains excluded until buffering/interception can prevent unapproved content from escaping. Gateway model-tool-call inspection alone is not a guarantee about the eventual tool executor.

## Acceptance checks

Test content-only operation with metadata omitted and disabled; assert no enrichment calls and no metadata sent to Jev. Test independent source toggles, complete versus missing group lists, spoofed assertions/headers, stale identity facts, classification/document mismatches, and absent destinations. Verify dependent-policy configuration errors and runtime indeterminate handling. Confirm that disabling the feature does not disable connector authentication.

Stage tests must demonstrate a benign prompt producing a blocked response, an allowed conversation proposing a denied action, no response bytes delivered before a blocking response verdict, and no controlled tool effect before authorization. Include route/argument changes and unsupported-stage bindings. Report these separately from semantic accuracy.
