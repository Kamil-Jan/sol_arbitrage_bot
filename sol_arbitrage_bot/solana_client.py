import asyncio
import aiohttp
import logging
from typing import List, Any, Optional

from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TokenAccountOpts
from solana.rpc.commitment import Processed
from solders.pubkey import Pubkey

from .constants import SOL_RPC_URL


MAX_RETRIES = 5
BACKOFF_FACTOR = 1.0
RPC_TIMEOUT = 10
RPC_CONCURRENCY_LIMIT = 5


class SolanaClient:
    """
    A class responsible for handling Solana RPC calls with
    built-in retry logic and concurrency control.
    """

    def __init__(
        self,
        rpc_url: str = SOL_RPC_URL,
        max_retries: int = MAX_RETRIES,
        backoff_factor: float = BACKOFF_FACTOR,
        rpc_timeout: int = RPC_TIMEOUT,
        rpc_concurrency_limit: int = RPC_CONCURRENCY_LIMIT
    ):
        self.rpc_url = rpc_url
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.semaphore = asyncio.Semaphore(rpc_concurrency_limit)

        self.client = AsyncClient(
            self.rpc_url,
            timeout=rpc_timeout
        )

    async def __aenter__(self) -> "SolanaClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.close()

    async def _rpc_call(self, func, *args, **kwargs) -> Any:
        for attempt in range(1, self.max_retries + 1):
            async with self.semaphore:
                try:
                    return await func(*args, **kwargs)
                except aiohttp.ClientResponseError as e:
                    if e.status == 429:
                        wait_time = self.backoff_factor * (2 ** (attempt - 1))
                        logging.warning(
                            f"429 Too Many Requests. Retrying in {wait_time} seconds "
                            f"(Attempt {attempt}/{self.max_retries})..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logging.error(f"Client response error: {e}. No further retry.")
                        break
                except Exception as e:
                    logging.error(f"RPC call error: {e}. Retrying...")
                    wait_time = self.backoff_factor * (2 ** (attempt - 1))
                    await asyncio.sleep(wait_time)

        logging.error(f"Max retries exceeded for RPC call: {func.__name__}")
        return None

    async def get_multiple_accounts_json_parsed(
        self,
        pubkeys: List[Pubkey]
    ) -> Optional[List[Any]]:
        response = await self._rpc_call(
            self.client.get_multiple_accounts_json_parsed,
            pubkeys,
            Processed
        )
        if response is not None:
            return response.value
        return None

    async def get_account_info_json_parsed(self, address: Pubkey) -> Optional[Any]:
        response = await self._rpc_call(
            self.client.get_account_info_json_parsed,
            address
        )
        if response is not None:
            return response.value
        return None

    async def get_token_accounts_by_owner(self, owner: Pubkey, token_mint: Pubkey) -> Optional[Any]:
        response = await self._rpc_call(
            self.client.get_token_accounts_by_owner,
            owner,
            TokenAccountOpts(token_mint),
            Processed
        )
        if response is not None:
            return response.value
        return None

    async def get_token_account_balance(self, address: Pubkey) -> Optional[Any]:
        response = await self._rpc_call(
            self.client.get_token_account_balance,
            address
        )
        if response is not None:
            return response.value
        return None

    async def get_latest_blockhash(self) -> Optional[Any]:
        response = await self._rpc_call(
            self.client.get_latest_blockhash,
        )
        if response is not None:
            return response.value
        return None