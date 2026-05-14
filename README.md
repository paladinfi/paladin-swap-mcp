# paladin-swap-mcp

**Open client and API spec for [PaladinFi Swap](https://paladinfi.com/swap/)** — a competitive multi-aggregator swap router for AI agents on Base. This repository contains the public REST and MCP API specification, working code examples, and thin client wrappers. The hosted backend at `swap.paladinfi.com` is proprietary.

> **Routing scope.** PaladinFi Swap queries integrated upstream aggregators (currently 0x and Velora) in parallel and returns whichever delivers the higher post-fee buy amount. We do not represent any returned route as the best available, lowest-cost, or optimal across the broader DeFi market. Phrases like "best execution" are reserved-meaning terms in U.S. securities law and are deliberately not used here.

[![Status](https://img.shields.io/badge/status-live-3fb950)](https://swap.paladinfi.com/health)
[![Chain](https://img.shields.io/badge/chain-Base%208453-2563eb)](https://basescan.org/)
[![Backend](https://img.shields.io/badge/backend-0x%20%2B%20Velora-555)](https://paladinfi.com/swap/)
[![Fee](https://img.shields.io/badge/fee-10%20bps-b64cef)](#fees)
[![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-7c3aed)](https://modelcontextprotocol.io)
[![CI](https://github.com/paladinfi/paladin-swap-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/paladinfi/paladin-swap-mcp/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![paladinfi/paladin-swap-mcp MCP server](https://glama.ai/mcp/servers/paladinfi/paladin-swap-mcp/badges/score.svg)](https://glama.ai/mcp/servers/paladinfi/paladin-swap-mcp)

---

## What is PaladinFi Swap?

A swap router built for **AI agents** that need to execute on-chain swaps. Your agent calls a single tool; the service returns ready-to-execute calldata your wallet signs and submits:

- **Router address** to send the transaction to
- **Calldata** with all routing pre-baked
- **Min buy amount** (slippage protection enforced on-chain)
- **Affiliate fee already injected** — no separate accounting on your side

Agents skip writing aggregator glue, slippage handling, and fee logic. One call, ready bytes.

The Service is **non-custodial**: PaladinFi never holds, signs, or moves user funds. Every transaction is signed and submitted by the user's own wallet (or their agent acting on their behalf).

## Install (MCP)

For [Claude Code](https://claude.com/claude-code) or any MCP-compatible client supporting Streamable-HTTP transport:

```bash
claude mcp add --transport http --scope user paladin-swap https://swap.paladinfi.com/mcp
```

Restart your client. Three tools become available:

- `swap_quote(sellToken, buyToken, sellAmount, taker, chainId?, slippageBps?)` — competitive route across 0x and Velora (highest post-fee buy amount); returns ready-to-execute calldata.
- `trust_check_preview(address, chainId?)` — **sample-fixture preview** of the trust gate. Returns `_real: false`, every factor is `real: false`, and the recommendation is prefixed `sample-` (e.g., `sample-allow`). **Do not use the preview verdict to gate real swaps**, signing, or any production agent decision. For production trust evaluation, POST to `/v1/trust-check` (paid, $0.001 USDC/call via x402) or use the npm plugins `@paladinfi/eliza-plugin-trust` / `@paladinfi/agentkit-actions`.
- `swap_health()` — liveness, fee config, per-source counters, decimals-cache state, last Velora startup-canary verdict, selector-enforcement state.

See [`mcp-tools.json`](mcp-tools.json) for the full tool schemas.
## MCP standards compliance

| Requirement | Status |
|---|---|
| Tool `title` + `annotations` (readOnlyHint, openWorldHint, idempotentHint, destructiveHint) | ✓ since v0.11.74; verify via the MCP `tools/list` method |
| Tool name ≤64 chars | ✓ longest is `trust_check_preview` (19 chars) |
| Streamable HTTP transport | ✓ at `https://swap.paladinfi.com/mcp` |
| Public OpenAPI 3.0 schema | ✓ at [`/openapi.yaml`](https://swap.paladinfi.com/openapi.yaml) |
| Documented rate limits | ✓ at [paladinfi.com/swap](https://paladinfi.com/swap) (5 r/s + burst 30 on `/v1/quote`; 10 r/s + burst 30 on `/mcp`; 5 concurrent connections per IP) |
| x402 paid-tool challenge | ✓ on the `/v1/trust-check` paid endpoint. The MCP `trust_check_preview` tool is gated to sample-fixture output with explicit misuse banners (`_real: false`, `_HUMAN_DO_NOT_USE_AS_REAL_VERDICT`, `sample-` recommendation prefix) — preview by design, never a real verdict |
| Tool descriptions narrow + accurate | ✓ see [`mcp-tools.json`](mcp-tools.json) for exact schemas |

Per [MCP `ToolAnnotations`](https://modelcontextprotocol.io/specification/2025-06-18/server/tools#tool-annotations):

- **`swap_quote`** — title `"Get Swap Quote"`; `readOnlyHint: true` (returns calldata, never mutates server state), `openWorldHint: true` (calls upstream aggregators 0x AllowanceHolder + Velora Augustus v6.2 on Base)
- **`trust_check_preview`** — title `"Token Trust Check (Preview)"`; `readOnlyHint: true`, `idempotentHint: true` (deterministic sample fixture per address), `openWorldHint: true` (paid-mode upstream factor sources cross the process boundary; defensive contract-violation handlers exist for shape drift)
- **`swap_health`** — title `"Swap Service Health"`; `readOnlyHint: true`, `openWorldHint: false` (introspection of our own service state only)


## Agent usage walkthrough

A representative call chain when an MCP-aware agent (e.g., Claude Code) handles a swap intent. Specific tool-call formatting varies by client; the key point is that the swap router returns ready-to-execute calldata so the agent never composes routing logic itself.

**User:** *"Swap 100 USDC for WETH on Base."*

**1. Optional pre-trade trust check** (free, sample-fixture only). Before composing the swap, the agent may call `trust_check_preview` to inspect the buy-token contract's risk shape.

```json
// Tool call
{
  "tool": "trust_check_preview",
  "arguments": {
    "address": "0x4200000000000000000000000000000000000006",
    "chainId": 8453
  }
}
```

```json
// Response (truncated)
{
  "_real": false,
  "_HUMAN_DO_NOT_USE_AS_REAL_VERDICT": "Preview-only fixture. See README.",
  "trust": {
    "recommendation": "sample-allow",
    "_preview": true,
    "factors": [
      { "real": false, "source": "ofac",      "signal": "clear" },
      { "real": false, "source": "goplus",    "signal": "clear" },
      { "real": false, "source": "etherscan", "signal": "verified-contract" }
    ]
  }
}
```

The preview is **sample-fixture only** — agents must check `_real === true` before consuming a verdict. For production gating, call `/v1/trust-check` (paid, $0.001 USDC/call via x402) or use the npm plugins [`@paladinfi/eliza-plugin-trust`](https://www.npmjs.com/package/@paladinfi/eliza-plugin-trust) / [`@paladinfi/agentkit-actions`](https://www.npmjs.com/package/@paladinfi/agentkit-actions).

**2. Competitive quote with calldata.** The agent calls `swap_quote` to get the route + ready-to-execute transaction.

```json
// Tool call
{
  "tool": "swap_quote",
  "arguments": {
    "sellToken": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "buyToken":  "0x4200000000000000000000000000000000000006",
    "sellAmount": "100000000",
    "taker":      "0xUserAgentWallet",
    "chainId":    8453,
    "slippageBps": 50
  }
}
```

```json
// Response (illustrative; values depend on live pool state)
{
  "source":           "velora",
  "chainId":          8453,
  "router":           "0x6a000f20005980200259b80c5102003040001068",
  "calldata":         "0xe3ead59e000000000000000000000000...",
  "buyAmount":        "43200000000000000",
  "minBuyAmount":     "42984000000000000",
  "sellAmount":       "100000000",
  "gas":              "318707",
  "ourFeeBps":        10,
  "ourFeeRecipient":  "0xeA8C33d018760D034384e92D1B2a7cf0338834b4"
}
```

`source` indicates whichever upstream aggregator (0x or Velora) delivered the higher post-fee buy amount for this pair. The 10 bps fee is already injected into the calldata; the `buyAmount` you see is the user's net (post-fee, pre-slippage). `minBuyAmount` reflects the requested 50 bps slippage tolerance.

**3. Sign + submit.** The agent surfaces the transaction shape to the user's wallet for signing — `to=router, data=calldata, value=0` (for ERC20 → ERC20). PaladinFi never sees the signature; the wallet broadcasts the transaction directly to Base.

**4. Confirm.** Slippage is enforced on-chain: the swap reverts if the actual fill would deliver less than `minBuyAmount`. The agent reports the transaction hash; the user's wallet shows the settled buy amount on Base. The 10 bps fee transfers to the published treasury address (`/health`) atomically as part of the same transaction — no second on-chain step.

**Non-custodial end-to-end.** At no point does PaladinFi hold, sign, or move funds. The MCP server returns metadata; the wallet executes. A compromised swap router could only return calldata; even malicious calldata is bounded by the v0.11.71 outer-router + selector + 0x Settler-target allowlist (see Roadmap below) and the user's own wallet-side approval limits.

## Install (REST)

No MCP needed — hit the endpoint directly:

```bash
curl -sS https://swap.paladinfi.com/v1/quote \
  -H 'content-type: application/json' \
  -d '{
    "chainId": 8453,
    "sellToken": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "buyToken":  "0x4200000000000000000000000000000000000006",
    "sellAmount": "5000000",
    "taker": "0xYOUR_AGENT_WALLET"
  }'
```

Full REST spec in [`openapi.yaml`](openapi.yaml).

## Endpoints

| Method | Path | Purpose | Pricing |
|--------|------|---------|---------|
| `GET` | `/health` | Liveness, fee config, per-source counters, decimals-cache state, last Velora canary verdict, selector-enforcement state | Free |
| `POST` | `/v1/quote` | Competitive route quote with calldata — highest post-fee buy amount across 0x and Velora | Free |
| `POST` | `/v1/trust-check` | Live token-contract trust evaluation (OFAC SDN, GoPlus, Etherscan, anomaly heuristics) | $0.001 USDC/call via x402 |
| `POST` | `/v1/trust-check/preview` | Sample-fixture preview of the trust-check response shape (no live data sources evaluated) | Free |
| `POST` | `/mcp` | MCP Streamable-HTTP transport (3 tools — see `mcp-tools.json`) | Free |

## Response shape (abridged)

```json
{
  "source": "velora",
  "chainId": 8453,
  "router": "0x6a000f20005980200259b80c5102003040001068",
  "calldata": "0x...",
  "buyAmount": "2160000000000000",
  "minBuyAmount": "2138000000000000",
  "sellAmount": "5000000",
  "gas": "318707",
  "ourFeeBps": 10,
  "ourFeeRecipient": "0xeA8C33d018760D034384e92D1B2a7cf0338834b4",
  "estimatedOurFeeAmount": "2160000000000",
  "estimatedOurFeeToken": "0x4200000000000000000000000000000000000006"
}
```

`source` is the upstream aggregator that won this quote (`"0x"` or `"velora"`). Submit the transaction as `to=router, data=calldata, value=0` (for ERC20→ERC20) from `taker`.

## Examples

- [`examples/python/quote_and_swap.py`](examples/python/quote_and_swap.py) — Python with web3.py
- [`examples/typescript/quote_and_swap.ts`](examples/typescript/quote_and_swap.ts) — TypeScript with viem

## Fees

A flat **10 basis points (0.1%)** is taken on the **buy token**. The fee is calculated against the *actual* fill amount, not the quoted estimate, so you never pay more than expected even if the pool moves between quote and fill. PaladinFi's 10 bps is taken from the buy-token side via the upstream aggregator's integrator-fee mechanism (0x's `swapFeeBps` / Velora's `partnerFeeBps`), so the `buyAmount` you see in the response already reflects both any upstream protocol fee and our 10 bps — no additional deduction at fill time.

Fees route directly to the PaladinFi treasury — no on-chain receipt step on your side. The fee recipient address is published in `/health` so it's auditable on-chain. The `/v1/quote` endpoint stays free to query, with no per-call charges or spread on top. (`/v1/trust-check` is the only paid endpoint, at $0.001 USDC/call via x402.)

## Supported assets

- **Chain:** Base (8453). Ethereum mainnet, Arbitrum, Optimism, BNB are on the roadmap.
- **Tokens:** Any ERC20 supported by either 0x or Velora on Base. Coverage is the union of both aggregators — canonical pairs (USDC, WETH, cbBTC, USDT, DAI, AERO) are routable on both; long-tail tokens often route on only one of the two.

## Trust Check data sources

The paid `/v1/trust-check` endpoint evaluates a token contract against a defined set of public data sources and returns a single `recommendation: "allow" | "warn" | "block"` verdict alongside per-source breakdown. Sources currently consulted, with verifiability pointers:

| Source | What it screens | Verifiability |
|--------|----------------|---------------|
| **OFAC SDN list** (U.S. Department of the Treasury) | Sanctioned addresses (the contract itself, deployer, and known associated wallets) | List refreshed daily on the hosted backend from the Treasury Sanctions List Service feed at `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.XML`. The address dataset extracted is the union of `Feature[@FeatureTypeID="345"]/FeatureVersion/VersionDetail[@DetailTypeID="1432"]` entries (FeatureTypeID 345 = ETH/EVM addresses; DetailTypeID 1432 = Digital Currency Address Detail). Loaded count as of last verification: **87 ETH addresses** (2026-04-30). The underlying Treasury feed is publicly downloadable so any client can independently re-derive the dataset and verify a positive match. |
| **GoPlus Token Security API** | Honeypot patterns, mint authority, ownership renouncement, transfer pause, blacklist function, anti-whale, hidden owners, slippage modifiers | Queried per-call via `https://api.gopluslabs.io/api/v1/token_security/8453?contract_addresses=<address>`. We normalize the GoPlus response into the `factors` array we surface; the full GoPlus response is publicly queryable so buyers can independently audit any signal. |
| **Etherscan / BaseScan source verification** (via the unified Etherscan v2 API) | Verified-source presence, proxy-pattern detection, contract age, deployer attribution | Queried per-call via `https://api.etherscan.io/v2/api?chainid=8453&module=contract&action=getsourcecode&address=<address>`. Public source code (when verified) is independently inspectable on basescan.org. |
| **Anomaly heuristics** (PaladinFi-internal) | Fresh-deploy detection, low-holder-count signal, proxy-pattern flags | Heuristic logic is part of the proprietary backend; the response includes the per-factor signal so a buyer can reproduce or override the conclusion using the verifiable sources above. |

**Preview vs paid distinction.** `/v1/trust-check/preview` (free) returns a static fixture with `_real: false` markers — none of the live data sources above are queried. `/v1/trust-check` (paid, $0.001 USDC via x402) consults all four. The preview exists so integrators can validate request shape and inspect the response schema without paying; agents must check the top-level `_real` field is `true` before consuming a verdict.

**Request logging.** Per call, PaladinFi retains a request log entry containing timestamp, the queried address, source IP, and billing/rate-limit reference. This is used for revenue accounting, rate-limit enforcement, and abuse detection — not for analytics or resale. PaladinFi does not maintain a separate database of evaluated tokens or buyer query history.

## Roadmap

- [x] 0x Settler routing on Base
- [x] **Highest-of-two routing across 0x and Velora on Base** (v0.11.66+, 2026-05-04)
- [x] MCP Streamable-HTTP transport with `swap_quote`, `swap_health`, and `trust_check_preview` tools
- [x] `/v1/trust-check` paid endpoint via x402 ($0.001 USDC/call)
- [x] Per-source 4-byte calldata selector + Settler-target allowlist (v0.11.71 — defense in depth against router-substitution / dispatcher-hijack attacks)
- [ ] Ethereum mainnet, Arbitrum, BNB, Optimism — planned
- [ ] Permit2-native flow (skip the approve tx) — planned

## Status

Production. The endpoint is live, monitored, and verified end-to-end with on-chain test transactions on Base. See [`/health`](https://swap.paladinfi.com/health) for current fee config, version, and per-source counters.

## What's in this repository

| File / folder | Purpose |
|---------------|---------|
| [`README.md`](README.md) | This file |
| [`LICENSE`](LICENSE) | MIT — covers everything in this repo |
| [`SECURITY.md`](SECURITY.md) | Vulnerability disclosure path + scope |
| [`openapi.yaml`](openapi.yaml) | OpenAPI 3.0 spec for the public REST API |
| [`mcp-tools.json`](mcp-tools.json) | MCP tool schemas |
| [`examples/`](examples) | Working code examples (Python, TypeScript) |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | CI: YAML/JSON syntax + OpenAPI 3.0 schema validation on push/PR |

**Not in this repository:** the hosted backend (proprietary). This repo is the public client surface — install instructions, schemas, and integration code samples.

## Contact

- Email: [dev@paladinfi.com](mailto:dev@paladinfi.com)
- Marketing: [paladinfi.com](https://paladinfi.com)
- API: [swap.paladinfi.com/health](https://swap.paladinfi.com/health)
- Landing: [paladinfi.com/swap/](https://paladinfi.com/swap/)

## Legal

Operated by **Malcontent Games LLC**, doing business as **PaladinFi**, a Michigan limited liability company. The Service routes quotes through third-party aggregators (currently 0x and Velora). You retain custody — your agent signs every transaction. PaladinFi never holds user funds.

Use of the hosted Service is subject to the [PaladinFi Terms of Service](https://paladinfi.com/terms/) and [Privacy Policy](https://paladinfi.com/privacy/).

## License

The contents of this repository are released under the [MIT License](LICENSE). The hosted backend is proprietary and not covered.
