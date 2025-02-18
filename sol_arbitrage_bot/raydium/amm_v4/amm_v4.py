import logging
import struct
from dataclasses import dataclass, field
from typing import Tuple, List, Optional

from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.instruction import AccountMeta, Instruction

from sol_arbitrage_bot.constants import SOL_MINT, TOKEN_PROGRAM_ID
from sol_arbitrage_bot.solana_client import SolanaClient
from sol_arbitrage_bot.accounts import *

from sol_arbitrage_bot.pool_base import LiquidityPool
from .layouts import AMM_V4_LAYOUT, MARKET_STATE_LAYOUT_V3
from .constants import AMM_V4_PROGRAM_ID, OPEN_BOOK_PROGRAM_ID, RAY_AUTHORITY_V4


def bytes_of(value):
    if not (0 <= value < 2**64):
        raise ValueError("Value must be in the range of a u64 (0 to 2^64 - 1).")
    return struct.pack('<Q', value)


@dataclass
class AmmV4PoolKeys:
    status: int
    nonce: int
    max_order: int
    depth: int
    base_decimals: int
    quote_decimals: int
    state: int
    reset_flag: int
    min_size: int
    vol_max_cut_ratio: int
    amount_wave_ratio: int
    base_lot_size: int
    quote_lot_size: int
    min_price_multiplier: int
    max_price_multiplier: int
    system_decimal_value: int
    min_separate_numerator: int
    min_separate_denominator: int
    trade_fee_numerator: int
    trade_fee_denominator: int
    pnl_numerator: int
    pnl_denominator: int
    swap_fee_numerator: int
    swap_fee_denominator: int
    base_need_take_pnl: int
    quote_need_take_pnl: int
    quote_total_pnl: int
    base_total_pnl: int
    pool_open_time: int
    punish_pc_amount: int
    punish_coin_amount: int
    orderbook_to_init_time: int
    swap_base_in_amount: int
    swap_quote_out_amount: int
    swap_base2_quote_fee: int
    swap_quote_in_amount: int
    swap_base_out_amount: int
    swap_quote2_base_fee: int
    base_vault: Pubkey
    quote_vault: Pubkey
    base_mint: Pubkey
    quote_mint: Pubkey
    lp_mint: Pubkey
    open_orders: Pubkey
    market_id: Pubkey
    market_program_id: Pubkey
    target_orders: Pubkey
    withdraw_queue: Pubkey
    lp_vault: Pubkey
    owner: Pubkey
    lp_reserve: int
    padding: List[int] = field(default_factory=lambda: [0] * 3)


    @classmethod
    def from_decoded(cls, parsed: dict) -> "AmmV4PoolKeys":
        return cls(
            status=parsed["status"],
            nonce=parsed["nonce"],
            max_order=parsed["maxOrder"],
            depth=parsed["depth"],
            base_decimals=parsed["baseDecimals"],
            quote_decimals=parsed["quoteDecimals"],
            state=parsed["state"],
            reset_flag=parsed["resetFlag"],
            min_size=parsed["minSize"],
            vol_max_cut_ratio=parsed["volMaxCutRatio"],
            amount_wave_ratio=parsed["amountWaveRatio"],
            base_lot_size=parsed["baseLotSize"],
            quote_lot_size=parsed["quoteLotSize"],
            min_price_multiplier=parsed["minPriceMultiplier"],
            max_price_multiplier=parsed["maxPriceMultiplier"],
            system_decimal_value=parsed["systemDecimalValue"],
            min_separate_numerator=parsed["minSeparateNumerator"],
            min_separate_denominator=parsed["minSeparateDenominator"],
            trade_fee_numerator=parsed["tradeFeeNumerator"],
            trade_fee_denominator=parsed["tradeFeeDenominator"],
            pnl_numerator=parsed["pnlNumerator"],
            pnl_denominator=parsed["pnlDenominator"],
            swap_fee_numerator=parsed["swapFeeNumerator"],
            swap_fee_denominator=parsed["swapFeeDenominator"],
            base_need_take_pnl=parsed["baseNeedTakePnl"],
            quote_need_take_pnl=parsed["quoteNeedTakePnl"],
            quote_total_pnl=parsed["quoteTotalPnl"],
            base_total_pnl=parsed["baseTotalPnl"],
            pool_open_time=parsed["poolOpenTime"],
            punish_pc_amount=parsed["punishPcAmount"],
            punish_coin_amount=parsed["punishCoinAmount"],
            orderbook_to_init_time=parsed["orderbookToInitTime"],
            swap_base_in_amount=parsed["swapBaseInAmount"],
            swap_quote_out_amount=parsed["swapQuoteOutAmount"],
            swap_base2_quote_fee=parsed["swapBase2QuoteFee"],
            swap_quote_in_amount=parsed["swapQuoteInAmount"],
            swap_base_out_amount=parsed["swapBaseOutAmount"],
            swap_quote2_base_fee=parsed["swapQuote2BaseFee"],
            base_vault=Pubkey.from_bytes(parsed["baseVault"]),
            quote_vault=Pubkey.from_bytes(parsed["quoteVault"]),
            base_mint=Pubkey.from_bytes(parsed["baseMint"]),
            quote_mint=Pubkey.from_bytes(parsed["quoteMint"]),
            lp_mint=Pubkey.from_bytes(parsed["lpMint"]),
            open_orders=Pubkey.from_bytes(parsed["openOrders"]),
            market_id=Pubkey.from_bytes(parsed["marketId"]),
            market_program_id=Pubkey.from_bytes(parsed["marketProgramId"]),
            target_orders=Pubkey.from_bytes(parsed["targetOrders"]),
            withdraw_queue=Pubkey.from_bytes(parsed["withdrawQueue"]),
            lp_vault=Pubkey.from_bytes(parsed["lpVault"]),
            owner=Pubkey.from_bytes(parsed["owner"]),
            lp_reserve=parsed["lpReserve"],
            padding=parsed["padding"],
        )


