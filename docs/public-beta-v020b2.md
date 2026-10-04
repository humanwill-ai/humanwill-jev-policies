# Public Beta 0.2.0b2 — native and Python hook clients

This beta is intended for controlled company pilots. Signing is deferred by
owner decision; the native packages retain the installation limits below.

## What's included

- **Four precompiled C hook clients:** macOS Intel, macOS Apple Silicon,
  Windows x64 and Linux x64. Non-system dependencies are bundled; endpoint users
  do not need Python for the native client. The central policy service remains
  Python and performs the Jev evaluations.
- **Python remains available:** the standalone `humanwill-hook-client` package
  provides `humanwill-hook`; the full service package retains
  `humanwill-policies hook`. Shared protocol code preserves their contracts.
- **Measured lower local overhead:** the exact Intel macOS archive binary takes
  approximately 19 ms median versus 324–328 ms for the legacy Python command,
  saving 306–310 ms per hook. These are synthetic loopback measurements, excluding
  network, Jev and editor scheduling. [Measurement](native-hook-validation.md#latency).

This release retains all features introduced in `0.2.0b1`:

- Optional non-streaming structured tool-call inspection through LiteLLM and
  the Agentgateway relay.
- MCP pre-execution checks through LiteLLM and Agentgateway ExtMCP.
- Active-conversation clarification with full-payload content restrictions.
- The optional disclosure-preparation policy example and numbered architecture
  diagrams, including PNGs rendered in GitHub Markdown.

**TODO: streaming support.** Streaming remains unsupported; see the
[planned work](next-action-plan.md#3-streaming-with-tested-buffering-and-blocking).
Policy thresholds, follow-up selection, monitoring defaults and metadata behavior
are unchanged. Research-only context/target experiments remain research-only.

## Install or upgrade

Use assets from
[v0.2.0b2](https://github.com/humanwill-ai/humanwill-jev-policies/releases/tag/v0.2.0b2)
and verify them with the attached `SHA256SUMS`.

- Native client: follow the [platform installation guide](native-hook-installation.md).
- Full Python service: follow [artifact installation](quickstart.md), using
  `humanwill_policies-0.2.0b2-py3-none-any.whl` and its matching source archive.
- Standalone Python client: follow the [Python guide](hook-client.md), using
  `humanwill_hook_client-0.2.0b2-py3-none-any.whl` and its matching source archive.

The service and standalone Python package report `0.2.0b2`. Native executables
retain the internal build ID `0.1.0.dev2-native`, their original filenames and
the exact hashes tested in CI and host acceptance. The release manifest explicitly
maps these native components to this beta; they were not renamed or rebuilt to
imply a different tested executable.

No automatic host migration occurs. Preserve the runtime/event, service URL,
connector token and failure settings when changing the hook executable. Remove
duplicate HumanWill hook entries. Retain the previous environment and executable
paths for rollback. Config/1–5 and existing request/result formats are preserved.
For gateway setup, use the existing [service guide](service-and-connectors.md).

## Validation and limits

All four native targets passed 108 protocol checks. Intel/ARM macOS also passed
eight actual-service checks; Linux passed those suites on Alpine and Ubuntu.
The exact Intel macOS binary passed 14 actual VS Code Local and six CLI scenarios.
See [native build evidence](native-bundled-builds.md) and
[host acceptance](native-hook-validation.md).

The release attachment `verification.json` records the new Python artifact checks
and privacy review. Earlier gateway/container evidence is linked from the
[0.2.0b1 report](beta-final-ci-report.md), with its original source revision;
it is not relabeled as a new `0.2.0b2` container run. Publication requires successful core and pinned-host workflows; the release
manifest records their exact runs and source revision.

The native packages lack Developer ID notarization and Authenticode signing.
Desktop Copilot acceptance on Apple Silicon, Windows and Linux remains open;
their native protocol tests do not establish every desktop/OS combination.
Host timeouts and disabled hooks can bypass enforcement; CLI submitted-prompt
hooks remain assessment-only. Company controls and synthetic acceptance checks
are still needed around this layer. See [security considerations](operations.md#security-considerations).

No new live Jev accuracy or overall latency claim is made. Hosted evaluation still
sends inspected content and policy text to the evaluator. Independent statistical
qualification, broader pilot experience and production authorization resolvers
remain outside this beta. Private workflow prompts and raw local logs are excluded
from the release source and attachments.
