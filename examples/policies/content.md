---
kind: policy
id: EXAMPLE-CONTENT-001
version: "1"
title: Avoid personal insults directed at customers
stages: [prompt, model_request, response]
---

# Avoid personal insults directed at customers

## Rule

Do not request or generate personal insults directed at customers.

## Exceptions

Criticism of an idea, explanation of a service problem, and quoting abusive
language to document or investigate an incident are permitted. Mentioning an
insult in an incident report is not the same as directing it at a customer.

## Evidence required

The supplied text and conversation context. No user identity, group membership,
document classification, or destination metadata is required.

## Examples

- Allowed: draft a factual explanation of a billing error.
- Allowed: summarize a complaint containing quoted insults.
- Violation: compose a reply that personally insults a customer.
