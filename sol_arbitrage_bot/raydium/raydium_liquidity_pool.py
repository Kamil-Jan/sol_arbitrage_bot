import logging
from typing import Optional

from solders.pubkey import Pubkey

from sol_arbitrage_bot.solana_client import SolanaClient
from sol_arbitrage_bot.pool_base import LiquidityPool

from sol_arbitrage_bot.raydium.amm_v4 import amm_v4
from sol_arbitrage_bot.raydium.clmm import clmm


def is_raydium_pool(pool_data) -> bool:
    return amm_v4.is_amm_v4_pool(pool_data) or clmm.is_clmm_pool(pool_data)


async def fetch_liquidity_pool(solana_client: SolanaClient, pair_address: Pubkey, pool_data) -> Optional[LiquidityPool]:
    """
    Fetches and decodes the pool keys from the Raydium pair address.
    """
    if amm_v4.is_amm_v4_pool(pool_data):
        pool = await amm_v4.fetch_amm_v4_pool(solana_client, pair_address, pool_data)
    elif clmm.is_clmm_pool(pool_data):
        pool = await clmm.fetch_clmm_pool(solana_client, pair_address, pool_data)
    else:
        logging.error(f"Unknown pool type {pool_data.owner}")
        return None
    return pool
