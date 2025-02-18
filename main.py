import json
import asyncio
import argparse

from solders.pubkey import Pubkey
from solders.keypair import Keypair

from jito_async import JitoJsonRpcSDK

from sol_arbitrage_bot.solana_client import SolanaClient
from sol_arbitrage_bot.raydium.raydium_fetcher import RaydiumFetcher
from sol_arbitrage_bot.liquidity_pool import fetch_liquidity_pool
from sol_arbitrage_bot.arbitrage import *
from sol_arbitrage_bot.accounts import *
from sol_arbitrage_bot.constants import SOL_RPC_URL


def argmin(a):
    return min(range(len(a)), key=lambda x : a[x])


def argmax(a):
    return max(range(len(a)), key=lambda x : a[x])


async def confirm_landed_bundle(sdk: JitoJsonRpcSDK, bundle_id: str, max_attempts: int = 60, delay: float = 2.0):
    for attempt in range(max_attempts):
        response = await sdk.get_bundle_statuses([bundle_id])
        if response is None:
            return

        if not response['success']:
            print(f"Error confirming bundle status: {response.get('error', 'Unknown error')}")
            await asyncio.sleep(delay)

        print(f"Confirmation attempt {attempt + 1}/{max_attempts}:")
        print(json.dumps(response, indent=2))

        if 'result' not in response['data']:
            print(f"Unexpected response structure. 'result' not found in response data.")
            await asyncio.sleep(delay)

        result = response['data']['result']
        if 'value' not in result or not result['value']:
            print(f"Bundle {bundle_id} not found in confirmation response")
            await asyncio.sleep(delay)

        bundle_status = result['value'][0]
        if bundle_status['bundle_id'] != bundle_id:
            print(f"Unexpected bundle ID in response: {bundle_status['bundle_id']}")
            await asyncio.sleep(delay)

        status = bundle_status.get('confirmation_status')

        if status == 'finalized':
            print(f"Bundle {bundle_id} has been finalized on-chain!")
            # Extract transaction ID and construct Solscan link
            if 'transactions' in bundle_status and bundle_status['transactions']:
                tx_id = bundle_status['transactions'][0]
                solscan_link = f"https://solscan.io/tx/{tx_id}"
                print(f"Transaction details: {solscan_link}")
            else:
                print("Transaction ID not found in the response.")
            return 'Finalized'
        elif status == 'confirmed':
            print(f"Bundle {bundle_id} is confirmed but not yet finalized. Checking again...")
        elif status == 'processed':
            print(f"Bundle {bundle_id} is processed but not yet confirmed. Checking again...")
        else:
            print(f"Unexpected status '{status}' during confirmation for bundle {bundle_id}")

        # Check for errors
        err = bundle_status.get('err', {}).get('Ok')
        if err is not None:
            print(f"Error in bundle {bundle_id}: {err}")
            return 'Failed'

        await asyncio.sleep(delay)

    print(f"Max confirmation attempts reached. Unable to confirm finalization of bundle {bundle_id}")
    return 'Landed'

