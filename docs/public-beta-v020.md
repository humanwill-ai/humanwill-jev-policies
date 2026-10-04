# HumanWill Jev Policies 0.2 Public Beta candidate

`0.2.0b1` is intended for controlled company pilots. It expands inspected coverage
while retaining monitoring defaults, optional metadata and explicit failure
handling. Beta describes the packaging/integration milestone; it does not certify
policy accuracy, production reliability or enterprise readiness.

**Not yet published.** The public release remains `v0.1.0a1`. Candidate validation is complete and release assets are staged under the
[approved plan](public-beta-v020-plan.md). See the [final record](beta-final-ci-report.md).

## What changes

- Optional [structured function-call inspection](structured-tool-calls.md) checks
  complete non-streaming proposals before release to the client. Agentgateway uses
  an authenticated relay for this path; LiteLLM uses its dedicated profile.
- [LiteLLM MCP](mcp-pre-execution.md) and [Agentgateway ExtMCP](agentgateway-mcp.md)
  check actual tool names/arguments before forwarding to the MCP server.
- Config/5 [conversation instructions](conversation-inspection.md) distinguish
  active requested work from abandoned history, retaining full-payload content
  restrictions. Repeated history is still evaluated; this is not a context cache.
- A [preparation-policy authoring example](../examples/preparation-policy/README.md)
  covers preparing project material for onward disclosure. It needs operator-owned
  approvals when bound as a permission policy; it is not enabled automatically.

Text-only profiles continue to reject structured tools. Streaming remains
unsupported. Tool-proposal inspection does not prove the agent executes the same
arguments; use the execution binding for that boundary. MCP tool results are not
inspected by these pre-execution bindings. Hooks still depend on host configuration
and timeout behavior; **Copilot CLI prompt hooks are assessment-only**.

Compact/grouped policy targets and the latest preparation-policy comparison remain
research evidence. They are not silently added to the runtime. The beta introduces
no approval UI and no production identity, classification or destination resolver.

## Install or upgrade

Use the wheel, source archive, locked requirements and hashes from the **same
candidate**. Until publication these are build/CI artifacts, not a PyPI package or
an available `v0.2.0b1` release download. Build from the reviewed candidate checkout
with `python -m build --no-isolation` after installing `requirements-dev.txt`, or
use its retained CI packages. Verify the source revision and artifact hashes.

Extract the source archive into a fresh directory, then:

```sh
python3 -m venv .venv-beta
.venv-beta/bin/python -m pip install -r requirements.txt
.venv-beta/bin/python -m pip install --no-deps /absolute/path/humanwill_policies-0.2.0b1-py3-none-any.whl
.venv-beta/bin/python -m pip check
.venv-beta/bin/humanwill-policies --version
.venv-beta/bin/humanwill-policies validate /absolute/company-policies \
  --config /absolute/company-policies/config.yaml --json
```

Keep your policy directory, credentials and old environment separate from the
package. Back up the exact policy/service/host configurations. Config/1–5 and
their existing result formats remain supported; no data migration is required.
Config/5 model-request wording changes can change judgments, so compare your own
representative cases in monitor mode before switching enforcement.

Restart the service using the new executable. Install the same wheel in LiteLLM's
environment; for Agentgateway MCP install its optional `agentgateway-mcp` extra
with the pinned dependency versions in that connector guide. Update absolute hook
executable paths when changing environments. Existing text profiles need no opt-in
changes; tool/MCP setup is explicit and must follow its separate guide.

Rollback means stopping the candidate, restoring the previous environment and
matching policy/service/host configuration, and restarting. Remove new tool/MCP
configuration before reverting to a package that does not implement it. Recheck
readiness, an allowed request and a deliberate synthetic denial after either switch.

## Security and assessment limits

Use this as one SDLC security layer. Hosted evaluation sends policy text and
inspected content to Jev/OpenRouter; self-hosting the adapter does not make that
evaluation local. Jev may misclassify, abstain or be affected by prompt injection.
An error fallback of allow can permit violations; block can stop legitimate work.
Review [security considerations](operations.md#security-considerations) and
[private vulnerability reporting](../SECURITY.md).

For **VS Code Local hooks**, verify sign-in, trust, hook settings, executable paths
and the actual runtime. Disabled hooks and host timeouts can bypass enforcement.
Copilot CLI has different contracts. Neither is a universal Copilot interception
point. Gateway and MCP enforcement also depends on routing all governed traffic
through the configured inspection path and protecting configuration from bypass.

The earlier tuned 170-case pack and text-path latency measurements are historical
development evidence, not beta/tool/MCP quality guarantees. Realistic multi-turn
workflow tests still show uncertainty. An independent holdout and the original
statistical acceptance gates remain open; pilot feedback is needed.

## Validation

Local preparation passed: 328 offline tests (six optional gRPC skips), Ruff,
Python 3.11/3.14 wheel/source installation outside checkout, and upgrade/rollback
from the released wheel with unchanged config/5 demo data. A fresh actual VS Code
Local run passed all 14 scenarios, including observed timeout/disabled-hook bypass.
See [local artifact evidence](evidence/beta-local-verification.json) and
[VS Code evidence](evidence/beta-vscode-local.json).

[Live tool/MCP measurement](beta-tools-live-v1-report.md): 48/48 guarded observations
matched expected outcomes, including no execution of denied MCP calls. Paired added
median delay was 438–473 ms for this one-policy, serial synthetic workload. Small
sample/tail and coverage limits are recorded alongside the results.

All seven consolidated GitHub jobs passed at `90cf4629e8b9cd10bd1a9db6155204a6b8d1ec5f`.
Exact packages, hashes, host evidence and the container inventory are retained;
see the [final CI/release packet](beta-final-ci-report.md). Seven attachments and
release prose are staged locally. Publication remains a separate final step.

## Draft release description

HumanWill Jev Policies 0.2 Public Beta lets teams apply their own Markdown policies
at AI gateway and MCP tool-execution boundaries. This release adds optional
non-streaming tool-proposal inspection, LiteLLM and Agentgateway MCP checks, and
clearer handling of active instructions in conversations.

Start in monitor mode with representative company policies. Configure explicit
error handling and validate the supported host profile before enabling enforcement.
Streaming, production approval resolvers and enterprise qualification are outside
this beta. See the linked coverage, security and validation evidence before use.
