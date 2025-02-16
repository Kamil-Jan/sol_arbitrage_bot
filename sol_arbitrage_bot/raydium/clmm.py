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
    def from_decoded(cls, parsed: dict) -> "RewardInfo":
        return cls(
            reward_state=parsed["rewardState"],
            open_time=parsed["openTime"],
            end_time=parsed["endTime"],
            last_update_time=parsed["lastUpdateTime"],
            emissions_per_second_x64=parsed["emissionsPerSecondX64"],
            reward_total_emissioned=parsed["rewardTotalEmissioned"],
            reward_claimed=parsed["rewardClaimed"],
            token_mint=Pubkey.from_bytes(parsed["tokenMint"]),
            token_vault=Pubkey.from_bytes(parsed["tokenVault"]),
            creator=Pubkey.from_bytes(parsed["creator"]),
            reward_growth_global_x64=parsed["rewardGrowthGlobalX64"],
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
    def from_decoded(cls, parsed: dict) -> "ClmmPoolKeys":
        return cls(
            blob=parsed["blob"],
            bump=parsed["bump"],
            amm_config=Pubkey.from_bytes(parsed["ammConfig"]),
            creator=Pubkey.from_bytes(parsed["creator"]),
            mint_a=Pubkey.from_bytes(parsed["mintA"]),
            mint_b=Pubkey.from_bytes(parsed["mintB"]),
            vault_a=Pubkey.from_bytes(parsed["vaultA"]),
            vault_b=Pubkey.from_bytes(parsed["vaultB"]),
            observation_id=Pubkey.from_bytes(parsed["observationId"]),
            mint_decimals_a=parsed["mintDecimalsA"],
            mint_decimals_b=parsed["mintDecimalsB"],
            tick_spacing=parsed["tickSpacing"],
            liquidity=parsed["liquidity"],
            sqrt_price_x64=parsed["sqrtPriceX64"],
            tick_current=parsed["tickCurrent"],
            unknown=parsed["unknown"],
            fee_growth_global_x64a=parsed["feeGrowthGlobalX64A"],
            fee_growth_global_x64b=parsed["feeGrowthGlobalX64B"],
            protocol_fees_token_a=parsed["protocolFeesTokenA"],
            protocol_fees_token_b=parsed["protocolFeesTokenB"],
            swap_in_amount_token_a=parsed["swapInAmountTokenA"],
            swap_out_amount_token_b=parsed["swapOutAmountTokenB"],
            swap_in_amount_token_b=parsed["swapInAmountTokenB"],
            swap_out_amount_token_a=parsed["swapOutAmountTokenA"],
            status=parsed["status"],
            unknown_seq=parsed["unknown_seq"],
            reward_infos=[RewardInfo.from_decoded(r) for r in parsed["rewardInfos"]],
            tick_array_bitmap=parsed["tickArrayBitmap"],
            total_fees_token_a=parsed["totalFeesTokenA"],
            total_fees_claimed_token_a=parsed["totalFeesClaimedTokenA"],
            total_fees_token_b=parsed["totalFeesTokenB"],
            total_fees_claimed_token_b=parsed["totalFeesClaimedTokenB"],
            fund_fees_token_a=parsed["fundFeesTokenA"],
            fund_fees_token_b=parsed["fundFeesTokenB"],
            start_time=parsed["startTime"],
            padding=parsed["padding"],
        )


class ClmmPool(LiquidityPool):
    def __init__(self, pair_address: Pubkey, pool_keys: ClmmPoolKeys):
        self.pair_address = pair_address
        self.pool_keys = pool_keys

    async def get_token_price(self, solana_client: SolanaClient, base_mint_address: str = SOL_MINT) -> Optional[float]:
        """
        Calculates the token price based on the given pool's reserves.
        """
        try:
            price = convert_sqrt_price_x64_to_regular(
                self.pool_keys.sqrt_price_x64,
                self.pool_keys.mint_decimals_a,
                self.pool_keys.mint_decimals_b,
            )

            base_mint_pubkey = Pubkey.from_string(base_mint_address)
            if self.pool_keys.mint_a == base_mint_pubkey:
                return 1 / price
            elif self.pool_keys.mint_b == base_mint_pubkey:
                return price
            else:
                logging.error(f"Invalid base mint address {base_mint_address} for pool {self.pair_address}")
                return None
        except Exception as e:
            logging.error(f"Error calculating token price: {e}")
            return None


def decode_clmm_pool(pair_address: Pubkey, clmm_data: bytes) -> ClmmPool:
    try:
        clmm_data_decoded = CLMM_LAYOUT.parse(clmm_data)
    except Exception as e:
        logging.error(f"Error parsing AMM data: {e}")
        return None

    try:
        return ClmmPool(pair_address, ClmmPoolKeys.from_decoded(clmm_data_decoded))
    except Exception as e:
        logging.error(f"Error constructing pool keys: {e}")
        return None
