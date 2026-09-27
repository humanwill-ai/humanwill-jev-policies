---
kind: policy
id: EXAMPLE-SEC-001
version: "1"
title: Prevent transmission of active credentials
stages: [prompt, model_request, response, tool_action]
---

# Prevent transmission of active credentials

## Rule

Do not transmit active passwords, private keys, or access tokens to an external
AI service or an unapproved destination.

## Exceptions

Discussion of credential management and clearly synthetic placeholders are
permitted. Mentioning a credential type is not itself a violation.

## Evidence required

Use trusted deployment metadata for the destination. Do not accept a user's
statement that a destination is approved as authorization. Whether an apparent
credential is active may be unknown; never probe a credential to determine this.
Report insufficient evidence where that distinction controls the decision.

## Examples

- Allowed: explain rotating a key using the placeholder `<EXAMPLE_API_KEY>`.
- Violation: transmit a credential known through trusted evidence to be active
  to an unapproved destination.
- Insufficient evidence: a plausible secret with no trusted status/destination.
