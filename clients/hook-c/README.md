# Native C hook client (unreleased)

For precompiled downloads, use the repository
[platform installation guide](../../docs/native-hook-installation.md).
[Fresh host acceptance and bundled-binary timings](../../docs/native-hook-validation.md)
are separate from the earlier prototype measurements below.

Selected for the next public release alongside the Python clients. Bundled
candidates target macOS x86_64/arm64, Windows x86_64 and Linux x86_64. See
`docs/native-bundled-builds.md` for the exact per-target verification record.

`humanwill-hook-c` is a native counterpart to the Python remote hook client. It
sends the same supported prompt/tool fields to an existing authenticated HumanWill
service. Policies, Jev calls and decisions remain on that service. It needs no
Python interpreter at runtime and does not change model evaluation or coverage.

The bundled release build uses one C implementation with a small OS integration
layer. libcurl and yyjson are statically linked. macOS/Linux also link a pinned
OpenSSL build statically; Windows uses Schannel and BCrypt. Linux is built against
musl with no shared-library dependencies. macOS and Windows still use their system
frameworks/DLLs, as native programs normally do. OS trust certificates remain OS
configuration; they are not frozen into the binary.

Build on the target OS with a C toolchain, CMake, and build-time Python:

```sh
python scripts/build_native.py --workdir artifacts/native-build
artifacts/native-build/bin/humanwill-hook-c --version
```

macOS also needs Perl/Make for the static OpenSSL build. Windows uses Visual Studio
2022 or newer with its C++/Windows SDK components. The Windows executable ends in
`.exe`. Linux release builds run in the pinned Alpine/musl container in
`.github/workflows/native.yml`. Dependency source URLs and SHA-256 values are in
`dependencies.json`; no unpinned system libcurl/OpenSSL is used in these builds.
The older Makefile remains a development-only system-library build.

Per-target build and test evidence is recorded in `docs/native-bundled-builds.md`.
These archives remain release candidates,
not replacements for published beta assets. macOS artifacts are not Developer ID
signed/notarized, and Windows artifacts are not Authenticode signed. No paid
signing account or certificate is required merely to compile/test them.

## Install a precompiled archive

Extract the archive for your OS/CPU into a stable directory; no package manager
or Python environment is needed for the executable. Preserve the accompanying
license notices. Check the archive SHA-256 against its `.sha256` file, and check
`SHA256SUMS` inside for the executable hash. The service URL and token are still
required: this archive does not include the central Python policy service.

Run `humanwill-hook-c --version` (`humanwill-hook-c.exe --version` on Windows)
from the extracted directory. For a path containing spaces, quote the executable
path in the host hook command; escape backslashes if editing JSON on Windows.
Then replace the existing `/path/humanwill-policies hook` or `/path/humanwill-hook`
command with an absolute path to `humanwill-hook-c`, preserving its arguments:

```sh
/absolute/path/humanwill-hook-c --runtime copilot_local \
  --event UserPromptSubmit --url https://policies.company.example \
  --token-env HUMANWILL_LOCAL_TOKEN --timeout-ms 6000 --on-error block
```

The executable supports both Local events (`UserPromptSubmit`, `PreToolUse`) and
CLI events (`userPromptSubmitted`, `preToolUse`). CLI prompt hooks remain
assessment-only. Host timeouts, disabled hooks and endpoint tampering remain
limitations. Revert by restoring the Python executable path. No host configuration
is modified by the build or tests.

## Security and compatibility

The client uses verified HTTPS for remote origins; HTTP is restricted to loopback
origins. An optional `--ca-file /path/to/company-ca.pem` explicitly selects a trusted CA
bundle; certificate verification stays enabled. It disables proxy environment inheritance, redirects, netrc credentials
and application retries, bounds request/response size and depth, rejects duplicate
JSON keys/nonfinite numbers, validates complete result schemas, checks request
SHA-256 and exact inspected coverage, and rejects simulated enforced verdicts.
Only the existing prompt/tool fields are transmitted. Error fallback defaults to
block, with the explicit `allow_monitor` alternative retained. Diagnostics contain
no payloads, tokens, paths or transport exception details.

The four canonical request/result schemas are embedded at build time. The C
validator implements their present keyword set; schema generation rejects unknown
keywords/patterns rather than silently dropping validation. This is not a general
JSON Schema engine. Future schema/contract changes require a coordinated native
update and compatibility tests. The native version uses OS/libcurl trust roots;
the Python HTTPX environment may use a different CA bundle.

JSON canonicalization reproduces Python's ASCII escaping, Unicode key ordering,
integer representation and shortest-double formatting for request binding. Tests
include 10,000 finite double values and Unicode/numeric tool arguments. Strict
UTF-8 parsing rejects lone surrogate escapes that Python can decode; the native
client also rejects trailing newlines in identifiers, tokens over 8192 bytes and
origins over 4096 bytes. These edge inputs produce the configured error fallback;
they are not silently accepted with weaker validation. Normal protocol inputs
retain their host outputs.

[yyjson 0.12.0](https://github.com/ibireme/yyjson/tree/8b4a38dc994a110abaec8a400615567bd996105f)
is vendored with its MIT license and exact source hashes. libcurl's documented
[proxy-disable setting](https://curl.se/libcurl/c/CURLOPT_PROXY.html) is explicit.
Our parser adds duplicate-key rejection and depth/size limits around yyjson's
[strict JSON and numeric handling](https://github.com/ibireme/yyjson/blob/8b4a38dc994a110abaec8a400615567bd996105f/doc/API.md).
Keep `vendor/yyjson/LICENSE`, the project license/notices, and relevant platform
library notices with any future binary distribution.

## Tests and performance

`scripts/verify_native_hook.py` exercises synthetic loopback HTTP/TLS contracts,
invalid/altered replies, timeouts, redirects, proxy bypass, input minimization,
numeric/Unicode binding and malformed-input mutation smoke tests. It is also run
against an AddressSanitizer/UndefinedBehaviorSanitizer build. No evaluator calls
are needed. These checks do not replace an independent C security review or new
interactive host acceptance.

`scripts/benchmark_hook_client.py --native-binary /absolute/path/humanwill-hook-c`
adds the native executable to the same randomized, fresh-process Python comparison.
All verdicts come from a synthetic loopback service. Measured overhead excludes
Jev inference, remote TLS/network latency and IDE scheduling. See the repository's
`docs/native-hook-client.md` for the measured comparison and reproduction commands.
