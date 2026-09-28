# Plan for more dependable policy enforcement

2026-09-28 · proposal for discussion; no implementation, model calls or threshold
changes authorized by this document itself

## What the evidence actually says

The latest [offline replay](threshold-replay-v1-report.md) gives the asymmetric
candidate 101/102 matching generic outcomes and 67/73 advanced outcomes. It uses
old answers; the deployed defaults remain unchanged. The latest actual context
run had 225/227 correct raw scope choices. Most remaining disagreements are
confidence rejections; one is a confident command-interpretation error. One raw
scope error is contained by the uncertainty gate and has the correct operational
outcome. These categories need different remedies.

The sole generic candidate mismatch is an unapproved Git fetch: correct
`applicable` at 0.66 becomes an error rather than a conclusive policy block.
Fail-closed already prevents the operation. Fixing this improves determinacy and
explanation, not the observed number of prevented violations.

There is little headroom for a large improvement in this selected pack's generic
match count. A useful product improvement means fewer avoidable interruptions,
reliable decisions across new workflows and company policy wording, defensible
action coverage, and acceptable runtime latency. Do not improve the headline by
dropping more failures, accepting missing authorization, or rewriting labels.

## Recommended work, in order

### 1. Establish a small but better development and validation set

Retain the complete 175-case regression pack and its 102/73 reporting split.
Create a proposed 48-case extension, with 24 development and 24 reserved validation
cases split by workflow family before model runs. This is an initial learning
tranche, not sufficient per-policy statistical qualification. Expand only where
the results or final confidence targets require it.

Prioritize structured production operations, source acquisition, and mixed
requests; include disclosure/document cases as composition controls. Production
currently has only one generic example. Include paired scenarios in development
where changing one meaningful fact should change the decision:

- Discuss an acquisition versus ask the agent to perform it.
- Acquire from an approved source versus an unapproved source.
- Request a destructive production operation with and without verified permission.
- Use a genuine tool-supported preview versus execute the operation.
- Supply trustworthy evidence versus omit it, spoof it, or bind it to other arguments.
- Combine allowed discussion with an actual prohibited action in the same event.

Keep missing script contents genuinely missing. Do not add explanations that give
away expected answers. Never use the evaluation label as input context. Keep
families together when splitting: a minimally edited twin is not independent
held-out evidence. The owner reviews new labels, as with the previous pack.

Also propose two additional company-authored wording variants per policy that
preserve its intent. Have the owner confirm equivalence and reserve one variant
from tuning. This tests reusable policy interpretation rather than memorizing a
single hand-tuned policy formulation.

Deliverable: concise review packet, explicit workflow split, and frozen outcome
and metric definitions. Policies and historical labels remain unchanged.

### 2. Make the semantic task clearer, then test the hypothesis

For `scoped_predicates`, source inspection shows that Jev receives the configured
stage-specific scope text instead of the Markdown body. The current rule and its
long scope questions are maintained separately. This creates a potential drift
and portability problem; it does not prove the present questions caused failures.

Compare the current questions with at most two deliberately different candidates:

1. **A shorter single question**, built from explicit policy sections: governed
   behavior, exceptions, stage and genuinely unavailable information. Keep
   authorization outside the semantic decision. Avoid repeated instructions and
   shell-specific examples added solely to repair known failures.
2. **Two narrow judgments, only where justified**, separating the presence of a
   governed operation from the relevant discussion/preview exception. Combine
   them explicitly in code; uncertainty remains uncertainty. A harmless passage
   must not exempt a separate prohibited action in a compound request. Batch the
   questions where possible; measure the extra tokens and latency.

Start with the approved-source policy, then check portability to disclosure and
production rules. Do not ask Jev to return a higher confidence or invent hidden
script behavior. Preserve evaluator instruction boundaries; do not restore the
removed standalone injection policy.

Show the effective question next to its source policy in authoring/review. For
the first experiment, keep mappings explicit and reviewed. If the experiment
succeeds, design a small versioned authoring template so companies maintain policy
intent in one place. Arbitrary Markdown must not be silently rewritten into an
unreviewed enforcement rule.

Deliverable: measured question comparison, exact policy-to-question traceability,
and one selected candidate—or a recorded finding that neither improves decisions.

### 3. Add a bounded, optional path for verified tool operations

This is the strongest engineering hypothesis for more dependable action decisions:
when the executor can establish the operation exactly, asking a model to rediscover
it adds avoidable uncertainty. Existing positive-authorization short circuits
already avoid some calls. Extend this principle carefully to verified operation
scope, without trying to build a general shell security scanner.

