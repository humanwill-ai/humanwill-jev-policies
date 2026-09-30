# Compatibility and reuse review

Host targets originally reviewed 2026-09-27. See [current candidate verification](preview-verification.md) for refreshed checks versus retained historical host evidence. **Do not infer that every host was rerun on the current artifact.** Support is bounded to the configurations in the [connector guide](service-and-connectors.md) and the [integration evidence](integration-report.md). Local evidence uses macOS x86_64 and a signed-in isolated profile.

| Surface | Version / environment | Status |
| --- | --- | --- |
| Offline Python package | Python 3.11–3.14, Linux/macOS | CI targets Python 3.11 and 3.14 on Ubuntu 24.04/macOS 15; local checks recorded in the implementation report |
| LiteLLM | [v1.102.1](https://github.com/BerriAI/litellm/releases/tag/v1.102.1) | Real macOS x86_64 and Ubuntu 24.04 host tests pass for text request/non-streaming response profile |
| Agentgateway | [v1.5.0](https://github.com/agentgateway/agentgateway/releases/tag/v1.5.0) | Real Linux amd64 host tests pass for text request/non-streaming response profile |
| VS Code Local | [1.139.1](https://github.com/microsoft/vscode/releases/tag/1.139.1) | Bundled Copilot Chat 0.67.0; fresh `0.1.0a1` installed-wheel macOS x86_64 Local acceptance passes 14 scenarios; host-timeout and disabled-hook bypass observed |
| Copilot CLI | [v1.0.88](https://github.com/github/copilot-cli/releases/tag/v1.0.88) | Real macOS x86_64 and Ubuntu 24.04 host tests pass for prompt assessment/tool deny; timeout/disabled-hook bypass observed |
| OpenRouter / direct TypeSafe | Models and paths in release design | Both adapters have synthetic HTTP tests; [OpenRouter live smoke passed](smoke-2026-09-27.md), direct TypeSafe live smoke optional for v0.1 |
| Windows | No declared version | Not supported by the POSIX loader in this first foundation |

The host targets come from official release metadata on the review date. Previously inspected gateway source commits may contain behavior not in these releases. Before implementing connectors, verify each target contains the required contract and adjust/pin the target based on evidence. Do not present development-branch findings as release-tested support.

## Bounded build-versus-reuse decision

Inspected [HumanWill Benchmark's policy implementation](https://github.com/humanwill-ai/humanwill-benchmark/blob/5be1e12c2865b47ebdc099a68ab7732fbae466ce/humanwill/policies.py) and the [`jev-edge` LiteLLM adapter](https://github.com/kiwi0719/jev-edge/blob/2396e445ffe0ed08a4328401fb8ad3a78ce2a3ce/adapters/litellm/jev_edge_guardrail.py), plus their documented license scope.

The benchmark's compilation/snapshots depend on its packs, topic overrides, and FR/usefulness contracts. Reusing that module would bring the wrong scoring dependency into this service. Reuse the design principle—content-addressed, explicit policy provenance—through a small original implementation. Do not import its datasets or policy text.

`jev-edge`'s adapter delegates to its `/_jev/authz` service and deliberately applies fail-open behavior. That is a useful later connector comparison, not a Markdown policy compiler or a gateway-neutral offline dependency. Keep an independent foundation and revisit narrowly reusable connector fixtures during integration work.

No upstream code, tests, or policy text was copied into this implementation. Runtime dependencies are PyYAML (MIT), jsonschema (MIT), HTTPX (BSD-3-Clause), Starlette (BSD-3-Clause), and Uvicorn (BSD-3-Clause) plus their dependencies; pinned inventories are in `requirements.txt` and `requirements-dev.txt`. Original project licensing is prepared as Apache-2.0; see [scope](../LICENSING.md) and [dependency notices](../THIRD_PARTY_NOTICES.md). Inspect retained notices/license obligations again before distributing artifacts or copying upstream material.
