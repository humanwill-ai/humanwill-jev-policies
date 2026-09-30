# Preview profile latency confirmation

Freeze before calls on 2026-09-30. Real LiteLLM 1.102.1 with a controlled local
OpenAI-compatible downstream; real Local/CLI hook executables, excluding editor
and agent scheduling. Current `0.1.0a1` runtime, all four final source-v4 policies,
config/5 `q05_stage_aware`, gates 0.80/0.70/0.80, monitor mode, live OpenRouter Jev.

Synthetic 128/4096/12000-character local coding requests; no handwritten fixture
context. Test-owned resolver supplies public document classification, approved
coding route and negative onward/source/destructive authorization. These facts
are not inferred from the prompt. This is a workload illustration, not throughput
certification, a follow-up stress test or a production resolver implementation.

LiteLLM baseline and guarded groups each contain one initial request, 12 serial
requests and 24 at concurrency four. Report request/response path timings and
matched index differences; separate baseline and guarded groups cannot remove
all temporal/provider variation. Each hook runtime gets 12 requests at concurrency
one and four, including Python startup and HTTP. Report p50/p95/p99 and errors;
small samples limit tail estimates. The development-pack report additionally
measures naturally triggered follow-ups.

Maximum 244 physical calls, reserving at most $2.44 inside the existing $5 budget;
actual cost is expected to be much lower. Keep the previously authorized $0.01
historical reservation; stop on new unknown charges. Freeze starting ledger and
runtime/harness inputs, commit, then run once. Do not tune or retry selected rows.
