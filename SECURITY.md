# Security policy

## Report a vulnerability privately

Email **[sergio@humanwill.ai](mailto:sergio@humanwill.ai)**, the HumanWill maintainer's
designated security-reporting address. Do not put sensitive vulnerability details
in a public issue or pull request.

Include the affected version/commit, connector and host version, relevant
configuration with secrets removed, impact, and a minimal synthetic reproduction.
Do not send credentials, customer/company policies, proprietary source, personal
data or raw account/session logs. If sensitive detail is essential, arrange its
handling with the maintainer before sending it. We do not promise a response-time
SLA or a bug bounty.

## Supported scope

No public version has been released yet. Security reports should target the current
`0.1.0a1` candidate or current development source. The first release is an
experimental developer preview; no long-term support or backport commitment is
made. Include the exact version because policy/configuration and host contracts
change independently.

Potential issues include authorization or trusted-metadata bypass, unauthorized
content egress, secret/raw-content logging, parser/path escape, or a supported
connector failing to honor a decision contrary to its documented contract.

Known boundaries remain explicit: semantic judgments can be wrong or uncertain,
monitor mode permits assessed events, configured error fallback may allow, and
hosts may skip disabled hooks or continue after hook timeouts. Prompt checks do
not cover every later action or unseen input. See [security considerations](docs/operations.md#security-considerations)
and [tested compatibility](docs/compatibility.md). A bypass beyond those documented
boundaries is still worth reporting privately. These limitations do not dismiss
new implementation vulnerabilities.

## Release handling

Maintainers reproduce reports using controlled fixtures, assess affected versions
and coordinate fixes/disclosure with the reporter where possible. A local test or
scanner result is evidence with limits, not a guarantee that vulnerabilities are
absent. Publication and visibility changes require review of code, history,
artifacts and existing GitHub logs as well as the intended release files.
