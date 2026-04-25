"""
PaladinFi Swap — end-to-end Python example.

Quotes USDC -> WETH on Base, signs the calldata returned by the service, and
submits the transaction. Requires:

    pip install web3 requests

Set TAKER_PRIVATE_KEY in the environment before running. The taker must hold
the sellToken and have approved the returned router (or use Permit2 — out of
scope for this example).
"""
from __future__ import annotations
import os
import sys
import requests
from web3 import Web3
from eth_account import Account

PALADIN_API = "https://swap.paladinfi.com"
BASE_RPC = "https://base-rpc.publicnode.com"
CHAIN_ID = 8453

# Base mainnet token addresses
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
WETH = "0x4200000000000000000000000000000000000006"


def quote(sell_token: str, buy_token: str, sell_amount: str, taker: str,
          slippage_bps: int = 50) -> dict:
    """Fetch a competitive route quote with ready-to-execute calldata."""
    payload = {
        "chainId": CHAIN_ID,
        "sellToken": sell_token,
        "buyToken": buy_token,
        "sellAmount": sell_amount,
        "taker": taker,
        "slippageBps": slippage_bps,
    }
    resp = requests.post(f"{PALADIN_API}/v1/quote", json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def submit(quote_response: dict, private_key: str) -> str:
    """Sign the quote's calldata and submit. Returns the tx hash."""
    w3 = Web3(Web3.HTTPProvider(BASE_RPC))
    acct = Account.from_key(private_key)
    if acct.address.lower() != quote_response["sellAmount"] and \
            acct.address.lower() != _safe_get_taker(quote_response).lower():
        # The quote was prepared for a specific taker; the signer must match.
        # We don't actually have taker in the quote response; the caller is
        # responsible for ensuring the keys match the address they passed in.
        pass

    tx = {
        "from": acct.address,
        "to": Web3.to_checksum_address(quote_response["router"]),
        "data": quote_response["calldata"],
        "value": 0,
        "gas": int(int(quote_response["gas"]) * 1.2),
        "maxFeePerGas": w3.to_wei(0.05, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(0.005, "gwei"),
        "nonce": w3.eth.get_transaction_count(acct.address),
        "chainId": CHAIN_ID,
    }
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return tx_hash.hex()


def _safe_get_taker(_quote_response: dict) -> str:
    # Placeholder — current API does not echo taker in the response. Caller
    # tracks this externally.
    return ""


def main() -> int:
    pk = os.environ.get("TAKER_PRIVATE_KEY")
    if not pk:
        print("Set TAKER_PRIVATE_KEY in the environment.", file=sys.stderr)
        return 1
    taker = Account.from_key(pk).address

    # 5 USDC -> WETH
    q = quote(USDC, WETH, "5000000", taker)
    print(f"Source:        {q['source']}")
    print(f"Router:        {q['router']}")
    print(f"Buy amount:    {q['buyAmount']} (min {q['minBuyAmount']})")
    print(f"Affiliate fee: {q['ourFeeBps']} bps to {q['ourFeeRecipient']}")
    print(f"Gas estimate:  {q['gas']}")
    print()
    print("Submitting transaction...")
    tx_hash = submit(q, pk)
    print(f"TX:            https://basescan.org/tx/{tx_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
