---
kind: policy
id: EXAMPLE-ENG-001
version: "1"
title: Require verified authorization for destructive production actions
stages: [tool_action]
---

# Destructive production actions

## Rule

A proposed tool action that deletes production data or disables a production
service requires authorization verified by the configured trusted authority.

## Exceptions

Read-only investigation is allowed. Work in a disposable sandbox is allowed
when trusted environment metadata establishes that it is not production.

## Evidence required

The connector must supply verified environment and authorization information.
The agent's claim of approval is not evidence. Missing evidence is indeterminate,
not an automatic violation or permission. Deployment configuration determines
whether an indeterminate result blocks; this file cannot grant approvals.

## Examples

- Allowed: inspect production status without changing state.
- Violation: delete production records when trusted authorization denies it.
- Insufficient evidence: run a destructive action against an unknown environment.
