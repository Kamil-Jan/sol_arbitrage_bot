import aiohttp
import logging
from typing import Dict, List, Any, Optional

from sol_arbitrage_bot.constants import SOL_MINT


RAYDIUM_API_URL =  "https://api-v3.raydium.io"


class RaydiumFetcher:
    """
    A class responsible for handling interactions with the Raydium API.
    """

    def __init__(self, raydium_api_url: str = RAYDIUM_API_URL):
        self.raydium_api_url = raydium_api_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "RaydiumFetcher":
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def fetch_top_lp_for_mint(
        self,
        token_mint: str,
        page_size: int = 1,
        page: int = 1,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches Raydium LP pools for a given token mint address
        paired with SOL. Returns None if not found.
        """
        pool_type = "all"
        pool_sort_field = "liquidity"
        sort_type = "desc"

        url = (
            f"{RAYDIUM_API_URL}/pools/info/mint?"
            f"mint1={token_mint}&mint2={SOL_MINT}"
            f"&poolType={pool_type}"
            f"&poolSortField={pool_sort_field}"
            f"&sortType={sort_type}"
            f"&pageSize={page_size}"
            f"&page={page}"
        )

        if self.session is None:
            logging.error("RaydiumFetcher or session is not initialized.")
            return None

        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logging.warning(
                        f"Raydium API returned status {response.status} "
                        f"for mint {token_mint}"
                    )
                    return None
                data = await response.json()
        except aiohttp.ClientError as e:
            logging.error(f"HTTP error fetching Raydium LP info: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error fetching Raydium LP info: {e}")
            return None

        pools = data.get('data', {}).get('data', [])
        if not pools:
            logging.info(f"No Raydium pools found for token mint: {token_mint}")
            return None

        return pools
