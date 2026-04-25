/**
 * PaladinFi Swap — end-to-end TypeScript example using viem.
 *
 *   pnpm add viem
 *
 * Set TAKER_PRIVATE_KEY in the environment before running. The taker must
 * hold the sellToken and have approved the returned router (or use Permit2 —
 * out of scope for this example).
 */
import { createPublicClient, createWalletClient, http, parseGwei, type Hex } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";

const PALADIN_API = "https://swap.paladinfi.com";

// Base mainnet token addresses
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" as const;
const WETH = "0x4200000000000000000000000000000000000006" as const;

interface QuoteResponse {
  source: string;
  chainId: number;
  router: string;
  calldata: string;
  buyAmount: string;
  minBuyAmount: string;
  sellAmount: string;
  gas: string;
  ourFeeBps: number;
  ourFeeRecipient: string;
  estimatedOurFeeAmount?: string;
  estimatedOurFeeToken?: string;
}

async function quote(params: {
  sellToken: string;
  buyToken: string;
  sellAmount: string;
  taker: string;
  slippageBps?: number;
}): Promise<QuoteResponse> {
  const res = await fetch(`${PALADIN_API}/v1/quote`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chainId: 8453, slippageBps: 50, ...params }),
  });
  if (!res.ok) {
    throw new Error(`Quote failed ${res.status}: ${await res.text()}`);
  }
  return (await res.json()) as QuoteResponse;
}

async function main() {
  const pk = process.env.TAKER_PRIVATE_KEY as Hex | undefined;
  if (!pk) {
    console.error("Set TAKER_PRIVATE_KEY in the environment.");
    process.exit(1);
  }
  const account = privateKeyToAccount(pk);

  const q = await quote({
    sellToken: USDC,
    buyToken: WETH,
    sellAmount: "5000000",
    taker: account.address,
  });

  console.log(`Source:        ${q.source}`);
  console.log(`Router:        ${q.router}`);
  console.log(`Buy amount:    ${q.buyAmount} (min ${q.minBuyAmount})`);
  console.log(`Affiliate fee: ${q.ourFeeBps} bps to ${q.ourFeeRecipient}`);
  console.log(`Gas estimate:  ${q.gas}`);
  console.log();

  const wallet = createWalletClient({
    account,
    chain: base,
    transport: http(),
  });
  const publicClient = createPublicClient({
    chain: base,
    transport: http(),
  });

  console.log("Submitting transaction...");
  const hash = await wallet.sendTransaction({
    to: q.router as `0x${string}`,
    data: q.calldata as `0x${string}`,
    value: 0n,
    gas: BigInt(Math.floor(Number(q.gas) * 1.2)),
    maxFeePerGas: parseGwei("0.05"),
    maxPriorityFeePerGas: parseGwei("0.005"),
  });
  console.log(`TX:            https://basescan.org/tx/${hash}`);

  // Optionally wait for inclusion
  const receipt = await publicClient.waitForTransactionReceipt({ hash });
  console.log(`Status:        ${receipt.status}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
