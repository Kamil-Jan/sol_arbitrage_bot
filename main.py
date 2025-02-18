import json
import asyncio
import argparse

from solders.pubkey import Pubkey
from solders.keypair import Keypair

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
    async with SolanaClient(rpc_url=rpc_url) as solana_client:
        async with RaydiumFetcher() as raydium_fetcher:
            for token_mint in [snai_token_mint]:
                pools = await raydium_fetcher.fetch_top_lp_for_mint(token_mint, 3, 1)
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

            liquidity_pools.append(liquidity_pool)

            price = await liquidity_pool.get_token_price(solana_client)
            if price is None:
                print(f"could not fetch price for liquidity pool {pair_address}")
            liquidity_pools_prices.append(price)

        if len(liquidity_pools) <= 1:
            print("could not arbitrage")
            return

        buy_pool = liquidity_pools[argmin(liquidity_pools_prices)]
        sell_pool = liquidity_pools[argmax(liquidity_pools_prices)]
        print("buy pool", buy_pool.pair_address)
        print("sell pool", sell_pool.pair_address)

        arbitrage_result = await arbitrage(solana_client, buy_pool, sell_pool, payer_keypair, 0.01)
        print(arbitrage_result)


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.wallet, args.rpc_url))

