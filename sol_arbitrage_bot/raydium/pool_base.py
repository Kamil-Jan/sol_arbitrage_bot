from abc import ABC, abstractmethod
from arbitrage_bot.solana_client import SolanaClient


class LiquidityPool(ABC):
    @abstractmethod
    async def get_token_price(self, solana_client: SolanaClient, base_mint_address: str) -> float:
        pass
