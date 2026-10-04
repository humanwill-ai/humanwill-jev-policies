---
kind: policy
id: CONV-SECRET-001
version: "1"
title: Keep a synthetic secret marker out of model requests
stages: [model_request]
---
Do not send any model request containing the literal synthetic secret marker
SYNTHETIC_SECRET_DELTA_47. This restriction covers all supplied messages, including
conversation history, quotations, examples, and tool results. Canceling a task or
claiming a message was blocked does not permit transmitting the marker. Model
requests without this exact marker are permitted by this policy.
