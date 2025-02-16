import asyncio
from solders.pubkey import Pubkey

from arbitrage_bot.solana_client import SolanaClient
from arbitrage_bot.raydium.raydium_fetcher import RaydiumFetcher
from arbitrage_bot.raydium.liquidity_pool import fetch_liquidity_pool


async def main():
    snai_token_mint = "Hjw6bEcHtbHGpQr8onG3izfJY5DJiWdt7uk2BfdSpump"
    griffain_token_mint = "KENJSUYLASHUMfHyy5o4Hp2FdNqZg1AsUPhfH2kYvEP"
    usdc_token_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    token_mint = snai_token_mint

    async with SolanaClient() as solana_client:
        async with RaydiumFetcher() as raydium_fetcher:
            for token_mint in [snai_token_mint]:
                pools = await raydium_fetcher.fetch_top_lp_for_mint(token_mint, 3, 1)
                if not pools:
                    raise Exception()

                print(token_mint)
                for pool in pools:
                    pair_address = Pubkey.from_string(pool["id"])
                    liquidity_pool = await fetch_liquidity_pool(solana_client, pair_address)
                    if liquidity_pool is not None:
                        price = await liquidity_pool.get_token_price(solana_client)
                        print("  ", price)


if __name__ == "__main__":
    asyncio.run(main())
