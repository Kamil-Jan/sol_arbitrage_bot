import logging
import struct
from dataclasses import dataclass, field
from typing import Tuple, List, Optional

from solders.pubkey import Pubkey
from solders.instruction import AccountMeta, Instruction

from sol_arbitrage_bot.constants import SOL_MINT, TOKEN_PROGRAM_ID
from sol_arbitrage_bot.solana_client import SolanaClient
from sol_arbitrage_bot.raydium.pool_base import LiquidityPool

from .constants import CLMM_PROGRAM_ID, TOKEN_2022_PROGRAM_ID, MEMO_PROGRAM_V2
from .layouts import CLMM_LAYOUT


def convert_sqrt_price_x64_to_regular(sqrt_price_x64, decimalsA, decimalsB):
    decimals_adjustment = 10 ** (decimalsA - decimalsB)
    sqrt_price = sqrt_price_x64 / (2 ** 64)
    return sqrt_price ** 2 * decimals_adjustment


@dataclass
class RewardInfo:
    reward_state: int
    open_time: int
    end_time: int
    last_update_time: int
    emissions_per_second_x64: int
    reward_total_emissioned: int
    reward_claimed: int
    token_mint: Pubkey
    token_vault: Pubkey
    creator: Pubkey
    reward_growth_global_x64: int

    @classmethod
    def from_decoded(cls, decoded: dict) -> "RewardInfo":
        return cls(
            reward_state=decoded["rewardState"],
            open_time=decoded["openTime"],
            end_time=decoded["endTime"],
            last_update_time=decoded["lastUpdateTime"],
            emissions_per_second_x64=decoded["emissionsPerSecondX64"],
            reward_total_emissioned=decoded["rewardTotalEmissioned"],
            reward_claimed=decoded["rewardClaimed"],
            token_mint=Pubkey.from_bytes(decoded["tokenMint"]),
            token_vault=Pubkey.from_bytes(decoded["tokenVault"]),
            creator=Pubkey.from_bytes(decoded["creator"]),
            reward_growth_global_x64=decoded["rewardGrowthGlobalX64"],
        )

@dataclass
class ClmmPoolKeys:
    blob: bytes
    bump: int
    amm_config: Pubkey
    creator: Pubkey
    mint_a: Pubkey
    mint_b: Pubkey
    vault_a: Pubkey
    vault_b: Pubkey
    observation_id: Pubkey
    mint_decimals_a: int
    mint_decimals_b: int
    tick_spacing: int
    liquidity: int
    sqrt_price_x64: int
    tick_current: int
    unknown: int
    fee_growth_global_x64a: int
    fee_growth_global_x64b: int
    protocol_fees_token_a: int
    protocol_fees_token_b: int
    swap_in_amount_token_a: int
    swap_out_amount_token_b: int
    swap_in_amount_token_b: int
    swap_out_amount_token_a: int
    status: int
    unknown_seq: List[int] = field(default_factory=lambda: [0] * 7)
    reward_infos: List[RewardInfo] = field(default_factory=lambda: [None] * 3)
    tick_array_bitmap: List[int] = field(default_factory=lambda: [0] * 16)
    total_fees_token_a: int = 0
    total_fees_claimed_token_a: int = 0
    total_fees_token_b: int = 0
    total_fees_claimed_token_b: int = 0
    fund_fees_token_a: int = 0
    fund_fees_token_b: int = 0
    start_time: int = 0
    padding: List[int] = field(default_factory=lambda: [0] * 57)

    @classmethod
    def from_decoded(cls, decoded: dict) -> "ClmmPoolKeys":
        return cls(
            blob=decoded["blob"],
            bump=decoded["bump"],
            amm_config=Pubkey.from_bytes(decoded["ammConfig"]),
            creator=Pubkey.from_bytes(decoded["creator"]),
            mint_a=Pubkey.from_bytes(decoded["mintA"]),
            mint_b=Pubkey.from_bytes(decoded["mintB"]),
            vault_a=Pubkey.from_bytes(decoded["vaultA"]),
            vault_b=Pubkey.from_bytes(decoded["vaultB"]),
            observation_id=Pubkey.from_bytes(decoded["observationId"]),
            mint_decimals_a=decoded["mintDecimalsA"],
            mint_decimals_b=decoded["mintDecimalsB"],
            tick_spacing=decoded["tickSpacing"],
            liquidity=decoded["liquidity"],
            sqrt_price_x64=decoded["sqrtPriceX64"],
            tick_current=decoded["tickCurrent"],
            unknown=decoded["unknown"],
            fee_growth_global_x64a=decoded["feeGrowthGlobalX64A"],
            fee_growth_global_x64b=decoded["feeGrowthGlobalX64B"],
            protocol_fees_token_a=decoded["protocolFeesTokenA"],
            protocol_fees_token_b=decoded["protocolFeesTokenB"],
            swap_in_amount_token_a=decoded["swapInAmountTokenA"],
            swap_out_amount_token_b=decoded["swapOutAmountTokenB"],
            swap_in_amount_token_b=decoded["swapInAmountTokenB"],
            swap_out_amount_token_a=decoded["swapOutAmountTokenA"],
            status=decoded["status"],
            unknown_seq=decoded["unknown_seq"],
            reward_infos=[RewardInfo.from_decoded(r) for r in decoded["rewardInfos"]],
            tick_array_bitmap=decoded["tickArrayBitmap"],
            total_fees_token_a=decoded["totalFeesTokenA"],
            total_fees_claimed_token_a=decoded["totalFeesClaimedTokenA"],
            total_fees_token_b=decoded["totalFeesTokenB"],
            total_fees_claimed_token_b=decoded["totalFeesClaimedTokenB"],
            fund_fees_token_a=decoded["fundFeesTokenA"],
            fund_fees_token_b=decoded["fundFeesTokenB"],
            start_time=decoded["startTime"],
            padding=decoded["padding"],
        )


