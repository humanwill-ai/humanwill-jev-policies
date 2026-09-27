# Project working instructions

- Begin with research and planning. Do not treat a suggested architecture, schema, integration order, or commercial hypothesis as approved.
- Read `docs/project-brief.md`, `docs/decisions.md`, `docs/release-plan.md`, and `docs/public-release-plan.md` before substantial work. Keep them editable as the owner adds requirements.
- Owner requirements: Markdown policy folders with recursive references and stable policy IDs; LiteLLM, Agentgateway, and Copilot hook connectors for both VS Code Local and Copilot CLI in v0.1; direct Jev and OpenRouter transports, with OpenRouter for development/testing. Keep Copilot runtime contracts explicit.
- Verify changing integration claims against current primary documentation and source. Record review dates and source revisions. Distinguish documented behavior, source inspection, runtime tests, assumptions, and unresolved questions.
- Keep the policy core independent of gateways and the Jev backend. Separate model judgments from deterministic facts and policy decisions, and assessment from actual enforcement.
- State inspected coverage and missing content explicitly. Never silently map unsupported review, missing metadata, or evaluation errors to allow. Failure behavior belongs to both policy and connector.
- Authorization, identity, destinations, and classification require trusted metadata; user assertions are insufficient.
- Metadata itself is optional and independently switchable. Content-only policies must work without it. Missing required facts must never become authorization; resolve dependent-policy configuration explicitly when disabling the feature. Connector authentication is separate.
- Check response and action policies at their governed stages. Prompt checks do not establish response/tool compliance, and post-execution audit does not prevent earlier effects.
- Measure false blocks and missed violations separately. Include legitimate research, authorized work, and direct and indirect prompt injection in evaluation.
- Minimize retained content. Hosted Jev is an external data recipient even if this service is self-hosted.
- Private GitHub creation and the initial push are authorized by the owner. Do not publish publicly, deploy, contact others, or send private datasets/content to other services without authorization.
- Do not commit credentials, raw customer content, or local evaluation artifacts. Distinguish planned features and authoring examples from implemented, tested behavior.

- Local OpenRouter development credential is already stored in macOS Keychain: service `org.humanwill.evals.openrouter`, account `api-key`. See `docs/smoke-2026-09-27.md`. Check that reference before concluding credentials are absent from environment/.env alone; never print or commit the secret. The owner extended the original $5 total cap to step 6 synthetic evaluations. Total recorded spend is $0.006473714 ($0.000024696 smoke plus $0.006449018 development/repeat calls). Reconcile `artifacts/quality/spending.json` and docs/evaluation-development-report.md before more calls; do not reset the ledger.

- Steps 4–5 status: service/gateway/CLI runtime tests implemented, version 0.1.0.dev2. Direct TypeSafe live smoke is optional for v0.1 by owner decision. VS Code Local real-runtime acceptance now passes, including observed host-timeout and disabled-hook bypasses; see docs/integration-report.md and docs/service-and-connectors.md. No paid API calls were made for these integration tests.

- Step 6 initial development comparison is complete; the release quality gate remains open. Policies/dataset/runner are under evals/step6. Approved targets and policy exceptions are in docs/decisions.md; 60 draft labels await human review in docs/step6-label-review.md. No holdout or calibrated enforcement profile exists. Preserve the baseline report and version any future tuning.
