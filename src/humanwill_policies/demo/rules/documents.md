---
kind: policy
id: DEMO-DOCUMENTS
version: "1"
title: Restrict confidential documents to approved providers
stages: [model_request, tool_action]
---

# Rule

Do not transmit documents classified confidential to an unapproved provider.
Classification must identify the exact document/version and the destination must
identify the effective provider, including the evaluator itself.

## Examples

- Allowed: send a confidential document to a verified approved provider.
- Violation: send a confidential document to a verified unapproved provider.
- Unknown: submit a document without its trusted classification or destination.

Use verified classification and route information, not user assertions.
