import logging
from typing import Optional

from solders.pubkey import Pubkey

from sol_arbitrage_bot.solana_client import SolanaClient
from sol_arbitrage_bot.raydium import raydium_liquidity_pool

from .pool_base import LiquidityPool


async def fetch_liquidity_pool(solana_client: SolanaClient, pair_address: Pubkey) -> Optional[LiquidityPool]:
    """
    Fetches and decodes the pool keys from the Raydium pair address.
    """
    pool_data = await solana_client.get_account_info_json_parsed(pair_address)
    if pool_data is None or not pool_data:
        logging.error(f"Failed to fetch AMM data for {pair_address}")
        return None

    if raydium_liquidity_pool.is_raydium_pool(pool_data):
        return raydium_liquidity_pool.fetch_raydium_liquidity_pool(solana_client, pair_address, pool_data)
    else:
        logging.error(f"Unknown pool type {pool_data.owner}")
        return None
