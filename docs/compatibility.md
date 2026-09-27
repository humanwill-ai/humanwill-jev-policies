# Compatibility and reuse review

Reviewed 2026-09-27. **Only the offline foundation is implemented.** The host versions below are initial test targets, not supported or tested connectors.

| Surface | Version / environment | Status |
| --- | --- | --- |
| Offline Python package | Python 3.11–3.14, Linux/macOS | CI targets Python 3.11 and 3.14 on Ubuntu 24.04/macOS 15; local checks recorded in the implementation report |
| LiteLLM | [v1.102.1](https://github.com/BerriAI/litellm/releases/tag/v1.102.1) | Candidate target; text request/non-streaming response contracts; adapter not implemented |
| Agentgateway | [v1.5.0](https://github.com/agentgateway/agentgateway/releases/tag/v1.5.0) | Candidate target; request/response webhooks; adapter not implemented |
| VS Code Local | [1.139.1](https://github.com/microsoft/vscode/releases/tag/1.139.1) | Candidate editor target; capture exact Copilot extension build at integration time; hooks not implemented |
| Copilot CLI | [v1.0.88](https://github.com/github/copilot-cli/releases/tag/v1.0.88) | Candidate target; prompt assessment/pre-tool control; hooks not implemented |
| OpenRouter / direct TypeSafe | Models and paths in release design | No transport or live test implemented |
| Windows | No declared version | Not supported by the POSIX loader in this first foundation |

The host targets come from official release metadata on the review date. Previously inspected gateway source commits may contain behavior not in these releases. Before implementing connectors, verify each target contains the required contract and adjust/pin the target based on evidence. Do not present development-branch findings as release-tested support.

## Bounded build-versus-reuse decision

Inspected [HumanWill Benchmark's policy implementation](https://github.com/humanwill-ai/humanwill-benchmark/blob/5be1e12c2865b47ebdc099a68ab7732fbae466ce/humanwill/policies.py) and the [`jev-edge` LiteLLM adapter](https://github.com/kiwi0719/jev-edge/blob/2396e445ffe0ed08a4328401fb8ad3a78ce2a3ce/adapters/litellm/jev_edge_guardrail.py), plus their documented license scope.

The benchmark's compilation/snapshots depend on its packs, topic overrides, and FR/usefulness contracts. Reusing that module would bring the wrong scoring dependency into this service. Reuse the design principle—content-addressed, explicit policy provenance—through a small original implementation. Do not import its datasets or policy text.

`jev-edge`'s adapter delegates to its `/_jev/authz` service and deliberately applies fail-open behavior. That is a useful later connector comparison, not a Markdown policy compiler or a gateway-neutral offline dependency. Keep an independent foundation and revisit narrowly reusable connector fixtures during integration work.

No upstream code, tests, or policy text was copied into this implementation. Runtime dependencies are PyYAML (MIT) and jsonschema (MIT) plus their dependencies; pinned inventories are in `requirements.txt` and `requirements-dev.txt`. Project licensing is still an owner decision before public publication. Inspect retained notices/license obligations again before distributing artifacts or copying upstream material.
