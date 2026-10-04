# Bundled native hook binaries

2026-10-04 · work in progress; no public release/tag has been created.

Owner requested four precompiled targets from one C codebase, with non-system
libraries bundled into the executable. The `0.1.0.dev2-native` candidate statically
links curl 8.22.0 and yyjson 0.12.0. macOS/Linux also bundle OpenSSL 3.5.9; Windows
uses OS Schannel and BCrypt. Only the platform layer handles binary streams and
SHA-256; normalization, schemas, HTTP behavior and decision output are shared.

| Target | Build and checks |
|---|---|
| macOS x86_64 | Local bundled build, 108 contract checks and eight actual-service checks pass; only OS frameworks/libSystem dynamically linked |
| macOS arm64 | GitHub native build/runtime checks pending |
| Windows x86_64 | GitHub native build/runtime checks pending |
| Linux x86_64 | GitHub musl/static build plus Alpine/Ubuntu runtime checks pending |

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
as part of an installer. Actual signed-in VS Code/CLI acceptance on these exact
binaries remains separate from protocol tests. No paid provider calls are made.

The earlier 20–21 ms measurement covers the development binary using system
libcurl. Bundled builds have not yet been timed against live Jev; do not present
an estimated overall median as a measurement of these four builds. The Python
client remains an option and rollback path.
