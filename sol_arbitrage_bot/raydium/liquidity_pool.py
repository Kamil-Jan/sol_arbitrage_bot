import logging
from typing import Optional

from solders.pubkey import Pubkey

from sol_arbitrage_bot.solana_client import SolanaClient

from .pool_base import LiquidityPool
from .amm_v4 import AMM_V4_PROGRAM_ID, AmmV4Pool, decode_amm_v4_pool_keys, decode_market_state_v3
from .clmm import CLMM_PROGRAM_ID, ClmmPool, decode_clmm_pool_keys


async def fetch_liquidity_pool(solana_client: SolanaClient, pair_address: Pubkey) -> Optional[LiquidityPool]:
    """
    Fetches and decodes the pool keys from the Raydium pair address.
    """
    pool_data = await solana_client.get_account_info_json_parsed(pair_address)
    if pool_data is None or not pool_data:
        logging.error(f"Failed to fetch AMM data for {pair_address}")
        return None

    if pool_data.owner == AMM_V4_PROGRAM_ID:
        pool_keys = decode_amm_v4_pool_keys(pool_data.data)
        if pool_keys is None:
            logging.error(f"Failed to fetch AMM pool keys for {pair_address}")
            return None

        market_data = await solana_client.get_account_info_json_parsed(pool_keys.market_id)
        if market_data is None or not market_data:
            logging.error(f"Failed to fetch AMM market data for {pair_address}")
            return None

        market_state = decode_market_state_v3(market_data.data)
        if market_state is None:
            logging.error(f"Failed to fetch Market state for {pair_address}")
            return None
        return AmmV4Pool(pair_address, pool_keys, market_state)
    elif pool_data.owner == CLMM_PROGRAM_ID:
        pool_keys = decode_clmm_pool_keys(pool_data.data)
        if pool_keys is None:
            logging.error(f"Failed to fetch CLMM pool keys for {pair_address}")
            return None

        return ClmmPool(pair_address, pool_keys)
    else:
        logging.error(f"Unknown pool type {pool_data.owner}")
        return None
