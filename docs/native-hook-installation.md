# Install the native hook client

Use the native C client to connect VS Code Local or Copilot CLI to your company's
HumanWill policy service without installing Python on every developer machine.
The service still loads your Markdown policies, calls Jev, and makes policy
decisions. The binary sends the supported hook event and returns the host's
allow/deny output; it does not contain Jev or replace the central service.

The four native archives accompany **Public Beta `v0.2.0b2`**. Their internal
build identifier remains **`0.1.0.dev2-native`**, preserving the exact binaries
validated in CI and the desktop tests. This is the native component's build ID,
not the Python service/release version. `--version` returns that build ID.

Download the archive and checksum from the same
[GitHub release](https://github.com/humanwill-ai/humanwill-jev-policies/releases/tag/v0.2.0b2).
The [build record](native-bundled-builds.md) retains the original GitHub Actions
evidence.

## Choose your download

| Computer | Archive suffix | Executable | Runtime evidence |
|---|---|---|---|
| macOS, Intel | `macos-x86_64.tar.gz` | `humanwill-hook-c` | macOS 15.7.9; actual VS Code Local and CLI validated |
| macOS, Apple Silicon | `macos-arm64.tar.gz` | `humanwill-hook-c` | macOS 15.7.9; native protocol/service tests |
| Windows, Intel/AMD 64-bit | `windows-x86_64.zip` | `humanwill-hook-c.exe` | Windows Server 2025; native protocol tests |
| Linux, Intel/AMD 64-bit | `linux-x86_64.tar.gz` | `humanwill-hook-c` | Alpine 3.22 and Ubuntu 24.04; native protocol/service tests |

macOS builds target 12.0+, but have only been executed on the version above.
There are no Linux ARM, Windows ARM or 32-bit builds. For remote development,
install the executable where the hook actually runs, using that machine's OS/CPU.
Desktop Copilot acceptance on Apple Silicon, Windows and Linux remains untested;
successful binary protocol tests do not establish editor integration on those hosts.

All non-system libraries are bundled. Linux is statically linked; macOS and
Windows retain their normal OS libraries. Linux still needs DNS configuration and
a current CA certificate bundle. These candidates are not Developer ID notarized
or Authenticode signed. Follow your organization's software approval process if
the OS blocks execution; these instructions do not disable OS security controls.

## Install on macOS

Download the archive and its `.sha256` file into the same directory. For Apple
Silicon use `macos-arm64`; for Intel replace it with `macos-x86_64`:

```sh
cd "$HOME/Downloads"
HW_PACKAGE=humanwill-hook-c-0.1.0.dev2-native-macos-arm64
shasum -a 256 -c "$HW_PACKAGE.tar.gz.sha256"
mkdir -p "$HOME/.local/share/humanwill"
tar -xzf "$HW_PACKAGE.tar.gz" -C "$HOME/.local/share/humanwill"
HW_BINARY="$HOME/.local/share/humanwill/$HW_PACKAGE/humanwill-hook-c"
"$HW_BINARY" --version
```

Stop if checksum verification fails. Keep the complete extracted folder, including
licenses and build evidence. Use the executable's **absolute path** in hook
configuration; shell variables in these installation commands are not automatically
expanded inside a hook JSON file.

## Install on Linux

On an x86_64 system, with the archive and checksum in your download directory:

```sh
cd "$HOME/Downloads"
HW_PACKAGE=humanwill-hook-c-0.1.0.dev2-native-linux-x86_64
sha256sum -c "$HW_PACKAGE.tar.gz.sha256"
mkdir -p "$HOME/.local/share/humanwill"
tar -xzf "$HW_PACKAGE.tar.gz" -C "$HOME/.local/share/humanwill"
HW_BINARY="$HOME/.local/share/humanwill/$HW_PACKAGE/humanwill-hook-c"
"$HW_BINARY" --version
```

No libcurl, OpenSSL or Python package installation is needed for the client.
For HTTPS, provision your distribution's `ca-certificates` package or supply an
explicit company CA file as described below. A static executable still requires
permission to execute and reach the policy service.

## Install on Windows

In PowerShell, with the ZIP and `.sha256` file in Downloads:

```powershell
Set-Location "$env:USERPROFILE\Downloads"
$hwPackage = 'humanwill-hook-c-0.1.0.dev2-native-windows-x86_64'
$hwExpected = ((Get-Content "$hwPackage.zip.sha256" -Raw).Trim() -split '\s+')[0]
$hwActual = (Get-FileHash "$hwPackage.zip" -Algorithm SHA256).Hash
if ($hwActual -ne $hwExpected) { throw 'Archive checksum mismatch' }
$hwInstall = Join-Path $env:LOCALAPPDATA 'HumanWill'
New-Item -ItemType Directory -Force $hwInstall | Out-Null
Expand-Archive "$hwPackage.zip" -DestinationPath $hwInstall
$hwBinary = Join-Path $hwInstall "$hwPackage\humanwill-hook-c.exe"
& $hwBinary --version
```

Keep the entire extracted folder. The executable uses Windows certificate trust
and needs no extra DLL download or Python runtime. Windows hook configuration
examples below follow the documented host contracts; they have not yet had an
interactive Windows desktop acceptance run.

## Connect to your policy service

Ask your service administrator for the HTTPS **origin**, such as
`https://policies.company.example`, and the connector token for your runtime.
Do not append `/v1/hooks/...`: the executable chooses the endpoint from its
`--runtime` and `--event` arguments. Local HTTP is supported only for loopback
development, for example `http://127.0.0.1:8088`.

The connector token is separate from your Jev/OpenRouter API key. The provider key
stays on the central service. Supply `HUMANWILL_LOCAL_TOKEN` to the VS Code process
or `HUMANWILL_CLI_TOKEN` to the CLI process through your approved secret-management
mechanism. Do not put token values in committed hook files. A variable set in a
terminal does not change an already-running VS Code process: restart the host
with the required environment. For central service and policy setup, follow the
[service guide](service-and-connectors.md).

For a company CA, append `--ca-file /absolute/path/company-ca.pem` to each command
(use the appropriate Windows path there). Certificate and hostname verification
remain enabled. Proxy environment variables are deliberately ignored by this
client, so the configured endpoint must be reachable directly.

## Configure VS Code Local

Merge the following into your workspace's `.github/hooks/humanwill-local.json`.
Replace the example executable paths and service origin. The `windows` field
overrides `command` on Windows; macOS/Linux use `command`. Quote paths containing
spaces and escape quotes/backslashes correctly in JSON. The example uses a
space-free Windows path; substitute your actual installed path and validate it
in the host. Do not retain a second Python hook for the same event unless you
intend to evaluate every event twice.

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "type": "command",
      "command": "\"/ABSOLUTE/PATH/humanwill-hook-c\" --runtime copilot_local --event UserPromptSubmit --url https://policies.company.example --token-env HUMANWILL_LOCAL_TOKEN --timeout-ms 6000 --on-error block",
      "windows": "C:/HumanWill/humanwill-hook-c.exe --runtime copilot_local --event UserPromptSubmit --url https://policies.company.example --token-env HUMANWILL_LOCAL_TOKEN --timeout-ms 6000 --on-error block",
      "timeout": 15
    }],
    "PreToolUse": [{
      "type": "command",
      "command": "\"/ABSOLUTE/PATH/humanwill-hook-c\" --runtime copilot_local --event PreToolUse --url https://policies.company.example --token-env HUMANWILL_LOCAL_TOKEN --timeout-ms 6000 --on-error block",
      "windows": "C:/HumanWill/humanwill-hook-c.exe --runtime copilot_local --event PreToolUse --url https://policies.company.example --token-env HUMANWILL_LOCAL_TOKEN --timeout-ms 6000 --on-error block",
      "timeout": 15
    }]
  }
}
```

Sign in to Copilot, trust the workspace, enable `chat.useHooks`, and select the
**Local** runtime. These are Local event names and payloads, not the Agent Host
contract. See the [VS Code Local reference](https://code.visualstudio.com/docs/agents/reference/hooks-reference).

## Configure Copilot CLI

Use this separate configuration in the CLI workspace's
`.github/hooks/humanwill-cli.json`. Do not copy Local hooks into CLI or install
both examples indiscriminately in a shared workspace. Preserve the distinct
runtime setup described in the [connector guide](service-and-connectors.md#install-and-remove-copilot-hooks).

```json
{
  "version": 1,
  "hooks": {
    "userPromptSubmitted": [{
      "type": "command",
      "bash": "\"/ABSOLUTE/PATH/humanwill-hook-c\" --runtime copilot_cli --event userPromptSubmitted --url https://policies.company.example --token-env HUMANWILL_CLI_TOKEN --timeout-ms 6000 --on-error block",
      "powershell": "& 'C:/HumanWill/humanwill-hook-c.exe' --runtime copilot_cli --event userPromptSubmitted --url https://policies.company.example --token-env HUMANWILL_CLI_TOKEN --timeout-ms 6000 --on-error block",
      "timeoutSec": 15
    }],
    "preToolUse": [{
      "type": "command",
      "bash": "\"/ABSOLUTE/PATH/humanwill-hook-c\" --runtime copilot_cli --event preToolUse --url https://policies.company.example --token-env HUMANWILL_CLI_TOKEN --timeout-ms 6000 --on-error block",
      "powershell": "& 'C:/HumanWill/humanwill-hook-c.exe' --runtime copilot_cli --event preToolUse --url https://policies.company.example --token-env HUMANWILL_CLI_TOKEN --timeout-ms 6000 --on-error block",
      "timeoutSec": 15
    }]
  }
}
```

Trust the intended CLI workspace. Submitted prompts are **assessment-only** in
this connector; `preToolUse` can deny actions. Changing from Python to C does not
add prompt blocking. GitHub documents the separate `bash`/`powershell` fields and
timeout behavior in its [hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference).

## Verify before relying on enforcement

`--version` confirms that the executable starts, not that policies are enforced.
In a disposable workspace, use synthetic examples to check an allowed request
and a harmless tool action that a test policy should deny. Confirm both the
service audit and the absence of the denied action's effect. A monitor-mode
policy can report a violation while intentionally letting the operation continue.

`--timeout-ms 6000` is the client's network deadline; `timeout`/`timeoutSec` is the
host deadline. Leave enough host time for the client to return its fallback.
`--on-error block` is the default; `allow_monitor` explicitly permits continuation
on client errors and is not a compliance verdict. Service evaluation-error policy
settings are separate. Host timeouts, disabled hooks and endpoint tampering can
bypass this layer. See [security considerations](operations.md#security-considerations).

Fresh native acceptance on Intel macOS passed all **14 VS Code Local scenarios**
and **six CLI scenarios**, including allow, deny, errors, monitoring and known
bypasses. The [validation record](native-hook-validation.md) gives exact versions,
artifact hashes and limits. No live Jev or private prompts were used.

## Latency compared with Python

The packaged Intel macOS binary measured **18.8–19.0 ms median** local hook
overhead versus **324–328 ms** for the legacy `humanwill-policies hook` command
and **290–293 ms** for the lightweight Python client. Paired median savings were
**306–310 ms per hook** versus legacy Python—about **94% less local overhead**.
Native p95 was **19.3–20.8 ms**, versus **335–371 ms** for legacy Python across
the four measured operations. p95 describes the slow end: 95% of samples are at
or below that measured value.

The [validation report](native-hook-validation.md#latency) contains the complete
comparison. Each operation used 30 fresh-process samples per client, randomized
in paired rounds with synthetic loopback replies. These measurements include
startup, validation and local HTTP; they exclude remote network/TLS, Jev inference,
follow-ups, and editor scheduling. They do not promise the same overall request
latency or savings on other platforms. The earlier **20–21 ms** prototype result
is preserved in the [original report](native-hook-client.md).

## Upgrade, roll back, or keep Python

Keep versioned installation folders and verify the new archive before changing
the hook executable path. Retain the old folder until allow/deny checks pass.
Roll back by restoring that path; no policy migration is required.

To use Python instead, replace the native executable with either the standalone
`humanwill-hook` command or `humanwill-policies hook`, keeping the runtime/event,
URL, token environment name, timeouts and fallback arguments. The native-only
`--ca-file` option is not interchangeable with Python's TLS configuration.
See the [Python client guide](hook-client.md). Remove only the HumanWill entries
when uninstalling, preserving other hooks in the workspace.