async def check_bundle_status(sdk: JitoJsonRpcSDK, bundle_id: str, max_attempts: int = 30, delay: float = 2.0):
    for attempt in range(max_attempts):
        response = await sdk.get_inflight_bundle_statuses([bundle_id])
        if response is None:
            return

        if not response['success']:
            print(f"Error checking bundle status: {response.get('error', 'Unknown error')}")
            await asyncio.sleep(delay)
            continue

        print(f"Raw response (Attempt {attempt + 1}/{max_attempts}):")
        print(json.dumps(response, indent=2))

        if 'result' not in response['data']:
            print(f"Unexpected response structure. 'result' not found in response data.")
            await asyncio.sleep(delay)
            continue

        result = response['data']['result']
        if 'value' not in result or not result['value']:
            print(f"Bundle {bundle_id} not found in response")
            await asyncio.sleep(delay)
            continue

        bundle_status = result['value'][0]
        status = bundle_status.get('status')
        print(f"Attempt {attempt + 1}/{max_attempts}: Bundle status - {status}")

        if status == 'Landed':
            print(f"Bundle {bundle_id} has landed on-chain! Performing additional confirmation...")
            final_status = await confirm_landed_bundle(sdk, bundle_id)
            return final_status
        elif status == 'Failed':
            print(f"Bundle {bundle_id} has failed.")
            return status
        elif status == 'Invalid':
            if attempt < 5:  # Check a few more times before giving up on Invalid(usually on start)
                print(f"Bundle {bundle_id} is currently invalid. Checking again...")
            else:
                print(f"Bundle {bundle_id} is invalid (not in system or outside 5-minute window).")
                return status
        elif status == 'Pending':
            print(f"Bundle {bundle_id} is still pending. Checking again in {delay} seconds...")
        else:
            print(f"Unknown status '{status}' for bundle {bundle_id}")

        await asyncio.sleep(delay)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Arbitrage bot")
    parser.add_argument(
        "--wallet",
        "-w",
        type=str,
        required=True,
        help="Path to wallet's keypair file"
    )
    parser.add_argument(
        "--rpc-url",
        "-r",
        type=str,
        required=False,
        default=SOL_RPC_URL,
        help="Solana RPC"
    )
    return parser.parse_args()


async def main(wallet: str, rpc_url: str):
    with open(wallet, 'r') as file:
        wallet_keypair_data = json.load(file)
    payer_keypair = Keypair.from_bytes(bytes(wallet_keypair_data))
    print("payer pubkey", payer_keypair.pubkey())

    snai_token_mint = "Hjw6bEcHtbHGpQr8onG3izfJY5DJiWdt7uk2BfdSpump"
    griffain_token_mint = "KENJSUYLASHUMfHyy5o4Hp2FdNqZg1AsUPhfH2kYvEP"
    usdc_token_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    token_mint = snai_token_mint


    """ async with SolanaClient(rpc_url=rpc_url) as solana_client: """
    """     txn_sig = await create_token_account( """
    """         solana_client, """
    """         payer_keypair, """
    """         Pubkey.from_string(token_mint) """
    """     ) """
    """     print(txn_sig) """

    async with SolanaClient(rpc_url=rpc_url) as solana_client:
        async with RaydiumFetcher() as raydium_fetcher:
            pools = await raydium_fetcher.fetch_top_lp_for_mint(
                token_mint,
                5, 1
            )
            if not pools or len(pools) == 0:
                raise Exception()

        print("token mint", token_mint)
        liquidity_pools = []
        liquidity_pools_prices = []
        for pool in pools:
            pair_address = Pubkey.from_string(pool["id"])
            liquidity_pool = await fetch_liquidity_pool(solana_client, pair_address)
            if liquidity_pool is None:
                print(f"could not fetch liquidity pool {pair_address}")
                continue

            print(f"fetched liquidity pool {pair_address}")
            liquidity_pools.append(liquidity_pool)

            price = await liquidity_pool.get_token_price(solana_client)
            if price is None:
                print(f"could not fetch price for liquidity pool {pair_address}")
            liquidity_pools_prices.append(price)

        if len(liquidity_pools) <= 1:
            print("could not arbitrage")
            return

        sol_in = 0.01
        bundle = True
        buy_pool = liquidity_pools[argmin(liquidity_pools_prices)]
        sell_pool = liquidity_pools[argmax(liquidity_pools_prices)]
        print("buy pool", buy_pool.pair_address)
        print("sell pool", sell_pool.pair_address)

        async with JitoJsonRpcSDK(url="https://frankfurt.mainnet.block-engine.jito.wtf") as jito_client:
            arbitrage_result = await arbitrage(
                solana_client,
                jito_client,
                buy_pool,
                sell_pool,
                payer_keypair,
                sol_in,
                bundle=bundle,
            )
            if arbitrage_result is None:
                print("error")
                return

            if bundle:
                await check_bundle_status(jito_client, arbitrage_result['data']['result'])


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.wallet, args.rpc_url))