@dataclass
class MarketStateV3:
    account_flags: dict
    own_address: Pubkey
    vault_signer_nonce: int
    base_mint: Pubkey
    quote_mint: Pubkey
    base_vault: Pubkey
    base_deposits_total: int
    base_fees_accrued: int
    quote_vault: Pubkey
    quote_deposits_total: int
    quote_fees_accrued: int
    quote_dust_threshold: int
    request_queue: Pubkey
    event_queue: Pubkey
    bids: Pubkey
    asks: Pubkey
    base_lot_size: int
    quote_lot_size: int
    fee_rate_bps: int
    referrer_rebate_accrued: int

    @classmethod
    def from_decoded(cls, decoded: dict) -> "MarketStateV3":
        return cls(
            account_flags={
                "initialized": decoded["account_flags"]["initialized"],
                "market": decoded["account_flags"]["market"],
                "open_orders": decoded["account_flags"]["open_orders"],
                "request_queue": decoded["account_flags"]["request_queue"],
                "event_queue": decoded["account_flags"]["event_queue"],
                "bids": decoded["account_flags"]["bids"],
                "asks": decoded["account_flags"]["asks"],
            },
            own_address=Pubkey.from_bytes(decoded["own_address"]),
            vault_signer_nonce=decoded["vault_signer_nonce"],
            base_mint=Pubkey.from_bytes(decoded["base_mint"]),
            quote_mint=Pubkey.from_bytes(decoded["quote_mint"]),
            base_vault=Pubkey.from_bytes(decoded["base_vault"]),
            base_deposits_total=decoded["base_deposits_total"],
            base_fees_accrued=decoded["base_fees_accrued"],
            quote_vault=Pubkey.from_bytes(decoded["quote_vault"]),
            quote_deposits_total=decoded["quote_deposits_total"],
            quote_fees_accrued=decoded["quote_fees_accrued"],
            quote_dust_threshold=decoded["quote_dust_threshold"],
            request_queue=Pubkey.from_bytes(decoded["request_queue"]),
            event_queue=Pubkey.from_bytes(decoded["event_queue"]),
            bids=Pubkey.from_bytes(decoded["bids"]),
            asks=Pubkey.from_bytes(decoded["asks"]),
            base_lot_size=decoded["base_lot_size"],
            quote_lot_size=decoded["quote_lot_size"],
            fee_rate_bps=decoded["fee_rate_bps"],
            referrer_rebate_accrued=decoded["referrer_rebate_accrued"],
        )


