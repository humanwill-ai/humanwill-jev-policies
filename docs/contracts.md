# Contract v1 and offline commands

Foundation reference for `humanwill-policies` **0.1.0.dev0**. The current evaluation extension uses [config/2 and result/2](evaluation-core.md); v1 validators remain available. This document describes the original offline contract. It freezes the offline authoring contract and candidate request/result shapes; it does not implement Jev calls, HTTP endpoints, hooks, authorization verification, or enforcement. Breaking contract changes require a new format identifier rather than silently reinterpreting saved inputs.

## Package and CLI

Python import: `humanwill_policies`. CLI: `humanwill-policies` (also `python -m humanwill_policies`). Supported foundation platforms are Linux and macOS, Python 3.11–3.14. The minimum/current CI matrix is 3.11 and 3.14 on Ubuntu 24.04/macOS 15. Windows support is deferred; the filesystem containment implementation requires POSIX directory descriptors and no-follow opens.

```sh
humanwill-policies init-demo ./demo
humanwill-policies validate ./demo --config ./demo/config.yaml
humanwill-policies preview ./demo --config ./demo/config.yaml --stage prompt --json
humanwill-policies schema request
```

`init-demo` writes a new directory containing three synthetic policies and a content-only configuration. It refuses an existing file, directory, or symlink. `validate` and `preview` read only the selected local files, make no network calls, read no API keys, and write no snapshots unless the user redirects output. `preview` intentionally includes rule text and exact source snapshots; keep its output private for private policy bundles.

Exit 0 means structural/configuration validation succeeded; exit 2 means invalid input or a CLI usage error. `--json` emits successful output to stdout and validation errors to stderr as `{valid:false,error:{code,message,location}}`. Argparse usage errors are ordinary text. YAML parser diagnostics are sanitized instead of echoing source data. A valid bundle does not mean the policies are semantically sound or enforced. `runtime_available` is always false at this milestone.

## Markdown policy format

The root is an explicit directory; default entry point is `policies.md`, replaceable with `--entrypoint`. The entry point must be a collection. Each UTF-8 file starts with `---` on its own line, followed by YAML front matter and a closing `---`. BOM-prefixed files are not accepted. Bodies remain exact Unicode text; bytes, including line endings, are hashed without normalization.

Collection fields: `kind: collection`, `id`, quoted string `version`, and nonempty `includes`. Policy fields: `kind: policy`, `id`, quoted string `version`, `title`, and a nonempty unique `stages` list. A policy needs a non-whitespace body. Unknown fields are rejected. IDs across both collections and policies must be unique and match `[A-Za-z][A-Za-z0-9._-]{0,127}`. No automatic extraction of rules or dependencies from prose occurs.

`includes` are literal `.md` paths relative to the declaring collection. `..` is permitted only when the normalized path stays inside the root. External URLs, absolute paths, fragments, query strings, backslashes, remote references, and non-Markdown paths are rejected. All symlinks beneath the selected root are rejected, including internal aliases; this intentionally tightens the initial design to avoid filesystem race/escape ambiguity. Non-regular files such as FIFOs are rejected without waiting for content. Repeated normalized file paths are deduplicated; active include cycles fail. Ordinary Markdown links never activate files.

Only a restricted YAML subset is accepted: no duplicate keys, anchors/aliases, explicit tags, non-string mapping keys, multiple documents, non-finite numbers, or non-JSON values such as implicit dates. Quote versions, dates, and ambiguous strings; use `true`/`false` for boolean fields. No YAML or Markdown content executes code.

Every policy is independent. Sorted IDs give deterministic output, not priority; an include's position grants no override. Exceptions belong in the rule body. Preview does not detect arbitrary contradictions or determine if a rule is testable.

## Limits

These defaults can be lowered or raised only within the stated ceilings through deployment `limits`. `load_project` applies them before reading the bundle. YAML/JSON structure nesting is separately limited to 24 levels.

| Limit | Default | Hard ceiling |
| --- | ---: | ---: |
| Bytes per Markdown file | 65,536 | 1,048,576 |
| Total unique source bytes | 1,048,576 | 8,388,608 |
| Unique source files | 128 | 512 |
| Policies | 100 | 500 |
| Include depth, root = 0 | 16 | 32 |
| Include entries per collection | 128 | 512 |
| Deployment configuration bytes | 65,536 | 65,536 |
| Request/result canonical JSON bytes | 262,144 | 262,144 |

Limits cause explicit errors, never truncation. Provider token limits and runtime concurrency/deadline settings will be added with the evaluation implementation rather than accepted as nonfunctional configuration now.

## Identity and snapshots

