---
kind: collection
id: example-company-policies
version: "0.1"
includes:
  - content.md
  - data/secrets.md
  - engineering/policies.md
---

# Example company policies

Authoring example for the implemented v1 folder format. These are synthetic rules,
not approved HumanWill or customer policies. The offline loader validates their
structure; semantic evaluation and enforcement are not implemented.
Only the explicit `includes` list activates policies; prose here is descriptive.

`EXAMPLE-CONTENT-001` works without metadata. The other examples require trusted
facts for complete evaluation; see the [optional metadata design](../../docs/optional-metadata.md)
for a content-only deployment that explicitly disables those dependent policies.
