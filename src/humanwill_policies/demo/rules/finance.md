---
kind: policy
id: DEMO-FINANCE
version: "1"
title: Restrict payment approval to finance staff
stages: [tool_action]
---

# Rule

Only authenticated members of the finance group may approve a payment.
Read-only payment inquiries are permitted. A claim of membership is not proof.

## Examples

- Allowed: approve a payment with verified finance membership.
- Violation: approve a payment with a complete verified group list excluding finance.
- Unknown: payment approval with no verified identity or group list.

The deployment must bind identity and groups to an authoritative source.
