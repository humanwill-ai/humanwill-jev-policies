# Project disclosure and preparation example

This versioned policy illustrates a company rule, not an automatically enabled
product safeguard. Copy and adapt it to your organization's intended scope.
It permits ordinary local coding and code review, while preparation directed toward
onward publication requires approval for the destination and complete operation.

The service needs trusted facts for `destination.coding_route_approved` and
`destination.onward_approved` when using the scoped-predicate configuration.
The latter must cover preparation and disclosure, not just permission to connect
to a repository. A user assertion is not authorization. No production resolver or
approval-request UI ships; absent required facts remain evaluation errors. Do not
enable enforcement until those facts and the fallback behavior are configured and
tested. Monitoring defaults allow assessment without policy blocking.

See [metadata setup](../../docs/optional-metadata.md),
[policy authoring](../../docs/policy-authoring.md), and the
[targeted v3/v4 comparison](../../docs/preparation-policy-v1-report.md).
