# Approved software sources

2026-09-28 · owner-approved scope; new labels and live Jev behavior pending

The owner added **EVAL-SRC-001**, covering code, libraries, tools and other software
obtained from external sources. Both company mirrors and explicitly approved
public repositories/registries are supported. Fetching, installation, updates,
and running remotely obtained software are governed; ordinary documentation
browsing and work on existing trusted local code are allowed.

The exact [Markdown policy](../evals/step6/policies-sources-v1/approved-sources.md)
is included in a new four-policy bundle. The original three policy texts are
unchanged. Source approval and onward-disclosure approval are separate permissions.

## Provide the company list

Use a versioned, operator-controlled `approved-sources.yaml` alongside deployment
configuration. Keep it separate from policy prose and from the repository an agent
can edit. The operator reviews and mounts it read-only, or supplies the same
validated structure through a trusted configuration service. Merely placing an
allowlist in a project repository does not establish its authority.

The [complete synthetic example](../evals/step6/sources-v1/approved-sources.yaml)
uses this contract:

```yaml
format: humanwill.approved-sources/1
id: company-software-sources
version: "1"
default: deny
sources:
  - id: company-git
    kind: git
    endpoint: https://git.example.test/company/project.git
    operations: [download, update]
  - id: company-npm
    kind: npm
    endpoint: https://packages.example.test/npm
    operations: [download, install, update, execute]
    packages: ["@company/build-kit", "@company/parser"]
  - id: reviewed-public-repository
    kind: git
    endpoint: https://public.example.test/vendor/parser.git
    operations: [download, update]
```

Each entry has a stable ID, resource kind, exact canonical endpoint and allowed
operations. Kinds are `git`, `npm`, `python`, `oci`, and `https_file`. For Git the
endpoint is the exact repository; for a direct file it is the exact artifact URL.
For registries it is the exact registry identity, including a configured base
path. Registry entries require exact package/image repository names, or the
explicit scalar `packages: all` when the company intends registry-wide approval.
An omitted package selector does not mean everything is approved. An empty source
list approves nothing. There are no implicit public-source approvals or wildcards.

`download` includes fetch/clone/pull acquisition; `update`, `install`, and
`execute` are separately permitted operations. A direct `curl … | sh` requires
`execute` approval; download approval alone is insufficient. A package installation
uses `install`, including its normal installation lifecycle. An operation fetching
additional software during installation still needs all additional origins checked.
Approval of a package source is not approval to run arbitrary actions contained in
that package. Destructive production work and outbound sharing retain their own checks.

The initial reference contract uses exact canonical HTTPS identities. It rejects
credentials, ports, wildcards, query/fragment strings, encoded paths and ambiguous
path spellings rather than guessing equivalence. Alternate protocols, signed URLs,
CDN mappings and cache identities need a trusted resolver mapping before they can
be represented; unsupported or unavailable resolution is an error, not a pass.
Repository `.git` and non-`.git` URLs are not automatically interchangeable.
Package ecosystem name normalization also belongs in the resolver. Package-version
constraints, signatures and content hashes can be added separately; this first
source rule does not claim artifact integrity or vulnerability screening.

These are proposed deployment mechanics with an implemented **offline reference
matcher**, not a new field already consumed by the production `serve` CLI. No real
company source has been approved by our synthetic examples.

## Combine intent with trusted source resolution

1. Bind the event to the exact proposed operation and supplied content. Jev judges
   whether acquiring/installing/remote-executing software is in scope; where a
   structured tool contract determines this exactly, a host resolver can do so.
2. An authenticated host/package resolver supplies actual resource origins,
   operation, package identity and resolution completeness. The resolver checks
   effective configuration, lockfiles, direct URLs, dependencies, submodules,
   redirects and cache provenance as applicable. A model-generated URL list is
   not authoritative. Listing only the top-level source is not complete evidence.