Policy identity is its stable ID; declared version is author-maintained. `Policy.sha256` hashes the exact source bytes (front matter plus body). The `humanwill.bundle/1` digest hashes canonical JSON containing compiler/format identity, entrypoint, and source paths/hashes sorted by path. It is independent of the absolute installation location. A source edit, rename, version change, or include-order edit changes provenance and the bundle digest even where effective rules are unchanged. A bundle digest is an integrity fingerprint, not a signature or proof of authorship.

`Bundle`, `Policy`, `Source`, and `Configuration` are immutable values. `snapshot()` and `to_dict()` return detached copies. Preview includes exact source text so a later evaluator can retain the same policy evidence. No snapshot import API is implemented yet. The effective configuration digest binds normalized settings/defaults to the bundle digest, excluding absolute configuration paths. It includes credential *environment variable names*, never credential values.

## Deployment configuration

`format: humanwill.config/1`, `metadata`, and `policies` are required. The [current packaged demo config](../src/humanwill_policies/demo/config.yaml) now uses config/2; see the evaluation-core migration notes. Every policy in the loaded bundle needs an explicit binding; missing or unknown IDs are errors. With no `--config`, only authoring structure is validated and preview marks all rules `unconfigured`.

Binding fields:

- `enabled` is required. Defaults for other fields: `mode: monitor`, `on_error: block`, `requires_metadata: []`, `predicates: []`.
- `mode` is `monitor` or `enforce`; `on_error` is `block` or `allow`. These are validated future-runtime instructions, not actions performed by preview. Unsupported `review` is rejected.
- `requires_metadata` explicitly names fields in the `identity`, `documents`, `destination`, `environment`, or `authorization` namespace, for example `identity.groups`. `predicates` declare `exists`, `equals`, `contains`, or `in`; every field must also be declared required. Predicates are not executed at this milestone. Their future combination with semantic applicability belongs to the evaluator, not an automatic authorization inferred from Markdown.
- Enforcing bindings require `evaluation_profile` with ID, exact model, dataset digest, and minimum confidence in [0,1], plus matching `provider` settings. This checks provenance fields, not whether calibration actually passed. Do not fabricate a calibration profile to enable production enforcement.

`metadata.enabled` is explicit. Optional source namespaces map to `{enabled, source}`. No lookups or trust verification happen during validation. Enabled enforcing rules with required facts reject disabled metadata/sources. Monitoring rules retain warnings, and explicitly disabled rules remain visible. Omitting a source never invents an identity or group. This feature does not configure connector authentication; there is no server yet.

Optional `provider` accepts only `transport: openrouter|typesafe`, `model`, and `api_key_env` (an environment variable name). Raw API keys and custom endpoint URLs are rejected. Credentials are never read in offline commands. Runtime destination authorization remains future work.

Optional `connectors` declare intended stage bindings. Unsupported assessment stages are rejected; enforced CLI prompt bindings are rejected as assessment-only. These checks encode documented contracts, not validated host implementation. See [compatibility](compatibility.md). Unsupported/unimplemented settings are rejected instead of silently ignored.

## Candidate evaluation wire contracts

Export the packaged JSON Schemas with `schema policy|collection|config|request|result`. The Python `validate_contract` adds finite-value, depth/byte-limit, content-ID, coverage, and timestamp checks. It performs no remote schema resolution. The three [request fixtures](../tests/fixtures/request-content.json) and [synthetic result](../tests/fixtures/result-example.json) illustrate shapes; they are not evaluation results.

`humanwill.request/1` contains `request_id`, `stage`, `content`, and `coverage`; metadata is optional. Content is text (optional role) or a proposed tool name/arguments. Tool-action events require an action item. Content IDs are unique, `coverage.inspected` matches supplied IDs, and `complete:true` cannot coexist with omissions. Completeness describes the declared event scope, not universal coverage. No policy selection, override, threshold, or trust flag is accepted from the requester.

Metadata entries identify field, value, source, subject/document reference, and timezone-bearing observation timestamp. A schema-valid entry is an assertion, not a trusted fact: a future authenticated connector/source verifier must establish provenance and freshness before a decision uses it. Fields such as `trusted:true` are rejected.

`humanwill.result/1` records decision (`allow`, `block`, or `evaluation_error`), per-policy judgments/reasons, bundle/configuration digests, coverage, evaluator identity or null, duration, errors, and requested enforcement. `enforcement.actual` is limited to `unconfirmed` or `not_requested`; an evaluator cannot claim the host executed its answer. Decision aggregation, probability evidence, and observed host outcomes need the next implementation milestone and versioned additions if contracts change. No endpoint currently accepts these payloads.
