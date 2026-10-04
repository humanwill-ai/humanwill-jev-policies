# Native C hook client and latency comparison

Status: unreleased implementation; original measurements on Intel macOS on 2026-10-04.
The [four bundled builds](native-bundled-builds.md) now have target-runtime evidence;
the measurements below remain those of the earlier system-library development build.
The published beta and installed Copilot configurations remain unchanged.

The owner selected this client for the next public release, keeping Python as an
option. The [release plan](native-release-plan.md) targets four precompiled platform
downloads and records the remaining portability, packaging and validation work.

The owner requested a native C counterpart after separating and measuring the
lightweight Python client. `humanwill-hook-c` now performs the remote hook flow
without starting Python: read/minimize the host event, validate it, authenticate
to the central service, validate and bind the verdict, then emit the host's JSON
allow/deny response. It supports VS Code Local and Copilot CLI's existing events.
Company policies, Jev inference and any follow-up calls remain on the service.

[Build, installation and compatibility details](../clients/hook-c/README.md)
include the exact command substitution. The C code embeds the existing schemas
at build time, and uses libcurl plus pinned yyjson source with its MIT license.
The tested macOS binary links only system libcurl/libSystem and is about 316 KiB.
Python is needed for schema generation during a source build, not at runtime.

## Measurement

The completed comparison uses Python 3.11.5 for both Python clients and an `-O2`
native build, all on the same Intel macOS machine:

| Operation | Released Python median / p95 | Lightweight Python median / p95 | Native C median / p95 |
|---|---:|---:|---:|
| Local prompt allow | 323.4 / 330.8 ms | 287.5 / 296.5 ms | 20.4 / 22.0 ms |
| Local prompt block | 322.9 / 327.7 ms | 288.1 / 296.0 ms | 20.4 / 21.2 ms |
| CLI tool allow | 323.0 / 337.2 ms | 288.7 / 294.6 ms | 20.5 / 21.6 ms |
| CLI tool block | 322.6 / 326.4 ms | 288.6 / 291.6 ms | 20.7 / 22.6 ms |

The paired median saving versus lightweight Python is **267–268 ms per hook**,
about **93% less local overhead** (roughly 14× faster). Versus the released client,
the native client saves about 302–303 ms. Startup-only `--version` medians are
214.1 / 50.1 / 8.0 ms respectively; the table above measures actual hook operations.

All runs use the exact published beta wheel, the previously verified lightweight
Python wheel, and the optimized native executable. The clients receive identical
synthetic events and valid allow/block verdicts from a loopback HTTP server. Each
runs as a new process. All 372 HTTP invocations, including warmups, produced the
expected host outputs. Exact hashes and summaries are in the
[evidence record](evidence/native-hook-latency-v1.json); full timings and logs are
retained under ignored `artifacts/performance/hook-c-v1/`.

The benchmark has 30 measurements per client/operation, one excluded warmup per
cell, and seeded randomized ordering within each round. Filesystem caches are
warm. It measures process startup, normalization, HTTP, complete result validation,
request binding and host-output serialization. It excludes Jev, remote TLS/network
latency, host/IDE scheduling and larger production payloads. A faster client does
not reduce model inference time or the number of evaluator calls.

## Verification

- 107 checks pass on both optimized and AddressSanitizer/UndefinedBehaviorSanitizer
  executables. This includes all four supported hook events, result formats 2–4,
  both fallback modes, request/coverage binding, invalid schemas/duplicate keys,
  body/depth limits, redirects, proxy bypass, timeouts, minimized fields, credential
  handling and rejection of an untrusted TLS certificate.
- Request hashing matches Python for Unicode and nested/numeric tool arguments,
  plus 10,000 finite randomly sampled double values and numeric boundaries.
- 200 deterministic malformed-input mutations complete without crashes or sanitizer
  diagnostics. This is smoke fuzzing, not exhaustive fuzzing or a security audit.
- Eight additional checks run the native executable against the actual HumanWill
  HTTP service with scripted evaluator answers: allow/block for every supported
  event. No Jev/provider calls are made.

The native parser deliberately rejects some unusual inputs accepted by Python
(lone surrogate escapes, newline-suffixed identifiers, oversized origins/tokens).
They receive the configured error fallback. See the client README for exact limits.
Schema generation fails on newly introduced unsupported validation keywords or
patterns. Future schema changes still require native compatibility validation.

This is a new C implementation, with independent maintenance and memory-safety
risks despite the passing checks. Before a public native release, validate target
architectures/OS versions, packaging/signing/upgrade/rollback, dependency inventory,
and actual editor/CLI invocation. Neither Windows nor ARM/Linux execution is
claimed here; the existing Python release remains the supported rollback path.
Host-timeout and disabled-hook bypasses remain unchanged.

## Reproduce

From the repository root, using its pinned development Python environment:

```sh
make -C clients/hook-c PYTHON=/absolute/path/to/.venv/bin/python all probe
python scripts/verify_native_hook.py \
  --binary artifacts/native-hook/humanwill-hook-c \
  --probe artifacts/native-hook/canonical-probe \
  --report artifacts/native-contracts.json
python scripts/verify_native_service.py \
  --binary artifacts/native-hook/humanwill-hook-c \
  --report artifacts/native-service.json
```

For sanitizer checks, choose a separate `OUT` directory and set
`CFLAGS='-O1 -g -std=c11 -Wall -Wextra -Werror -Wno-deprecated-declarations -fsanitize=address,undefined -fno-omit-frame-pointer'`.
Run the same verifier against those outputs. Use optimized, unsanitized executables
for timing. The comparison runner accepts the same isolated Python environments
as the [Python measurement](hook-client.md) plus:

```sh
python scripts/benchmark_hook_client.py \
  --baseline-python /baseline/venv/bin/python \
  --client-python /client/venv/bin/python \
  --baseline-wheel /path/to/released-humanwill.whl \
  --client-wheel /path/to/hook-client.whl \
  --native-binary artifacts/native-hook/humanwill-hook-c \
  --report artifacts/native-latency.json
```

Keep previous reports; each verification/benchmark command requires a new report
path. Raw measurements, compiled binaries and logs remain ignored local artifacts.
