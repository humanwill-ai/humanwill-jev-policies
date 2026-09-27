---
kind: policy
id: DEMO-CONTENT
version: "1"
title: Avoid personal insults directed at customers
stages: [prompt, model_request, response]
---

# Rule

Do not request or generate personal insults directed at customers.
Permit factual criticism and quoted insults in incident reports.

## Examples

- Allowed: explain a billing error factually.
- Allowed: summarize a complaint containing quoted insults.
- Violation: compose a reply personally insulting a customer.

No identity or other metadata is required.
