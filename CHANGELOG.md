# Changelog

Public-API-affecting changes to `paladin-swap-mcp` and the hosted backend at `swap.paladinfi.com`. Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Versions are the unified server cohort; the same number is reported by `swap.paladinfi.com/health` and used in the apex homepage badge at <https://paladinfi.com>. Prior to v0.11.66 the public surface evolved without a dedicated public-repo changelog; the entries below cover from v0.11.66 forward.

---

## v0.11.74 — 2026-05-12

### Added

- **MCP tool annotations** on all three tools per [MCP spec `ToolAnnotations`](https://modelcontextprotocol.io/specification/2025-03-26/server/tools):
  - `swap_quote`: `title: "Get Swap Quote"`, `readOnlyHint: true`, `destructiveHint: false`, `idempotentHint: false` (quote responses move with on-chain prices + aggregator routing), `openWorldHint: true` (calls 0x + Velora upstream).
  - `trust_check_preview`: `title: "Token Trust Check (Preview)"`, `readOnlyHint: true`, `destructiveHint: false`, `idempotentHint: true` (fixture data is deterministic), `openWorldHint: true` (crosses a process boundary to upstream whose response shape we don't own; defensive contract-violation handlers in the server confirm this).
  - `swap_health`: `title: "Swap Service Health"`, `readOnlyHint: true`, `destructiveHint: false`, `idempotentHint: false`, `openWorldHint: false` (introspection of our own service state, not external).

### Changed

- **FastMCP `instructions` string** corrected from the stale "0x Settler today; 1inch and Odos planned" copy to current state: "0x AllowanceHolder dispatching to Settler + Velora Augustus v6.2 on Base". Matches the v0.11.71 dispatcher-disambiguation finding and the v0.11.66 Velora addition.
- **Preview-endpoint fixture** (`/v1/trust-check/preview`) `trust.version` bumped from `1.0` to `1.1` to match the v0.11.73 contract. Drift fix.
- **Backend `/health` version** bumped to match the cohort (was lagging at 0.11.73 from the prior ship).

### Notes

- This release closes the "missing tool annotations" rejection cause for the Anthropic Connectors Directory submission process; per Anthropic submission docs, missing annotations are the most common rejection cause.
- No behavioral change to any tool body. Patch is decorator metadata + 3 string updates.

---

## v0.11.73 — 2026-05-07

### Changed

- **Trust-block contract**: closes a silent-allow vector on `/v1/trust-check`. Per-source raise → factor included in response with `signal: "unreachable"`, `real: false`. All-sources raise → verdict forced to `warn` (not silently `allow`). OFAC SDN hit preserves the highest-priority `block` override.
- `TRUST_BLOCK_VERSION` bumped `1.0 → 1.1` (paid endpoint; preview followed in v0.11.74).
- Public `details` field on unreachable factors is the static phrase `"source unreachable"` — never `str(err)`, closing a previously-possible upstream-key leak via exception strings. Full `str(err)` is preserved server-side for ops triage.

### Removed

- Stale "lookalike check" references in apex pages (index, /trust-check, /terms). The lookalike-detector was deprecated in v0.11.62 but copy lagged.

---

## v0.11.71 — 2026-04-30

### Added

- **Calldata selector allowlist (defense-in-depth)** on every quote response:
  - Outer router whitelist per source (existing; preserved).
  - Outer selector allowlist: 0x = `0x2213bc0b` (`AllowanceHolder.exec`) only; Velora = the 11 swap selectors of AugustusSwapper v6.2.
  - For 0x `exec`: decode + validate the inner `target` argument equals the canonical 0x Settler address `0x7747f8d2a76bd6345cc29622a946a929647f2359`. Without this, the outer selector check is cosmetic because `AllowanceHolder.exec` is a `target.call(data)` dispatcher.
- **Hard deny-list** (7 selectors, unconditional even in warn-only mode): Permit2 `permitTransferFrom`/`permit` single+batch, AllowanceTransfer `transferFrom`, ERC-20 `transferFrom`/`transfer`/`approve`.
- `/health` exposes the `selector_enforcement` block surfacing per-source allowlist sizes, the deny-list, and the mode (`enforce` or `warn-only`).

### Process

- First v0.11.x patch to use the "treat as audit, not code review" framing for the security reviewer in the 3-adversary review pass. That framing caught the dispatcher-gap (layer 3) that 1-reviewer-precedent passes missed across 5 prior versions.

---

## v0.11.66 — late April 2026

### Added

- **Velora Delta integrated as second quote source** on `/v1/quote`. Best-of-N routing across 0x and Velora; the higher post-fee `buyAmount` wins, with `minBuyAmount` as second-key tiebreak and a final deterministic `0x`-prefer tiebreaker.
- Per-source kill switches via env (`SOURCE_VELORA_ENABLED`, `SOURCE_0X_ENABLED`).
- `/health` per-source counters (`ok`, `err`, `enabled`, `avg_latency_ms`).
- PII sanitization in error responses — never leak upstream URLs, request bodies, or taker addresses.
- Per-source router-allowlist and priceRoute token-invariant check (closes a router-substitution attack on the Velora 2-step prices→transactions flow).

### Security

- Module-level `ThreadPoolExecutor(max_workers=4)` with `atexit.register(shutdown)` + `as_completed(timeout=12s)` wall-clock cap so a single misbehaving upstream cannot block the quote pipeline.

---

## Prior versions

Versions prior to v0.11.66 are not documented in this CHANGELOG. The `paladin-swap-mcp` repo's [README](README.md) Roadmap section names the major capabilities that landed across the v0.11.x series.

Health-endpoint version, fee bps, supported chains, and selector-enforcement state are all introspectable live: <https://swap.paladinfi.com/health>.
