# Next public release: native and Python hook clients

Owner decision, 2026-10-04: include the C hook client in the next public release
and retain Python as a user-selectable alternative. Target four precompiled native
downloads. Release preparation is authorized; this does not publish a new tag,
upload assets, modify user hook installations, or authorize paid signing accounts.
Freeze the next release version when the candidate is ready; do not overwrite
the already published `0.2.0b1` artifacts.

## User choices and target downloads

Present the native client as the low-overhead installation option on validated
platforms. Keep the standalone `humanwill-hook-client` Python wheel/source archive
and the existing full-package `humanwill-policies hook` command. No forced migration
or automatic replacement of existing configurations. All use the same central
Python policy service, policies, authentication and host-event contracts.

| Target | Planned archive suffix | Executable | Current evidence |
|---|---|---|---|
| macOS Intel, x86_64 | `macos-x86_64.tar.gz` | `humanwill-hook-c` | 108 contract + eight service checks pass; Intel additionally passes 14 Local + six CLI host scenarios |
| macOS Apple Silicon, arm64 | `macos-arm64.tar.gz` | `humanwill-hook-c` | Bundled native build: 108 contract + eight service checks pass |
| Windows Intel/AMD, x86_64 | `windows-x86_64.zip` | `humanwill-hook-c.exe` | Bundled native build: 108 contract checks pass on Windows Server 2025 |
| Linux Intel/AMD, x86_64 | `linux-x86_64.tar.gz` | `humanwill-hook-c` | Static musl build: 108 contract + eight service checks pass on Alpine and Ubuntu |

Archive names include `humanwill-hook-c-{version}-` before these suffixes. x86_64
means 64-bit Intel/AMD; no 32-bit x86 target. Linux ARM, Windows ARM and a universal
macOS archive are outside this initial matrix. Publish minimum OS versions and
tested host versions per target. Linux x86_64 has been tested on Alpine/musl and Ubuntu; that does not promise all
distributions or kernels. See [bundled build evidence](native-bundled-builds.md).
Python availability likewise does not establish untested Windows service support.

## Preparation sequence

1. **Port and pin the build.** Add a cross-platform build definition alongside the
   current Makefile. Replace POSIX-only regex/string calls with bounded portable
   equivalents; retain generated-schema validation and drift rejection. Add Windows
   binary stdin/stdout handling, path/argument tests, and an explicit SHA-256/TLS
   implementation choice. Pin downloaded build dependencies and record hashes.
   Python may remain a build-time schema generator; native users need neither
   Python nor a compiler.
2. **Package usable archives.** Prefer macOS system libraries. For Windows, prefer
   a libcurl build using Schannel and OS certificate trust; bundle any required
   non-system runtime libraries. Select an explicit Linux ABI baseline and verify
   all shared-library requirements on a clean machine/container. Include licenses,
   third-party notices, dependency inventory, version/build provenance, SHA-256
   checksums, install/configuration instructions and rollback steps in the release.
   Avoid accidental dependencies on developer Homebrew/vcpkg/build directories.
3. **Validate exact binaries on each target.** Run the protocol/security suite,
   numeric/Unicode hashing comparison, malformed-input checks and actual-service
   tests against extracted release archives. Test trusted and rejected HTTPS,
   timeouts, both fallback modes, authentication, and paths containing spaces.
   Run sanitizers where supported and smoke-test installation without a Python
   runtime. Exercise actual VS Code Local/CLI invocation on declared supported
   hosts; record those separately from synthetic wire-contract checks. Keep the
   Python wheel/source and legacy-command checks in the release gate.
4. **Prepare one consolidated CI/release candidate.** Use one native build/test
   matrix with exact artifact retention, alongside the existing core/host checks.
   Avoid duplicate dispatches and automatic publication. Verify runner availability
   when implementing the workflow. Arrange platform signing/notarization where
   credentials are available; record signature verification and limitations. Do
   not purchase certificates or silently bypass OS security prompts. Stage the
   concrete assets and release notes for owner confirmation before publication.

Platform code changes must preserve request binding, complete result validation,
content minimization, TLS verification, explicit errors and CLI assessment-only
behavior. The native client remains a remote client; this release does not move
Jev or policy decisions into C or make hook enforcement tamper-proof.

## Performance claims

Retain the [measured comparison](native-hook-client.md): approximately 20–21 ms
local median on Intel macOS versus 288–289 ms for lightweight Python. These are
synthetic loopback measurements, not live Jev end-to-end timings or measurements
on the other architectures. The approximately 0.5-second overall C estimate must
not be published as an observed median. A paired live comparison may establish
that later using the existing accounting rules and synthetic content only.

## Remaining release work

- Minimum macOS/Windows versions and Linux ABI/distribution baseline.
- Available macOS Developer ID/notarization and Windows signing credentials.
- Final public package version. The current build identifier is
  `0.1.0.dev2-native`; it is not a new public release version.
- Interactive VS Code/CLI acceptance on Apple Silicon, Windows and Linux. The
  [exact Intel macOS binary now passes](native-hook-validation.md) both hosts.
- Complete the final release review and obtain owner confirmation to publish.

These details do not block local portability/build work. They must be settled
before advertising frictionless signed installation or broad OS support.

Primary references checked 2026-10-04:
[Windows stream translation](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/setmode?view=msvc-170),
[libcurl TLS trust stores](https://curl.se/docs/sslcerts.html), and
[Apple Developer ID distribution](https://developer.apple.com/developer-id/).
Windows text-mode translation needs explicit treatment; Schannel uses the native
Windows CA store; Apple Developer ID and notarization concern downloaded-software
trust. These are documented platform behaviors, not completed project validation.
