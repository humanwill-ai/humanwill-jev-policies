# Bundled native hook binaries

2026-10-04 · all four candidate binaries built and verified; no public release/tag created.

Owner requested four precompiled targets from one C codebase, with non-system
libraries bundled into the executable. The `0.1.0.dev2-native` candidate statically
links curl 8.22.0 and yyjson 0.12.0. macOS/Linux also bundle OpenSSL 3.5.9; Windows
uses OS Schannel and BCrypt. Only the platform layer handles binary streams and
SHA-256; normalization, schemas, HTTP behavior and decision output are shared.

| Target | Build and checks | Compressed archive |
|---|---|---:|
| macOS x86_64 | Native macOS 15.7.9: 108 contract + eight actual-service checks pass | 2.53 MiB |
| macOS arm64 | Native macOS 15.7.9: 108 contract + eight actual-service checks pass | 2.78 MiB |
| Windows x86_64 | Windows Server 2025 runner: 108 contract checks pass; OS DLLs only | 0.44 MiB |
| Linux x86_64 | Fully static musl; 108 contract + eight actual-service checks on both Alpine 3.22 and Ubuntu 24.04 | 3.27 MiB |

The contract suite includes four hook profiles, verified/untrusted HTTPS, timeout
fallback, request/coverage binding, 10,000 finite-double canonicalization samples,
and 200 malformed-input mutations. The actual-service tests use the real Python
HTTP service with a scripted evaluator; no Jev/provider calls. Windows runs the
native client against the synthetic wire-contract server, not the full Python
policy service. Its Python-reported OS string contains `Windows-10`; the actual
Actions runner is `windows-2025`, not evidence of a Windows 10 desktop run.

Successful jobs: [both macOS targets](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/37214678727),
[Linux](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/37215118126),
[Windows](https://github.com/humanwill-ai/humanwill-jev-policies/actions/runs/37215293319).
The initial matrix overall failed: Windows needed Windows SDK headers before
BCrypt; Linux needed writable host report directories after the root-owned
container build. Windows' first repair then found an expected timeout disconnect
reported as `ConnectionAbortedError`; the harness now treats that like its POSIX
counterparts. Only failed targets were rerun; successful Mac jobs were retained.
No security assertions or certificate verification were weakened.

Exact source commits, binary/archive SHA-256 values and OS dependency lists are
in [the evidence inventory](evidence/native-bundled-builds.json). Source is on
`work/native-bundled-binaries`; main and published beta assets are unchanged.
The builds use the same C implementation. Source differences between the platform
runs are the Windows include-order fix and test/build/notice changes; no separate
platform fork or policy-decision implementation exists.

Final local archives are in `dist/native/` with `SHA256SUMS`, individual checksum
files, and extracted executables under `dist/native/extracted/<target>/`.
`scripts/collect_native.py` collected the CI-tested executables and supplemented
README/license notices and Linux Ubuntu evidence. Every binary's hash remains
identical to the tested CI artifact; final archive hashes differ and are recorded
alongside the original CI archive hashes. Original downloads, logs and Alpine
package inventory remain under ignored `artifacts/native-bundled/`. Each final
archive includes its build manifest, packaging provenance and verification reports.

The workflow `.github/workflows/native.yml` uses a dedicated build branch and
retains exact binaries, dependency manifests, archive/binary SHA-256 values and
verification reports. It has no release-publication job. It sends only source and
synthetic test data to Actions; private prompts, credentials and local evaluation
artifacts are excluded from the build-branch changes.

## What "bundled" means

Users do not need Python, a compiler, a separate libcurl/OpenSSL installation, or
extra non-system DLLs/dylibs. macOS/Windows still use system libraries. The Linux
binary is fully static against musl; it still needs normal OS resources such as
DNS configuration and CA certificate files. macOS/Windows use OS certificate trust
by default. An explicit `--ca-file` selects a company CA bundle without disabling
certificate or hostname checks. No CA-trust snapshot is embedded in the binary.

Builds and package audits reject unexpected dynamic dependencies. Linux is tested
on Alpine and Ubuntu; that does not promise compatibility with every kernel or
distribution. macOS compilation targets 12.0+, but execution evidence is tied to
the actual runner OS. Windows build/runtime evidence is on the Actions Windows
Server image and does not replace a Windows desktop/Copilot acceptance run.

## Candidate limits

No Developer ID notarization or Authenticode signing has been performed. The
binaries are suitable for release review and target-runtime testing; downloading
and launching them may invoke OS trust controls. Do not disable those controls
as part of an installer. Fresh [actual VS Code Local and CLI acceptance](native-hook-validation.md) now
passes on the exact Intel macOS archive binary (14 Local + six CLI scenarios).
Other platforms retain their native contract/service evidence; desktop host
acceptance there remains open. No paid provider calls were made.

The [fresh bundled-binary comparison](native-hook-validation.md#latency) measures
18.8–19.0 ms local median on Intel macOS versus 324–328 ms legacy Python. This is
synthetic loopback overhead, not live Jev end-to-end latency or other-platform
timing. The Python client remains an option and rollback path. See the
[platform installation guide](native-hook-installation.md).
