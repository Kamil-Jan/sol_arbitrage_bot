import logging
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional

from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.instruction import Instruction

from .solana_client import SolanaClient
from .constants import SOL_MINT
from .accounts import close_account_instruction


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
        quote_mint_base_quote_decimals = self.get_base_quote_decimals(base_mint)
        if quote_mint_base_quote_decimals is None:
            return None

        base_decimals, quote_decimals = quote_mint_base_quote_decimals
        base_in_count = int(base_in * (10 ** base_decimals))

        quote_out = await self.calculate_received_quote_tokens(
            solana_client,
            base_in,
            base_mint
        )
        if quote_out is None:
            return None

        quote_out_count = int(quote_out * (10 ** quote_decimals))

        slippage_adjustment = 1 - (slippage / 100)
        minimum_quote_out_count = int(quote_out_count * slippage_adjustment)

        swap_instruction = self.make_swap_instruction(
            amount_in=base_in_count,
            minimum_amount_out=minimum_quote_out_count,
            token_account_in=base_token_account,
            token_account_out=quote_token_account,
            owner=payer_keypair.pubkey(),
            input_mint=base_mint,
        )
        if swap_instruction is None:
            return None

        return [swap_instruction]

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
        if not (1 <= percentage <= 100):
            logging.error("percentage must be between 1 and 100")
            return None

        quote_balance = await solana_client.get_token_account_balance(quote_token_account)
        if quote_balance is None:
            logging.error("could not fetch quote balance")
            return None

        base_quote_decimals = self.get_base_quote_decimals(base_mint)
        if base_quote_decimals is None:
            logging.error("invalid base mint")
            return None

        base_decimals, quote_decimals = base_quote_decimals

        quote_mint = self.get_quote_mint(base_mint)
        if quote_mint is None:
            return None

        quote_in = quote_balance.ui_amount * (percentage / 100)
        quote_in_count = int(quote_in * (10 ** quote_decimals))

        base_out = await self.calculate_received_base_tokens(
            solana_client,
            quote_in,
            base_mint,
        )
        if base_out is None:
            return None

        base_out_count = int(base_out * (10 ** base_decimals))

        slippage_adjustment = 1 - (slippage / 100)
        minimum_base_out_count = int(base_out_count * slippage_adjustment)

        swap_instruction = self.make_swap_instruction(
            amount_in=quote_in_count,
            minimum_amount_out=minimum_base_out_count,
            token_account_in=quote_token_account,
            token_account_out=base_token_account,
            owner=payer_keypair.pubkey(),
            input_mint=quote_mint,
        )
        if swap_instruction is None:
            return None

        instructions = [swap_instruction]

        if percentage == 100:
            close_token_account_instruction = close_account_instruction(
                quote_token_account, payer_keypair
            )
            instructions.append(close_token_account_instruction)

        return instructions
