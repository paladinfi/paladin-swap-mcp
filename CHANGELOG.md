# Changelog

Public-API-affecting changes to `paladin-swap-mcp` and the hosted backend at `swap.paladinfi.com`. Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Versions are the unified server cohort; the same number is reported by `swap.paladinfi.com/health` and used in the apex homepage badge at <https://paladinfi.com>. Prior to v0.11.66 the public surface evolved without a dedicated public-repo changelog; the entries below cover from v0.11.66 forward.

---

## README — 2026-05-27 (doc-only, no version bump)

- Added cross-link in "Install (REST)" section to the new dev tutorial at [paladinfi.com/docs/screen-wallets/](https://paladinfi.com/docs/screen-wallets/) — drop-in cURL + ~3-minute React hook for the free `/v1/trust-check/ofac` endpoint. No code or wire-format change; this repo is the OpenAPI catalog spec only (no npm publish). Backend server version remains v0.11.77.

---

## v0.11.77 — 2026-05-23

### Added

- **`POST /v1/trust-check/ofac` — free wallet-OFAC tier.** Anonymous (no API key), real-data (`_real: true`), rate-limited (1 r/s + burst 3 + `limit_conn perip 3` via dedicated nginx zone). Runs only the OFAC SDN screen (in-memory frozenset lookup of ~93 Treasury SDN wallet addresses refreshed daily). Designed as the on-ramp for callers who want to validate request shape against the trust-check API without bridging to x402 micropayment first. Response includes `_paid_endpoint_info` upgrade hint to the full composition endpoint.

  **Scope note**: this is a wallet-address screen, not a token-contract screen. The Treasury SDN list at FeatureTypeID=345/DetailTypeID=1432 carries individual + entity wallet addresses; token-contract OFAC hits (e.g., Tornado Cash routers) require an extended sanctioned-contract list not in this release. Every response includes a `_scope` field disclosing this explicitly: `"ofac-only (wallet-address screen; use /v1/trust-check for full composition: GoPlus + Etherscan + anomaly heuristics)"`.

  **Response shape** (matches `/v1/trust-check` paid format for consistency):

  ```json
  {
    "address": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
    "chainId": 8453,
    "trust": {
      "recommendation": "allow",
      "factors": [
        { "source": "ofac", "signal": "not_listed", "weight": 0, "details": "", "real": true }
      ],
      "version": "1.1",
      "_real": true,
      "_scope": "ofac-only (wallet-address screen; use /v1/trust-check for full composition: GoPlus + Etherscan + anomaly heuristics)",
      "_ofac_list_updated_at": "2026-05-23T04:06:35Z",
      "_ofac_sdn_count": 93
    },
    "_paid_endpoint_info": { "url": "https://swap.paladinfi.com/v1/trust-check", "method": "POST", "auth": "x402 (USDC EIP-3009 transferWithAuthorization on Base)", "price_usdc": "0.001", "...": "..." }
  }
  ```

- **`/health` block `ofac_free_endpoint`** with `enabled`, `calls_total`, `last_hit_ts`, `last_result`, `error_count`, and `ofac_list { last_refresh_iso, count, date_of_issue }`. Surfaces both endpoint usage telemetry and the OFAC SDN list's staleness so ops can detect "list went stale" without SSH+grep.

### Notes

- **No upstream API calls in this handler by design.** The OFAC screen is an in-memory frozenset lookup; adding any upstream HTTP call from this endpoint would turn the free tier into a free DDoS vector against PaladinFi's upstream API budgets. Comment-banner in `swap_router_service.py` documents this constraint for future maintainers.
- **Sec HIGH-V2 invariant**: defensive try/except on `is_sanctioned()` returns a warn shape with the static phrase `"source unreachable"` — never `str(err)`, which would leak API keys or hostnames via embedded URLs. Same invariant as the v0.11.73 trust_block fail-closed contract.
- **Feature flag**: `OFAC_FREE_ENDPOINT_ENABLED=true` default; operators can flip to `false` + restart `trading-swap-router.service` to disable the endpoint in <30s without redeploy.
- **EEAGeofence applies identically**: EU users see HTTP 451 on this endpoint as on all others.
- `TRUST_BLOCK_VERSION` stays at `1.1` — no contract change; the new endpoint uses the same factor shape as the v0.11.73 contract, just emitting only the single OFAC factor.

### Changed

- `/health` version bumped `0.11.76 → 0.11.77`.

---

## v0.11.76 — 2026-05-22

### Changed

- **`/v1/trust-check` response shape — `scam_intel` sub-sources now emit explicit `unreachable` factors** when they can't run, closing a silent-`[]` gap one layer below the v0.11.73 fail-closed contract. Previously a missing `ETHERSCAN_API_KEY` or an upstream API failure on either `goplus` or `etherscan_source` caused the affected sub-source to be omitted from the `factors[]` array entirely. Customers couldn't distinguish "sub-source ran and returned no signal" from "sub-source didn't run". Now both modes emit a flagged factor with `signal: "unreachable"`, `real: false`, `weight: 0`, `details: "source unreachable"` — identical shape to the v0.11.73 source-level unreachable factor. Three paths affected:
  - `_check_goplus` upstream API failed (non-success code or network error) → unreachable.
  - `_check_etherscan_source` `ETHERSCAN_API_KEY` not configured → unreachable.
  - `_check_etherscan_source` upstream API failed (network error, non-success status, or missing result) → unreachable.

### Notes

- **Additive change for downstream consumers.** Code already filtering `real: false` factors out of risk computation per the v0.11.73 contract handles this transparently — new unreachable factors are ignored. Code counting `factors[]` length sees more items when sub-sources are unreachable; that's the intended honest signal.
- **`TRUST_BLOCK_VERSION` stays at `1.1`.** The structural contract — per-source unreachable factor emission — is unchanged from v0.11.73; v0.11.76 extends the contract's coverage to sub-source paths in the `scam_intel` group without changing the wire shape.
- **Sec HIGH-V2 invariant preserved.** The `details` field is the static phrase `"source unreachable"`, never a stringified exception. No API-key, hostname, or URL leak vectors through the new unreachable factors.
- **Still silent-`[]` by design (out of scope):** GoPlus chain-unsupported (out-of-coverage is semantically distinct from unreachable; deserves its own taxonomy in a future scope discussion); GoPlus "no data on this address" (honest "ran fine, no signal" answer — not a failure).
- 10 unit tests at `tests/v0.11.76/test_scam_intel_unreachable.py`; 24/24 pass alongside the existing 13 v0.11.73 fail-closed tests (no regression).

---

## v0.11.75 — 2026-05-22

### Added

- **`CORSMiddleware` on `swap.paladinfi.com`** enabling in-browser cross-origin calls to `/v1/quote` from `paladinfi.com` and `www.paladinfi.com`. The new interactive widget on the `/swap/` apex page calls `/v1/quote` live from the browser; this middleware unblocks the preflight that would otherwise prevent the widget from working.
  - `allow_origins`: `["https://paladinfi.com", "https://www.paladinfi.com"]` — narrow allowlist. Both surfaces serve via LiteSpeed (no `www → apex` redirect), so both must be present.
  - `allow_methods`: `["GET", "POST", "OPTIONS"]`.
  - `allow_headers`: `["content-type"]` — narrow.
  - `allow_credentials`: `false`.
  - `max_age`: `600` (10-minute preflight cache).
- Middleware is registered **first** (outermost in Starlette's LIFO stack) so `OPTIONS` preflight short-circuits inside CORS before reaching `EEAGeofenceMiddleware` / `PaymentMiddleware`. EEA-blocked 451 responses still receive the CORS `Access-Control-Allow-Origin` header on the response path, so the browser sees a clean 451 with allow-origin set rather than an opaque network error.

### Changed

- `/health` version bumped `0.11.74 → 0.11.75`.

### Notes

- **No public-API behavioral change for non-browser callers.** `curl`, MCP clients, and server-to-server callers see identical behavior to v0.11.74. Only cross-origin browser callers from `paladinfi.com` / `www.paladinfi.com` see new behavior (CORS preflight succeeds).
- Deploy procedure gained a pre-flight nginx CORS-header scan to prevent future double-CORS-header bugs from misconfigured nginx zones. Scan returned clean for v0.11.75.
- Paid-mode (`/v1/quote-paid`) is unaffected — x402 settlement headers (`X-PAYMENT`, etc.) are intentionally not in `allow_headers` because the in-browser widget calls only the free `/v1/quote` path. A future paid-mode browser surface would require widening the allowlist.

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
