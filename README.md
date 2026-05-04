# paladin-swap-mcp

**Open client and API spec for [PaladinFi Swap](https://paladinfi.com/swap/)** — a competitive multi-aggregator swap router for AI agents on Base. This repository contains the public REST and MCP API specification, working code examples, and thin client wrappers. The hosted backend at `swap.paladinfi.com` is proprietary.

> **Routing scope.** PaladinFi Swap queries a limited set of integrated upstream aggregators (currently 0x and Velora; 1inch and Odos planned) in parallel and returns whichever delivers the higher post-fee buy amount. We do not represent any returned route as the best available, lowest-cost, or optimal across the broader DeFi market. Phrases like "best execution" are reserved-meaning terms in U.S. securities law and are deliberately not used here.

[![Status](https://img.shields.io/badge/status-live-3fb950)](https://swap.paladinfi.com/health)
[![Chain](https://img.shields.io/badge/chain-Base%208453-2563eb)](https://basescan.org/)
[![Backend](https://img.shields.io/badge/backend-0x%20%2B%20Velora%20best--of--N-555)](https://paladinfi.com/swap/)
[![Fee](https://img.shields.io/badge/fee-10%20bps-b64cef)](#fees)
[![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-7c3aed)](https://modelcontextprotocol.io)
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

- `swap_quote(sellToken, buyToken, sellAmount, taker, chainId?, slippageBps?)` — best-of-N quote across 0x + Velora; returns ready-to-execute calldata.
- `trust_check_preview(address, chainId?)` — sample-fixture preview of token-contract trust evaluation. Free / non-paid; returns `_real: false` to clearly mark as a preview. Real evaluations available via `@paladinfi/eliza-plugin-trust` or `@paladinfi/agentkit-actions` (paid via x402, $0.001/call).
- `swap_health()` — liveness + per-source counters for the routing service.

See [`mcp-tools.json`](mcp-tools.json) for the full tool schemas.

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

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness + fee config + per-source counters |
| `POST` | `/v1/quote` | Best-of-N route quote with calldata (0x + Velora today) |
| `POST` | `/v1/trust-check/preview` | Free sample-fixture preview of trust evaluation |
| `POST` | `/mcp` | MCP Streamable-HTTP transport |

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

A flat **10 basis points (0.1%)** is taken on the **buy token**. The fee is calculated against the *actual* fill amount, not the quoted estimate, so you never pay more than expected even if the pool moves between quote and fill.

Fees route directly to the PaladinFi treasury — no on-chain receipt step on your side. The fee recipient address is published in `/health` so it's auditable on-chain. The service stays free to query, with no per-call charges or spread on top.

## Supported assets

- **Chain:** Base (8453). Ethereum mainnet, Arbitrum, Optimism, BNB are on the roadmap.
- **Tokens:** Any ERC20 supported by either 0x or Velora on Base. Coverage is the union of both aggregators — canonical pairs (USDC, WETH, cbBTC, USDT, DAI, AERO) are routable on both; long-tail tokens often route on only one of the two.

## Roadmap

- [x] 0x Settler routing on Base
- [x] **Best-of-N routing across 0x and Velora on Base** (v0.11.66+, 2026-05-04)
- [x] MCP Streamable-HTTP transport
- [x] `trust_check_preview` MCP tool (v0.11.65)
- [ ] 1inch + Odos as additional routing sources — planned
- [ ] Ethereum mainnet, Arbitrum, BNB, Optimism — planned
- [ ] Permit2-native flow (skip the approve tx) — planned

## Status

Production. The endpoint is live, monitored, and verified end-to-end with on-chain test transactions on Base. See [`/health`](https://swap.paladinfi.com/health) for current fee config, version, and per-source counters.

## What's in this repository

| File / folder | Purpose |
|---------------|---------|
| [`README.md`](README.md) | This file |
| [`LICENSE`](LICENSE) | MIT — covers everything in this repo |
| [`openapi.yaml`](openapi.yaml) | OpenAPI 3.0 spec for the public REST API |
| [`mcp-tools.json`](mcp-tools.json) | MCP tool schemas |
| [`examples/`](examples) | Working code examples (Python, TypeScript) |

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
