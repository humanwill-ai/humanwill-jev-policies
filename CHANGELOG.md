# Changelog

## 0.1.0a1 — unpublished developer preview candidate

- Company-authored Markdown bundles, optional trusted metadata, Jev transports,
  authenticated service and LiteLLM/Agentgateway/Local/CLI connector profiles.
- Config/5 policy-text evaluation, global outcome thresholds, optional bounded
  Q05/Q04 and stage-aware follow-ups with result/4 audit/usage fields.
- Final 170-case development-pack measurement and refreshed installation evidence.
- Monitoring examples; no calibrated enforcement or independent holdout claim.
- See [current status](docs/preview-status.md) for remaining publication gates.

No public release has been published. Versions below identify private development snapshots; proposed `0.1.0a1` awaits the release, licensing and publication gates.

## 0.1.0.dev3 — historical development series

- Adds optional `policy_assessment: q05_stage_aware`: Q05 first, then at most one tool-specific scope follow-up for `tool_action` or Q04 for other stages. Preserves existing profiles, gates, full policy batches and trusted checks. Includes stage-specific preview and packaged demo configuration; update strict clients with the service.

- Adds opt-in `policy_assessment: q05_q04` to config/5: measured scope wording and one bounded full-batch follow-up, with unchanged confidence gates, trusted checks and error fallback. Result/4 records normalized follow-up evidence and both call usage records. Existing configurations keep their behavior; upgrade service and strict clients together. See [runtime contract](docs/bounded-policy-followup.md).

- Adds opt-in config/5: actual Markdown policy text plus a shared evaluator template, explicit trusted-data bindings, question preview and result/4. Legacy formats remain unchanged. See [behavior and migration](docs/direct-policy-evaluation.md); live quality validation remains pending.

- Adds opt-in config/4 with three global outcome confidence thresholds, preserving config/1–3 behavior and result/3 compatibility. Defaults remain 0.80; asymmetric values are configurable, not calibrated. See [migration and semantics](docs/outcome-thresholds.md).
- Adds opt-in config/3 and result/3 with per-stage scopes and trusted-predicate short circuiting; retains config/2 behavior.
- Clarifies approved coding-model use versus onward disclosure. The current synthetic evaluation bundle has software disclosure, production action and classified-document policies. The standalone instruction-integrity policy was removed after its development comparison.
- Adds exact wheel/source installation verification, installed service startup/rollback checks, a local container recipe and installation, policy-authoring and operations guides.
- Jev development results are documented separately from runtime connector evidence. Human-reviewed independent quality and performance release gates remain open; examples default to monitor mode.

Upgrade service and hook clients together for config/3. Preserve the previous artifact and matching policy/configuration for [rollback](docs/operations.md). Runtime gateway tests and interactive Copilot evidence retain their exact [pinned versions](docs/compatibility.md); installing a newer package does not revalidate every host version.

## 0.1.0.dev2

- Authenticated HTTP service, LiteLLM/Agentgateway text profiles and separate Copilot Local/CLI hook clients.
- Real pinned gateway and Copilot runtime tests, including observed timeout and disabled-hook bypasses.
- Minimal-content audit logs, limits, deadlines and explicit connector failure behavior.

## Earlier private foundation

- Markdown collections and policy IDs, immutable bundle provenance, offline validation/preview/demo and schemas.
- Evaluator abstraction, deterministic decisions, optional trusted facts, strict Jev adapters for OpenRouter and direct TypeSafe, and synthetic transport tests.
- OpenRouter live smoke passed. A separate direct TypeSafe live smoke remains optional for the first release.
