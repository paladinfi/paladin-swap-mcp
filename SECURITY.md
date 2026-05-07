# Security Policy

## Reporting a Vulnerability

If you discover a security issue in `paladin-swap-mcp` or any of the hosted endpoints in scope below, please email **[dev@paladinfi.com](mailto:dev@paladinfi.com)** with:

- A clear description of the issue + reproduction steps
- The affected endpoint, MCP tool, or call path
- Any logs, error responses, or proof-of-concept
- Whether the issue has been disclosed publicly elsewhere

We aim to acknowledge within **5 business days** and provide a triage update within **7 days**. Please do **not** open a public Issue for security-relevant findings.

PaladinFi operates with a small engineering team. We do not currently run a bug bounty.

## Scope

In scope:

- The MCP server at `swap.paladinfi.com/mcp` (3 tools: `swap_quote`, `swap_health`, `trust_check_preview`)
- The REST API endpoints at `swap.paladinfi.com/v1/quote`, `/v1/trust-check`, and `/v1/trust-check/preview`
- The OpenAPI schema (`openapi.yaml`) and MCP tool list (`mcp-tools.json`) in this repository
- The example integration code under [`examples/`](examples)

Out of scope:

- Issues in upstream aggregators (0x, Velora) — please report to those projects directly
- Customer-specific OFAC / GoPlus / Etherscan data quality — these are external feeds; correctness disputes go to the source provider
- Third-party MCP clients consuming our server
- Issues that require a malicious customer to opt themselves into harm (e.g., disabling client-side validation in a fork of our published plugins)

## Disclosure

After a fix ships, we publish a CHANGELOG entry describing the issue, the fix, and the affected versions. If you reported the issue, we credit you by handle (with your permission) in the CHANGELOG.
