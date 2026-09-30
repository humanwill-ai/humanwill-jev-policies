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
- Fresh Jev fullpack run and separate real-LiteLLM/hook-process live latency run;
  see [quality](preview-final-v1-report.md) and [latency](preview-latency-v1-report.md).

The candidate wheel/source verification report and checksums are local under
`artifacts/packaging/preview-final`. Those identify exact built bytes; a version
string alone does not. Host checks initially used the preparation wheel; package
member parity against the final wheel is checked separately. Source reports are
kept public-safe; raw test/profile logs and evaluator payloads remain ignored.

## Limits and unfinished fresh-host checks

- **VS Code Local:** the candidate passes Local adapter contracts and executable
  live latency checks. A fresh actual-editor attempt reused a private copy of the
  earlier isolated signed-in profile but timed out before the first `allow` case
  completed. No fresh editor pass is claimed. The successful fourteen-scenario
  signed-in run on VS Code 1.139.1 / Copilot Chat 0.67.0 remains historical evidence
  in [the integration report](integration-report.md). The current attempt did not
  establish whether the obstacle was session state or fixture startup.
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
