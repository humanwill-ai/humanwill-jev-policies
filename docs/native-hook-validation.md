# Native archive validation

2026-10-04 · candidate `0.1.0.dev2-native`; no new public release.

The exact macOS Intel executable from the four-platform archive set passed fresh
VS Code Local and Copilot CLI acceptance. No native code or archive was changed.
All archive checksums were rechecked. The earlier per-platform native tests remain
the evidence for Apple Silicon, Windows and Linux; we did not repeat those Actions
jobs or imply that we ran their desktop editors locally.

## Actual host acceptance

| Host | Version | Result |
|---|---|---|
| VS Code Local | VS Code 1.139.1 / Copilot Chat 0.67.0 | 14/14 scenarios pass |
| Copilot CLI | 1.0.88 | 6/6 scenarios pass |

Platform: Intel macOS 15.7.9. Binary SHA-256:
`d39bc4db2aaf5d1e68a758dee8a32ef75aabd8e26c5908fd88e06f2888e31889`.
The real policy service used the installed published `0.2.0b1` wheel with synthetic
model/evaluator transports. The Local test ran in a separate signed-in fixture
profile; the CLI used offline mode and a temporary workspace. Normal user hooks,
workspace settings and installations were not changed. No hosted Jev calls or
private workflow prompts were involved.

Local covered allow, prompt deny, tool deny, provider errors/timeouts, unavailable
service, malformed input, monitor mode, host timeouts, disabled hooks, and restored
enforcement. Denied actions left no synthetic marker file. Prompt denial prevented
the synthetic model call. CLI covered allow, tool deny, prompt assessment-only,
service failure, host timeout, and disabled hooks.

**Known bypasses remain:** host timeouts and disabled hooks allowed the synthetic
action in the expected bypass scenarios. Passing these tests means the observed
behavior matches the documented limits, not that every scenario blocked. CLI
prompt assessment did not stop the prompt. The faster binary does not make the
host tamper-proof or add a new enforcement stage.

[Sanitized host evidence](evidence/native-host-validation.json) contains all 20
outcomes. Private editor state/raw logs remain ignored under local test directories.
The native binary is selected by a new optional `--hook-binary` argument to both
existing host harnesses; their Python default is preserved. VS Code's `--signed-in`
flag skips the manual wait only when reusing a dedicated signed-in test profile.

## Latency

After host tests completed, the same archive binary was compared with the installed
published Python beta and lightweight Python client on this Intel macOS machine:

| Operation | Legacy Python median / p95 | Lightweight Python median / p95 | Bundled C median / p95 |
|---|---:|---:|---:|
| Local prompt allow | 327.4 / 371.3 ms | 293.0 / 323.4 ms | 18.8 / 19.4 ms |
| Local prompt block | 326.8 / 347.1 ms | 291.0 / 322.7 ms | 18.8 / 20.8 ms |
| CLI tool allow | 328.5 / 355.6 ms | 293.1 / 354.2 ms | 19.0 / 19.6 ms |
| CLI tool block | 324.5 / 335.5 ms | 289.8 / 300.6 ms | 18.9 / 19.3 ms |

The paired median saving versus legacy Python was **306–310 ms per hook**; versus
lightweight Python it was **271–274 ms**. Native local overhead was about **94%
lower** than legacy Python. These results agree with the earlier prototype's
20–21 ms range without establishing a statistically significant improvement over
that prototype.

Method: Python 3.11.5; 30 samples per operation/client, one excluded warmup, seeded
randomized client order in paired rounds, fresh processes, warm filesystem cache.
All 372 synthetic HTTP invocations returned the expected host output. These are
client/process/loopback HTTP/validation timings, not live Jev latency or whole-editor
timings. No provider calls, remote TLS or IDE scheduling are included. Other
platforms have not been benchmarked. No service policies or thresholds changed.

The [latency evidence](evidence/native-bundled-latency.json) records exact binary
and wheel hashes. All 52 baseline package files and 13 lightweight-client package
files matched their respective wheels. The raw runner was initially given a
rebuilt wheel path for its metadata field although the installed baseline was the
published wheel; the evidence corrects that hash after the file comparison, with
timings unchanged and original raw-report hash preserved. An earlier incomplete
benchmark was stopped to avoid overlapping host work; it is not used in the table.

## Remaining release limits

The [four-target build record](native-bundled-builds.md) retains native protocol,
TLS, canonicalization and service evidence for the other targets. Actual desktop
VS Code/CLI acceptance on Apple Silicon, Windows and Linux remains open, as does
Developer ID notarization/Authenticode signing. This run does not establish live
Jev latency, validate arbitrary company policies, or publish new release assets.

For installation and migration, use the [platform guide](native-hook-installation.md).
