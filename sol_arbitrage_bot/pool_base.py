from abc import ABC, abstractmethod
from typing import Tuple, List, Optional
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.instruction import Instruction
from sol_arbitrage_bot.solana_client import SolanaClient
from sol_arbitrage_bot.constants import SOL_MINT


class LiquidityPool(ABC):
    @abstractmethod
    async def get_token_price(self, solana_client: SolanaClient, base_mint: Pubkey = SOL_MINT) -> float:
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
        base_in: float,
        base_mint: Pubkey,
    ) -> Optional[float]:
        pass

    @abstractmethod
    async def calculate_received_base_tokens(
        self,
        solana_client: SolanaClient,
        quote_in: float,
        base_mint: Pubkey,
    ) -> Optional[float]:
        pass

    @abstractmethod
    def make_swap_instruction(
        self,
        amount_in: int,
        minimum_amount_out: int,
        token_account_in: Pubkey,
        token_account_out: Pubkey,
        owner: Pubkey,
        input_mint: Pubkey,
    ) -> Optional[Instruction]:
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

