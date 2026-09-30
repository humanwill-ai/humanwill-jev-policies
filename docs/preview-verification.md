# Candidate verification

2026-09-30 · `0.1.0a1` · local preparation, no new GitHub Actions run.

## Completed checks

- 254 unit/contract tests on Python 3.14 and Python 3.11; Ruff lint and formatting.
  Two review-import assertions were updated for the owner's 170-case/12-removal
  baseline. Historical 175-case composition tests retain their original fixtures.
- Exact wheel and source archive installed separately in fresh environments outside
  the checkout. Offline demo/schema checks, both gateway contracts, Local/CLI hook
  contracts, stage-aware follow-up paths and installed service processes pass.
- Installed service startup, authentication, no-egress behavior, invalid-config
  rejection and rollback/restart pass. Synthetic loopback operation checks cover
  load, overload, provider failures/recovery, immutable running bundle and restart.
- Real LiteLLM 1.102.1 and Copilot CLI 1.0.88 host tests run outside the checkout with
  an installed candidate wheel and copied harnesses. Both pass their allow, deny,
  monitor/assessment and failure/bypass scenarios. The host fixtures use controlled
  model answers; this is protocol/enforcement evidence, not live model accuracy.
- **Fresh VS Code Local acceptance passes all 14 scenarios** on editor 1.139.1 /
  Copilot Chat 0.67.0, macOS x86_64, using the exact installed candidate wheel
  outside the checkout. See [sanitized results and hashes](evidence/preview-vscode-local-2026-09-30.json).
  A short private temporary profile reused the earlier dedicated sign-in. Prompt
  denial stops before model invocation; tool denial prevents the marker; provider,
  service and malformed-input failures block; monitoring permits; host timeouts
  and disabled hooks bypass; restoring hooks restores denial. No paid model calls.
- Fresh Jev fullpack run and separate real-LiteLLM/hook-process live latency run;
  see [quality](preview-final-v1-report.md) and [latency](preview-latency-v1-report.md).

The candidate wheel/source verification report and checksums are local under
`artifacts/packaging/preview-final`. Those identify exact built bytes; a version
string alone does not. Host checks initially used the preparation wheel; package
member parity against the final wheel is checked separately. Source reports are
kept public-safe; raw test/profile logs and evaluator payloads remain ignored.

## Limits and unfinished fresh-host checks

- **Agentgateway 1.5.0:** fresh installed-artifact adapter contracts pass. The real
  Linux amd64 host evidence is the earlier pinned Actions run. This macOS x86_64
  machine has no matching release binary, Linux runtime or Docker. No fresh actual
  Agentgateway or container build is claimed, and no quota-consuming job was
  dispatched. Cross-platform candidate CI also remains unrefreshed.
- Native gateway host fixtures use the stable synthetic contract configuration;
  config/5 follow-up behavior is covered by installed-artifact tests and live
  LiteLLM/hook latency. Do not imply every host/profile combination was exercised.
- Direct TypeSafe transport contracts pass; its separate live smoke remains waived
  for this release by the owner.

The first service-operation attempt completed its assertions outside the checkout
but could not write its provenance report because the harness expects Git metadata.
It was rerun with the installed wheel and copied harness from a Git-aware working
directory; this was a harness reporting issue, not a service failure.

These checks establish a useful local candidate. They do not close the independent
semantic qualification or the remaining public-release licensing/history/exposure
review. No public release, deployment, tag, visibility change or push occurred.

## VS Code retry and harness correction

The earlier inconclusive attempt is preserved. A diagnostic retry exposed
`listen EINVAL`: the profile's IPC socket path exceeded macOS's 103-byte limit.
The editor exited before the fixture started; this was not a policy denial or an
established authentication failure. Launching the native editor with a short
`/tmp` profile reached fixture readiness and completed all fourteen cases.

The harness now defaults to a private short temporary directory and rejects overly
long macOS profile paths before launching. Ruff and a negative startup-preflight
check pass. The successful host run used the candidate's original harness with an
explicit short path; the subsequent harness change only prevents this setup error.
The candidate wheel and source archive bytes were not replaced by this retry;
updated documentation/harness belong in the next source packaging pass before
publication. Original artifact reports remain preserved beside the new retry record.
