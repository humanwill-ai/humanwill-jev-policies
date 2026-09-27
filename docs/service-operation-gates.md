# Local service operation checks

2026-09-27 · step 6 operational evidence, synthetic provider only

Run `python tests/hosts/service_operations.py` from a checkout or extracted source
archive with the package installed. The script starts a real Uvicorn listener on
loopback and uses authenticated HTTP requests. It never calls a hosted model,
reads a provider credential, or installs hooks. The provider transport returns
controlled answers; the fixture uses config/2. Existing unit tests separately
exercise config/3 service and hook results.

## Observed checks

- 100 serial warm requests and 80 requests in batches of eight all allowed.
- A burst of 32 requests to a deliberately slow evaluator all returned explicit
  fail-closed errors. The evaluator has its own smaller admission limit; these
  results combine evaluator overload and timeout, not 32 model timeouts.
- Holding eight HTTP request bodies open filled the separate service admission
  limit. An additional authenticated request received `service_overloaded`.
- Provider errors and explicit violations requested blocking. A subsequent clean
  request allowed, readiness remained available, and an invalid token got 401.
- An invalid on-disk policy was rejected by the loader. The running service kept
  its previously validated immutable snapshot. After restoring that exact policy
  and restarting the listener/application, the same bundle hash allowed again.

This tests validation and application restart with a restored bundle. It does not
exercise an operating-system service manager, rolling deployment, or persistent
state recovery; the service has no persistent database.

## Timing observation

One local macOS/Python 3.14 run, with a synthetic in-process provider:

| Workload | Requests | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: |
| Warm serial | 100 | 4.446 ms | 4.933 ms | 5.214 ms |
| Batches of eight | 80 | 35.009 ms | 45.705 ms | 47.134 ms |
| Evaluator timeout/overload burst | 32 | 118.806 ms | 331.720 ms | 334.459 ms |

First HTTP request: 28.161 ms. The same functional checks also passed locally
on Python 3.11; its warm serial p95 was 4.427 ms and batch-of-eight p95 43.120 ms. This includes local client, network and service
work; it is **not** pure service overhead, provider latency, real gateway added
latency, or sustained production capacity. The run predates the commit of this
harness and records base commit `8d6083f` with a dirty tree. Raw, reproducible local
output is ignored at `artifacts/operations/service.json`; CI also runs the harness
against its candidate commit.

No paid calls or semantic labels are involved. The checks strengthen operational
evidence but do not close the independent holdout, real-provider concurrency, or
end-to-end host latency gates in the [release roadmap](public-release-plan.md).
