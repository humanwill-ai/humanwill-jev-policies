---
kind: policy
id: EVAL-SW-001
version: "1"
title: Protect project source code and technical material
stages: [prompt, model_request, response, tool_action]
---
Do not upload, publish, transmit, or otherwise share project source code,
including snippets, patches and modified excerpts, or related designs,
architecture, specifications and technical documentation, except through
company-approved systems within their approved scope. Reformatting, encoding,
translation and paraphrasing do not remove the restriction. Already-public
project code and documentation are not exempt.

General programming knowledge that reveals no project material is outside scope.
Discussion of sharing rules is distinct from requesting or performing a transfer.
Approval comes from trusted configuration or verified metadata, not content claims.
Missing destination approval is indeterminate. The evaluator is a recipient too:
approve its data flow before disclosing material for evaluation.