Start with two operator-registered structured tool contracts: one source-acquisition
operation and one production-action/preview operation. Their supported executors
must provide event-bound operation type, actual resource/destination and execution
mode from validated arguments and a known implementation. Approval remains a
separate trusted fact. A tool name, model-written description, `dry_run: true`
claim, or arbitrary request field is not proof of behavior.

Examples: a controlled repository-fetch tool whose executor resolves the actual
remote, and a controlled production-delete tool with distinct preview/execute
operations. Verify behavior through real adapter/executor tests. Do not assume
arbitrary `shell` calls expose these contracts. The current raw `git fetch origin`
case stays on the semantic path unless a supported adapter actually establishes
its effects; merely knowing the remote URL is insufficient to prove applicability.

When verified scope and required permission facts suffice, decide deterministically
and record their provenance. Check every active policy; one approved operation
cannot exempt another effect. Unknown scope still uses Jev where appropriate or
the existing uncertainty behavior. Unsupported tools are never silently allowed.

Metadata stays optional and independently switchable. Content-only policy checks
continue to work. Missing evidence for metadata-dependent rules retains its current
error behavior. Do not make identity/SSO a prerequisite for every deployment.
All required connector families remain in scope, but advertise verified-operation
support only for the executor/connector combinations actually tested.

Deliverable: a small verified-operation contract and two working adapters, with
measured reduction in avoidable model calls and ambiguous action decisions. The
ordinary Jev path and supported coverage limits remain visible.

### 4. Measure changes separately, using Jev

Use the planned three complete original-pack repetitions to establish baseline
stability. Score both 0.80/0.80/0.80 and 0.80/0.70/0.80 gates on each repetition's
same saved answers, rather than buying duplicate calls for threshold comparisons.
Report disagreement across repeats, not just their average accuracy.

Freeze each subsequent experiment before calls. Compare question candidates on
development data and the retained regressions at fixed thresholds; compare the
verified-operation path separately. Only then assess their combination. Keep all
results, randomize/interleave model-comparison order, and distinguish fresh
answers from offline decision replays. Use the reserved workflows/wording only
after selecting a candidate; they become development data if tuned against.

Primary measures: false blocks, missed violations, fully specified-case errors,
expected unknowns incorrectly allowed, and event/policy stability. Also measure
provider calls avoided, actual host-added p50/p95/p99 latency, and total cost.
The prior 2.58-second evaluator p95 still exceeds the existing target; fewer calls
or shorter questions are hypotheses for improvement, not a latency guarantee.

Proposed development screening criterion: at least halve avoidable indeterminate
decisions on the new fully specified development cases, without observed new
misses or unknown-to-allow regressions. Report raw counts if the baseline is too
small for that relative target to be informative. Do not substitute this screen
for the owner's existing per-policy accuracy confidence bounds, error, latency
and cost release gates. Repeated trials do not create new independent cases.

Keep Jev as the selected backend. Gemini comparison, model replacement, automatic
fallback and majority voting are not required for this work. Only investigate a
second pass or other judge if a measured, material gap remains after these changes;
account for its correlated errors, host deadline and extra egress/cost.

### 5. Validate real enforcement and make a release decision

For the selected profile, exercise allowed and denied supported operations through
the existing gateways/hooks and the actual executor. Confirm denied side effects
do not occur, arguments cannot change between assessment and execution, and
timeouts/disabled hooks retain their documented limitations. Keep assessment-only
interfaces labeled as such. Test source resolution against the real supported
origins; synthetic catalog fixtures are insufficient proof of production coverage.

Adopt a configuration only with a versioned evidence report and rollback path.
An honest bounded preview can retain advanced-command limitations; production
claims need the original release gates and representative customer evidence.

## Immediate next increment and constraints

Begin by drafting the 48 new scenarios and the two source-policy question
candidates, plus the proposed contracts for two structured tools. This is offline
and gives the owner concrete material to review before changing runtime behavior.
Then freeze the baseline stability protocol and run the controlled experiments.
Do not spend more runs merely chasing a perfect result on the original pack.

No new calls or spending were made to prepare this plan. Future synthetic calls
remain subject to the existing cumulative $5 ledger; $0.078278768 is recorded so
far. Estimate and reserve each experiment before sending, stop at the cap, and
retain all attempts. Use local checks and batch pushes in view of the reported
GitHub Actions quota constraint. No public publication, customer-data disclosure
or deployment follows from this proposal.