class ClmmPool(LiquidityPool):
    def __init__(self, pair_address: Pubkey, pool_keys: ClmmPoolKeys):
        self.pair_address = pair_address
        self.pool_keys = pool_keys

        """ tick_current = int(self.pool_keys.tick_current) """
        """ tick_spacing = int(self.pool_keys.tick_spacing) """
        """"""
        """ bitmap_extension = get_pda_tick_array_bitmap_extension(pool_state) """
        """ bitmap_ext_data = client.get_account_info_json_parsed(bitmap_extension, commitment=Processed).value.data """
        """ parsed_bitmap_ext_data = TickArrayBitmapExtension.parse(bitmap_ext_data) """
        """ positive_tick_array_bitmap = [list(container) for container in parsed_bitmap_ext_data.positive_tick_array_bitmap] """
        """ negative_tick_array_bitmap = [list(container) for container in parsed_bitmap_ext_data.negative_tick_array_bitmap] """
        """ tick_array_bitmap = list(parsed_pool_data.tick_array_bitmap) """
        """ tickarray_bitmap_extension = [positive_tick_array_bitmap, negative_tick_array_bitmap] """
        """ tick_array_keys = load_current_and_next_tick_arrays(pool_state, tick_current, tick_spacing, tick_array_bitmap, tickarray_bitmap_extension, zero_for_one) """
        """"""
        """ current_tick_array = tick_array_keys[0] """
        """ next_tick_array_1 = tick_array_keys[1] """
        """ next_tick_array_2 = tick_array_keys[2] """

    async def get_token_price(self, solana_client: SolanaClient, base_mint: Pubkey = SOL_MINT) -> Optional[float]:
        try:
            price = convert_sqrt_price_x64_to_regular(
                self.pool_keys.sqrt_price_x64,
                self.pool_keys.mint_decimals_a,
                self.pool_keys.mint_decimals_b,
            )

            if self.pool_keys.mint_a == base_mint:
                return 1 / price
            elif self.pool_keys.mint_b == base_mint:
                return price
            else:
                logging.error(f"Invalid base mint address {base_mint} for pool {self.pair_address}")
                return None
        except Exception as e:
            logging.error(f"Error calculating token price: {e}")
            return None

    async def get_quote_mint(self, base_mint: Pubkey) -> Optional[Pubkey]:
        if self.pool_keys.mint_a == base_mint:
            return self.pool_keys.mint_b
        elif self.pool_keys.mint_b == base_mint:
            return self.pool_keys.mint_a
        logging.error(f"Invalid base mint address {base_mint} for pool {self.pair_address}")
        return None

    async def get_base_quote_decimals(self, base_mint: Pubkey) -> Optional[Tuple[int, int]]:
        if self.pool_keys.mint_a == base_mint:
            base_decimals = self.pool_keys.mint_decimals_a
            quote_decimals = self.pool_keys.mint_decimals_b
        elif self.pool_keys.mint_b == base_mint:
            base_decimals = self.pool_keys.mint_decimals_b
            quote_decimals = self.pool_keys.mint_decimals_a
        else:
            logging.error(f"Invalid base mint address {base_mint} for pool {self.pair_address}")
            return None
        return base_decimals, quote_decimals

    async def calculate_received_quote_tokens(
        self,
        solana_client: SolanaClient,
        base_in: float,
        base_mint: Pubkey,
    ) -> Optional[float]:
        token_price = await self.get_token_price(solana_client, base_mint)
        if token_price is None:
            return None
        return round(base_in / token_price, 9)

    async def calculate_received_base_tokens(
        self,
        solana_client: SolanaClient,
        quote_in: float,
        base_mint: Pubkey,
    ) -> Optional[float]:
        token_price = await self.get_token_price(solana_client, base_mint)
        if token_price is None:
            return None
        return round(quote_in * token_price, 9)

    """ def make_swap_instruction( """
    """     self, """
    """     amount_in: int, """
    """     minimum_amount_out: int, """
    """     token_account_in: Pubkey, """
    """     token_account_out: Pubkey, """
    """     owner: Pubkey, """
    """     input_mint: Pubkey, """
    """ ) -> Optional[Instruction]: """
    """     try: """
    """         if token_in_mint == self.pool_keys.mint_a: """
    """             input_vault = self.pool_keys.vault_a """
    """             output_vault = self.pool_keys.vault_b """
    """             output_mint = self.pool_keys.mint_b """
    """         elif token_in_mint == self.pool_keys.mint_b """
    """             input_vault = self.pool_keys.vault_b """
    """             output_vault = self.pool_keys.vault_a """
    """             output_mint = self.pool_keys.mint_a """
    """         else: """
    """             logging.error(f"Invalid token in mint address {token_in_mint} for pool {self.pair_address}") """
    """             return None """
    """"""
    """         keys = [ """
    """             AccountMeta(pubkey=owner, is_signer=True, is_writable=True), """
    """             AccountMeta(pubkey=self.pool_keys.amm_config, is_signer=False, is_writable=False), """
    """             AccountMeta(pubkey=self.pair_address, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=token_account_in, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=token_account_out, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=input_vault, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=output_vault, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=self.pool_keys.observation_id, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False), """
    """             AccountMeta(pubkey=TOKEN_2022_PROGRAM_ID, is_signer=False, is_writable=False), """
    """             AccountMeta(pubkey=MEMO_PROGRAM_V2, is_signer=False, is_writable=False), """
    """             AccountMeta(pubkey=input_mint, is_signer=False, is_writable=False), """
    """             AccountMeta(pubkey=output_mint, is_signer=False, is_writable=False), """
    """             AccountMeta(pubkey=accounts.current_tick_array, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=accounts.bitmap_extension, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=accounts.next_tick_array_1, is_signer=False, is_writable=True), """
    """             AccountMeta(pubkey=accounts.next_tick_array_2, is_signer=False, is_writable=True) """
    """         ] """
    """"""
    """         data = bytearray() """
    """         data.extend(bytes.fromhex("2b04ed0b1ac91e62")) #SWAP V2 """
    """         data.extend(struct.pack('<Q', amount_in)) """
    """         data.extend(struct.pack('<Q', 0)) """
    """         data.extend((0).to_bytes(16, byteorder='little')) """
    """         data.extend(struct.pack('<?', True)) """
    """         swap_instruction = Instruction(Pubkey.from_string("CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"), bytes(data), keys) """
    """"""
    """         return swap_instruction """
    """     except Exception as e: """
    """         print(f"Error occurred: {e}") """
    """         return None """


def decode_clmm_pool_keys(clmm_data: bytes) -> Optional[ClmmPoolKeys]:
    try:
        clmm_data_decoded = CLMM_LAYOUT.parse(clmm_data)
    except Exception as e:
        logging.error(f"Error parsing AMM data: {e}")
        return None

    try:
        return ClmmPoolKeys.from_decoded(clmm_data_decoded)
    except Exception as e:
        logging.error(f"Error constructing pool keys: {e}")
        return None

