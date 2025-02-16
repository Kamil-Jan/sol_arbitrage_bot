import logging
from dataclasses import dataclass, field
from typing import List, Optional

from solders.pubkey import Pubkey

from sol_arbitrage_bot.constants import SOL_MINT
from sol_arbitrage_bot.solana_client import SolanaClient

from .pool_base import LiquidityPool
from .layouts import CLMM_LAYOUT


CLMM_PROGRAM_ID = Pubkey.from_string("CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK")


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

    async def get_token_price(self, solana_client: SolanaClient, base_mint: Pubkey = SOL_MINT) -> Optional[float]:

        """
        Calculates the token price based on the given pool's reserves.
        """
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


def decode_clmm_pool_keys(pair_address: Pubkey, clmm_data: bytes) -> Optional[ClmmPoolKeys]:
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
