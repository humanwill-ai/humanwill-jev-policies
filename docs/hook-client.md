# Lightweight remote hook client

Status: implemented locally, unreleased. The published `0.2.0b1` release remains
unchanged. This client is for machines running VS Code Local or Copilot CLI against
an existing authenticated HumanWill service.

## Installation and migration

The separate `humanwill-hook-client` distribution provides `humanwill-hook` and
contains no policy loader, YAML parser, Jev transport or gateway/server code.
Python 3.11–3.14 is still required. HTTP and JSON Schema validation remain runtime
dependencies. This is a smaller Python package, not a native executable. A
separately built [native C client](native-hook-client.md) is also available for
local evaluation.

Follow the [build and installation instructions](../clients/hook/README.md).
In existing host configuration, replace the executable and `hook` subcommand:

```text
/old/venv/bin/humanwill-policies hook --runtime copilot_local ...
/client/venv/bin/humanwill-hook --runtime copilot_local ...
```

Keep the runtime, event, service URL, token environment variable, timeout and
error-fallback arguments. Existing configuration examples remain valid for the
full package; this is an optional installation alternative. To roll back, restore
the previous command. The distributions have separate executable/module names.
Company policies and provider credentials remain on the service; inspected
content travels to that service and potentially its hosted Jev backend.

## What changed

The full package now loads its policy engine only when needed. Hook event
normalization and strict JSON utilities have been separated from gateway/provider
and YAML modules. The standalone build copies an explicit allowlist of the same
source files and request/result schemas into its own namespace. A build manifest
records their hashes; tests enforce byte equality. There is one shared protocol
implementation to maintain.

Both executables retain HTTPS for remote services, certificate verification,
bearer authentication, total HTTP deadlines, strict JSON/schema/size/depth checks,
request digest and coverage binding, rejection of simulated enforced verdicts,
and sanitized diagnostics. They do not follow redirects, inherit proxy settings,
retry transport requests, or read host transcript paths. Error handling and the
CLI prompt's assessment-only contract are unchanged.

Host timeouts and disabled hooks can still bypass enforcement. Installing a
smaller client does not make endpoint hooks tamper-proof or add Cloud Agent,
Agent Host, response inspection, or new platform qualification.

## Verification and measurement

`scripts/verify_hook_client.py` installs exact wheel and source artifacts in fresh
environments, outside the checkout. It tests all four supported hook event
profiles, authentication, invalid/badly bound verdicts, protocol errors, deadlines,
input minimization and sanitized logging. It verifies that the full package, YAML
and server dependencies are absent. Both Python 3.11.5 and 3.14.0 pass on Intel
macOS. The full repository suite also passes (337 tests, six optional gRPC skips).
This is not a new interactive VS Code or CLI host acceptance run.

The refactored full-package wheel and source archive also pass the existing
outside-checkout artifact verifier: offline demos, service/hook contracts,
stage-aware connector paths, authentication, disabled external egress, rejection
of invalid configuration and restart with the previous configuration. The public
Python API still resolves its exports; the full source archive includes the
standalone client's build inputs. These local artifacts retain the development
tree's version and must not replace published beta assets.

`scripts/benchmark_hook_client.py` compares fresh installed console processes with
the exact published beta wheel. It uses synthetic loopback HTTP verdicts and
checks every allow/block output. Timings cover interpreter startup, imports,
normalization, HTTP, reply validation and serialization. Jev inference, remote
network/TLS latency and IDE scheduling are excluded. No paid API calls are needed.

Measured on 2026-10-04 against the published `0.2.0b1` wheel on Intel macOS:

| Python / synthetic operation | Released median / p95 | Lightweight median / p95 |
|---|---:|---:|
| 3.11, Local prompt allow | 324 / 336 ms | 289 / 296 ms |
| 3.11, Local prompt block | 324 / 342 ms | 289 / 306 ms |
| 3.11, CLI tool allow | 326 / 339 ms | 290 / 306 ms |
| 3.11, CLI tool block | 322 / 354 ms | 288 / 323 ms |
| 3.14, Local prompt allow | 365 / 371 ms | 325 / 332 ms |
| 3.14, Local prompt block | 364 / 371 ms | 327 / 331 ms |
| 3.14, CLI tool allow | 364 / 369 ms | 326 / 333 ms |
| 3.14, CLI tool block | 370 / 381 ms | 331 / 343 ms |

The paired median saving is **34–40 ms per hook**, approximately **10–11% of
local overhead**. The `--version` startup control falls from 221 to 51 ms on 3.11
and 234 to 74 ms on 3.14, but it does not perform a policy check and is not a
representative request-latency improvement. Actual hook invocations still load
HTTP and JSON Schema dependencies. Jev and remote-network latency are additional;
we have not measured a new live end-to-end improvement.

Each cell has 30 measurements after one excluded warmup. Fresh processes run in
seeded randomized pairs, with warm filesystem caches and Python versions tested
sequentially. p95 is a small-sample observation, not an SLA. All 496 loopback HTTP
calls (including warmups) produced the expected valid host outputs. Baseline and
candidate use fresh environments with the corresponding locked dependencies.
Source/wheel hashes and summaries are in the
[measurement record](evidence/hook-client-latency-v1.json); raw timings/install logs
remain under ignored `artifacts/performance/hook-client-v1/`.

The package split is useful for endpoint installation and modestly reduces delay.
It does not eliminate Python startup cost. Native-client work should be judged
against the remaining 288–331 ms local median, separately from provider latency;
it is not part of this change.
