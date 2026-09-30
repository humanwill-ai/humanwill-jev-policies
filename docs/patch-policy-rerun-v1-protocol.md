# Source-policy clarification: patch-only rerun

Owner authorized applying the proposed clarification and rerunning Apply local
patch, 2026-09-30. EVAL-SRC-001 v2 exempts ordinary local editing including locally
produced patches, while retaining approval requirements for incorporating
externally obtained third-party code. Local storage is not proof of source approval.

Run holdout-v1-sw-git-apply three times through the implemented q05_stage_aware
runtime with active reviewed-v4/policies-sources-v3. Preserve the command,
expected allow label, both full policies, original neutral context and trusted
fixtures. In particular, preserve the statement that the patch's origin and
approval are unestablished; do not invent locally produced provenance. Report
that limitation when interpreting outcomes. Only source-policy body/version
changes compared with the corresponding local-policy-rerun-v1 calls.

Same Jev/OpenRouter model, .80/.70/.80 gates, total15s budget, strict validation,
same-choice agreement and at most one eligible follow-up. Three primary calls,
at most three extra calls, no repeated transport attempts. Max additional$.05
inside existing$5 budget; starting ledger has4850entries, one historical unknown
at1830 with$.01 reserved. Stop on any new unknown charge. Require clean committed
source/input hashes, starting ledger hash, exclusive ledger lock and fresh output.
Only the previously authorized synthetic case leaves the machine.

Compare all three outcomes and source-scope confidence with the saved previous
run. Audit payload differences and recorded runtime replay without further API
calls. No full pack, general local test suite, fresh controls, deployment,
publication or push. No full-pack or causal accuracy claim; report then stop.
