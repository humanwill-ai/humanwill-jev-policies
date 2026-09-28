# Changelog

No public release has been published. Versions below identify private development snapshots; proposed `0.1.0a1` awaits the release, licensing and publication gates.

## 0.1.0.dev3 — current development candidate

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
