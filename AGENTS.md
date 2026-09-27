# Project working instructions

- Begin with research and planning. Do not treat a suggested architecture, schema, integration order, or commercial hypothesis as approved.
- Read `docs/project-brief.md` and `docs/decisions.md` before substantial work. Keep them editable as the owner adds requirements.
- Verify changing integration claims against current primary documentation and source. Record review dates and source revisions. Distinguish documented behavior, source inspection, runtime tests, assumptions, and unresolved questions.
- Keep the policy core independent of gateways and the Jev backend. Separate model judgments from deterministic facts and policy decisions, and assessment from actual enforcement.
- State inspected coverage and missing content explicitly. Never silently map unsupported review, missing metadata, or evaluation errors to allow. Failure behavior belongs to both policy and connector.
- Authorization, identity, destinations, and classification require trusted metadata; user assertions are insufficient.
- Measure false blocks and missed violations separately. Include legitimate research, authorized work, and direct and indirect prompt injection in evaluation.
- Minimize retained content. Hosted Jev is an external data recipient even if this service is self-hosted.
- Private GitHub creation and the initial push are authorized by the owner. Do not publish publicly, deploy, contact others, or send private datasets/content to other services without authorization.
- Do not commit credentials, raw customer content, or local evaluation artifacts. No product implementation is requested in this initial research stage.
