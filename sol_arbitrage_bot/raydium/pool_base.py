from abc import ABC, abstractmethod
from typing import Tuple, List, Optional
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.instruction import Instruction
from sol_arbitrage_bot.solana_client import SolanaClient
from sol_arbitrage_bot.constants import SOL_MINT


class LiquidityPool(ABC):
    @abstractmethod
    async def get_token_price(self, solana_client: SolanaClient, base_mint_address: Pubkey = SOL_MINT) -> float:
        pass

    @abstractmethod
    def get_quote_mint(self, base_mint: Pubkey) -> Optional[Pubkey]:
        pass

    @abstractmethod
    def get_base_quote_decimals(self, base_mint: Pubkey) -> Optional[Tuple[int, int]]:
        pass

    @abstractmethod
    async def calculate_received_quote_tokens(
        self,
        solana_client: SolanaClient,
        base_in_count: int,
        base_mint: Pubkey,
    ) -> Optional[Tuple[Pubkey, float, int]]:
        pass

    @abstractmethod
    async def make_buy_instructions(
        self,
        solana_client: SolanaClient,
        payer_keypair: Keypair,
        slippage: float,
        base_in: float,
        quote_token_account: Pubkey,
        base_token_account: Pubkey,
        base_mint: Pubkey,
    ) -> Optional[List[Instruction]]:
        pass

    @abstractmethod
    async def make_sell_instructions(
        self,
        solana_client: SolanaClient,
        payer_keypair: Keypair,
        slippage: float,
        percentage: int,
        quote_token_account: Pubkey,
        base_token_account: Pubkey,
        base_mint: Pubkey,
    ) -> Optional[List[Instruction]]:
        pass