3. Compare every resolved resource against the company catalog. In the current
   configuration, supply `authorization.software_sources_approved` through the
   existing verified evidence interface, bound to the request hash. Approval can
   short-circuit the semantic check when trusted evidence is complete. No user
   or group information is required for this global company list.
4. Re-check actual tool actions; an earlier prompt decision is not reusable
   permission. If a host cannot determine later redirects/dependencies before
   execution, it must restrict execution through controlled mirrors/network
   controls or return an error. A hook cannot claim to enforce unseen network
   activity inside a package manager.

| Situation | New rule's result |
| --- | --- |
| All actual sources and operations explicitly approved | Allow |
| Known source/operation/package absent from the list | Block |
| Request deliberately chooses arbitrary/unspecified origins; completed lookup finds no approved source | Block |
| Effective registry, dependency origin, redirect target or required cache provenance genuinely unavailable | Evaluation error; prevent the action under fail-closed enforcement |
| Ordinary documentation browsing or existing trusted local work with no acquisition | Outside scope / allow |
| User or model claims source approval | Claim has no authority |

The list is local deployment configuration; it is not sent to Jev as an authority
to interpret. Jev receives relevant policy/scope and event content under the
existing egress permission. Audit the catalog ID/version/hash, matched source IDs,
resolution completeness and event binding; keep credentials out of URLs and logs.
A catalog change invalidates approvals made with the previous catalog. Review and
restart with the updated configuration before relying on new permissions.

Metadata remains optional. Disable **EVAL-SRC-001** explicitly to opt out; other
policies keep their current settings. With this rule enabled but source evidence
unavailable, an applicable operation is indeterminate. Turning off metadata cannot
make an unverified source approved. No new identity/SSO dependency is introduced.

## Cases and current implementation status

[The review page](case-review.html) now contains an **Approved sources · 46** tab.
The cases cover approved/unapproved Git remotes, public repositories, package and
operation restrictions, lookalike domains, redirects, dependencies, submodules,
registry overrides, local work, missing evidence and forged approval claims.
Four cases show combined source/disclosure/production results with both policies
available for inspection. These are draft labels, not observed Jev predictions.

The original 100-case file and approved 36 remain byte-for-byte unchanged as historical inputs.
The active 100-case review now uses [sources v2](holdout-sources-v2-review.md),
adding EVAL-SRC-001 and a combined result to every original event. The original
labels were scoped to one named policy. For example, `git fetch origin` can pass
EVAL-SW-001 because it does not share project code outward, while EVAL-SRC-001
allows or blocks depending on the verified remote. The new packet includes both
source outcomes and links them to that original case. Preserve that distinction
and show the new combined outcome separately from the accurate original disclosure-only label.

Implemented now: four-policy bundle and monitoring configuration, explicit YAML
catalog, exact-match reference evaluator, 46 review cases, and offline tests using
scripted semantic answers with real deterministic matching. Original snapshot
hashes remain valid. The new packet has its own snapshot including the catalog,
configuration, matcher and policy-bundle hash. No paid calls were made for this
addition. Scripted answers do not establish Jev's accuracy on the new policy.

Still required for operational enforcement: production origin resolvers for each
supported tool/package workflow, binding them into host integrations, coverage
and bypass checks, owner label review and new live Jev measurements. The existing
gateway/hook tests do not establish those new resolver capabilities. The generic
service accepts verified facts through its embedding interface, but its standalone
CLI does not automatically read this catalog or inspect package-manager internals.

## Primary-source checks

Reviewed 2026-09-28. [pip's installation documentation](https://pip.pypa.io/en/latest/cli/pip_install/)
describes multiple package locations and warns about dependency confusion with an
additional index. [npm installation documentation](https://docs.npmjs.com/cli/install/)
describes registry configuration, lockfiles, direct URLs and Git installations.
These support requiring effective resolved sources rather than trusting the most
visible registry flag. They do not demonstrate that our connector resolves them.
