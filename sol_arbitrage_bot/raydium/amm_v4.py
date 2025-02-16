import logging
import struct
from dataclasses import dataclass, field
from typing import List, Optional

from solders.pubkey import Pubkey
from solders.instruction import AccountMeta, Instruction

from sol_arbitrage_bot.constants import SOL_MINT, TOKEN_PROGRAM_ID
from sol_arbitrage_bot.solana_client import SolanaClient

from .pool_base import LiquidityPool
from .layouts import AMM_V4_LAYOUT


AMM_V4_PROGRAM_ID = Pubkey.from_string("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
RAY_AUTHORITY_V4 = Pubkey.from_string("5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1")
OPEN_BOOK_PROGRAM = Pubkey.from_string("srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX")

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


class AmmV4Pool(LiquidityPool):
    def __init__(self, pair_address: Pubkey, pool_keys: AmmV4PoolKeys):
        self.pair_address = pair_address
        self.pool_keys = pool_keys

    async def get_token_price(self, solana_client: SolanaClient, base_mint: Pubkey = SOL_MINT) -> Optional[float]:
        """
        Calculates the token price based on the given pool's reserves.
        """
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

            return base_reserve / quote_reserve
        except Exception as e:
            logging.error(f"Error calculating token price: {e}")
            return None

    """ def make_v4_swap_instruction( """
    """     self, """
    """     amount_in: int, """
    """     minimum_amount_out: int, """
    """     token_account_in: Pubkey, """
    """     token_account_out: Pubkey, """
    """     owner: Pubkey """
    """ ) -> Optional[Instruction]: """
    """     try: """
    """         keys = [ """
    """             AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False), """
    """             AccountMeta(pubkey=self.pair_address, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=RAY_AUTHORITY_V4, is_signer=False, is_writable=False), """
    """             AccountMeta(pubkey=self.pool_keys.open_orders, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=self.pool_keys.target_orders, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=self.pool_keys.base_vault, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=self.pool_keys.quote_vault, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=OPEN_BOOK_PROGRAM, is_signer=False, is_writable=False), """
    """             AccountMeta(pubkey=self.pool_keys.market_id, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=self.pool_keys.bids, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=self.pool_keys.asks, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=self.pool_keys.event_queue, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=self.pool_keys.market_base_vault, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=self.pool_keys.market_quote_vault, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=self.pool_keys.market_authority, is_signer=False, is_writable=False), """
    """             AccountMeta(pubkey=token_account_in, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=token_account_out, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=owner, is_signer=True, is_writable=False) """
    """         ] """
    """"""
    """         data = bytearray() """
    """         discriminator = 9 """
    """         data.extend(struct.pack('<B', discriminator)) """
    """         data.extend(struct.pack('<Q', amount_in)) """
    """         data.extend(struct.pack('<Q', minimum_amount_out)) """
    """         swap_instruction = Instruction(AMM_V4_PROGRAM_ID, bytes(data), keys) """
    """"""
    """         return swap_instruction """
    """     except Exception as e: """
    """         print(f"Error occurred: {e}") """
    """         return None """


def decode_amm_v4_pool(pair_address: Pubkey, amm_data: bytes) -> Optional[AmmV4Pool]:
    try:
        amm_data_decoded = AMM_V4_LAYOUT.parse(amm_data)
    except Exception as e:
        logging.error(f"Error parsing AMM data: {e}")
        return None

    try:
        return AmmV4Pool(pair_address, AmmV4PoolKeys.from_decoded(amm_data_decoded))
    except Exception as e:
        logging.error(f"Error constructing pool keys: {e}")
        return None
