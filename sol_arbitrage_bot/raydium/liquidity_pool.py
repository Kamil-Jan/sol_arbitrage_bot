import logging
from typing import Optional

from solders.pubkey import Pubkey

from sol_arbitrage_bot.solana_client import SolanaClient

from .pool_base import LiquidityPool
from .amm_v4 import AMM_V4_PROGRAM_ID, decode_amm_v4_pool
from .clmm import CLMM_PROGRAM_ID, decode_clmm_pool


async def fetch_liquidity_pool(solana_client: SolanaClient, pair_address: Pubkey) -> Optional[LiquidityPool]:
    """
    Fetches and decodes the pool keys from the Raydium pair address.
    """
    account_data = await solana_client.get_account_info_json_parsed(pair_address)
    if account_data is None or not account_data:
        logging.error(f"Failed to fetch AMM data for {pair_address}")
        return None

    if account_data.owner == AMM_V4_PROGRAM_ID:
        return decode_amm_v4_pool(pair_address, account_data.data)
    elif account_data.owner == CLMM_PROGRAM_ID:
        return decode_clmm_pool(pair_address, account_data.data)
    else:
        logging.error(f"Unknown pool type {account_data.owner}")
        return None
