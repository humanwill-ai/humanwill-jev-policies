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

Draft authoring example for the proposed v0.1 format. These are synthetic rules,
not approved HumanWill or customer policies. No loader is implemented yet.
Only the explicit `includes` list activates policies; prose here is descriptive.

`EXAMPLE-CONTENT-001` works without metadata. The other examples require trusted
facts for complete evaluation; see the [optional metadata design](../../docs/optional-metadata.md)
for a content-only deployment that explicitly disables those dependent policies.