class AmmV4Pool(LiquidityPool):
    def __init__(self, pair_address: Pubkey, pool_keys: AmmV4PoolKeys, market_state: MarketStateV3):
        self.pair_address = pair_address
        self.pool_keys = pool_keys
        self.market_state = market_state
        self.authority = Pubkey.create_program_address(
            seeds=[bytes(self.pool_keys.market_id),
                   bytes_of(self.market_state.vault_signer_nonce)],
            program_id=OPEN_BOOK_PROGRAM_ID
        )

    def get_quote_mint(self, base_mint: Pubkey) -> Optional[Pubkey]:
        if self.pool_keys.base_mint == base_mint:
            return self.pool_keys.quote_mint
        elif self.pool_keys.quote_mint == base_mint:
            return self.pool_keys.base_mint
        logging.error(f"Invalid base mint address {base_mint} for pool {self.pair_address}")
        return None

    def get_base_quote_decimals(self, base_mint: Pubkey) -> Optional[Tuple[int, int]]:
        if self.pool_keys.base_mint == base_mint:
            base_decimals = self.pool_keys.base_decimals
            quote_decimals = self.pool_keys.quote_decimals
        elif self.pool_keys.quote_mint == base_mint:
            base_decimals = self.pool_keys.quote_decimals
            quote_decimals = self.pool_keys.base_decimals
        else:
            logging.error(f"Invalid base mint address {base_mint} for pool {self.pair_address}")
            return None
        return base_decimals, quote_decimals

    async def __get_base_quote_reserves(
        self,
        solana_client: SolanaClient,
        base_mint: Pubkey
    ) -> Optional[Tuple[int, int]]:
        try:
            base_vault_balance_resp = await solana_client.get_token_account_balance(self.pool_keys.base_vault)
            if base_vault_balance_resp is None:
                logging.error(f"Cannot fetch base vault token account balance {self.pool_keys.base_vault}")
                return None

            quote_vault_balance_resp = await solana_client.get_token_account_balance(self.pool_keys.quote_vault)
            if quote_vault_balance_resp is None:
                logging.error(f"Cannot fetch quote vault token account balance {self.pool_keys.quote_vault}")
                return None

            base_vault_balance = base_vault_balance_resp.ui_amount
            quote_vault_balance = quote_vault_balance_resp.ui_amount

            if base_vault_balance is None or quote_vault_balance is None:
                logging.error("One of the pool account balances is None.")
                return None

            if self.pool_keys.base_mint == base_mint:
                base_reserve = base_vault_balance
                quote_reserve = quote_vault_balance
            elif self.pool_keys.quote_mint == base_mint:
                base_reserve = quote_vault_balance
                quote_reserve = base_vault_balance
            else:
                logging.error(f"Invalid base mint address {base_mint} for pool {self.pair_address}")
                return None

            if quote_reserve == 0:
                logging.warning("Quote reserve is zero, cannot calculate price.")
                return None

            return base_reserve, quote_reserve
        except Exception as e:
            logging.error(f"Error calculating token price: {e}")
            return None

    async def get_token_price(self, solana_client: SolanaClient, base_mint: Pubkey = SOL_MINT) -> Optional[float]:
        reserves = await self.__get_base_quote_reserves(solana_client, base_mint)
        if reserves is None:
            return None
        base_reserve, quote_reserve = reserves
        return base_reserve / quote_reserve

    def make_swap_instruction(
        self,
        amount_in: int,
        minimum_amount_out: int,
        token_account_in: Pubkey,
        token_account_out: Pubkey,
        owner: Pubkey,
        input_mint: Pubkey,
    ) -> Optional[Instruction]:
        try:
            keys = [
                AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(pubkey=self.pair_address, is_signer=False, is_writable=True),
                AccountMeta(pubkey=RAY_AUTHORITY_V4, is_signer=False, is_writable=False),
                AccountMeta(pubkey=self.pool_keys.open_orders, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.pool_keys.target_orders, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.pool_keys.base_vault, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.pool_keys.quote_vault, is_signer=False, is_writable=True),
                AccountMeta(pubkey=OPEN_BOOK_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(pubkey=self.pool_keys.market_id, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.market_state.bids, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.market_state.asks, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.market_state.event_queue, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.market_state.base_vault, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.market_state.quote_vault, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.authority, is_signer=False, is_writable=False),
                AccountMeta(pubkey=token_account_in, is_signer=False, is_writable=True),
                AccountMeta(pubkey=token_account_out, is_signer=False, is_writable=True),
                AccountMeta(pubkey=owner, is_signer=True, is_writable=False)
            ]

            data = bytearray()
            discriminator = 9
            data.extend(struct.pack('<B', discriminator))
            data.extend(struct.pack('<Q', amount_in))
            data.extend(struct.pack('<Q', minimum_amount_out))
            swap_instruction = Instruction(AMM_V4_PROGRAM_ID, bytes(data), keys)

            return swap_instruction
        except Exception as e:
            print(f"Error occurred: {e}")
            return None

    async def calculate_received_quote_tokens(
        self,
        solana_client: SolanaClient,
        base_in: float,
        base_mint: Pubkey,
    ) -> Optional[float]:
        reserves = await self.__get_base_quote_reserves(solana_client, base_mint)
        if reserves is None:
            logging.error("Could not get base reserves while making buy instructions")
            return None

        base_reserve, quote_reserve = reserves

        swap_fee = self.pool_keys.swap_fee_numerator / self.pool_keys.swap_fee_denominator
        effective_used = base_in - (base_in * (swap_fee / 100))
        constant_product = base_reserve * quote_reserve
        updated_quote_vault_balance = constant_product / (base_reserve + effective_used)
        tokens_received = quote_reserve - updated_quote_vault_balance
        return round(tokens_received, 9)

    async def calculate_received_base_tokens(
        self,
        solana_client: SolanaClient,
        quote_in: float,
        base_mint: Pubkey,
    ) -> Optional[float]:
        reserves = await self.__get_base_quote_reserves(solana_client, base_mint)
        if reserves is None:
            logging.error("Could not get base reserves while making buy instructions")
            return None

        base_reserve, quote_reserve = reserves

        swap_fee = self.pool_keys.swap_fee_numerator / self.pool_keys.swap_fee_denominator
        effective_used = quote_in - (quote_in * (swap_fee / 100))
        constant_product = base_reserve * quote_reserve
        updated_base_vault_balance = constant_product / (quote_reserve + effective_used)
        tokens_received = base_reserve - updated_base_vault_balance
        return round(tokens_received, 9)

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
        base_in_count = base_in * (10 ** base_decimals)

        quote_out = await self.calculate_received_quote_tokens(
            solana_client,
            base_in,
            base_mint
        )
        if quote_out is None:
            return None

        quote_out_count = quote_out * (10 ** quote_decimals)

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
            close_token_account_instruction = close_account(
                CloseAccountParams(
                    program_id=TOKEN_PROGRAM_ID,
                    account=quote_token_account,
                    dest=payer_keypair.pubkey(),
                    owner=payer_keypair.pubkey(),
                )
            )
            instructions.append(close_token_account_instruction)

        return instructions

def decode_amm_v4_pool_keys(amm_data: bytes) -> Optional[AmmV4PoolKeys]:
    try:
        amm_data_decoded = AMM_V4_LAYOUT.parse(amm_data)
    except Exception as e:
        logging.error(f"Error parsing AMM data: {e}")
        return None

    try:
        return AmmV4PoolKeys.from_decoded(amm_data_decoded)
    except Exception as e:
        logging.error(f"Error constructing pool keys: {e}")
        return None


def decode_market_state_v3(market_data: bytes) -> Optional[MarketStateV3]:
    try:
        market_data_decoded = MARKET_STATE_LAYOUT_V3.parse(market_data)
    except Exception as e:
        logging.error(f"Error parsing AMM data: {e}")
        return None

    try:
        return MarketStateV3.from_decoded(market_data_decoded)
    except Exception as e:
        logging.error(f"Error constructing pool keys: {e}")
        return None

