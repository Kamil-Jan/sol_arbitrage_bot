from construct import *
from construct import Struct as cStruct

EXTENSION_TICKARRAY_BITMAP_SIZE = 14

REWARD_INFO = cStruct(
    "rewardState" / Int8ul,
    "openTime" / Int64ul,
    "endTime" / Int64ul,
    "lastUpdateTime" / Int64ul,
    "emissionsPerSecondX64" / BytesInteger(16, signed=False, swapped=True),
    "rewardTotalEmissioned" / Int64ul,
    "rewardClaimed" / Int64ul,
    "tokenMint" / Bytes(32),
    "tokenVault" / Bytes(32),
    "creator" / Bytes(32),
    "rewardGrowthGlobalX64" / BytesInteger(16, signed=False, swapped=True)
)

CLMM_LAYOUT = cStruct(
    "blob" / Bytes(8),
    "bump" / Int8ul,
    "ammConfig" / Bytes(32),
    "creator" / Bytes(32),
    "mintA" / Bytes(32),
    "mintB" / Bytes(32),
    "vaultA" / Bytes(32),
    "vaultB" / Bytes(32),
    "observationId" / Bytes(32),
    "mintDecimalsA" / Int8ul,
    "mintDecimalsB" / Int8ul,
    "tickSpacing" / Int16ul,
    "liquidity" / BytesInteger(16, signed=False, swapped=True),
    "sqrtPriceX64" / BytesInteger(16, signed=False, swapped=True),
    "tickCurrent" / Int32sl,
    "unknown" / Int32ul,
    "feeGrowthGlobalX64A" / BytesInteger(16, signed=False, swapped=True),
    "feeGrowthGlobalX64B" / BytesInteger(16, signed=False, swapped=True),
    "protocolFeesTokenA" / Int64ul,
    "protocolFeesTokenB" / Int64ul,
    "swapInAmountTokenA" / BytesInteger(16, signed=False, swapped=True),
    "swapOutAmountTokenB" / BytesInteger(16, signed=False, swapped=True),
    "swapInAmountTokenB" / BytesInteger(16, signed=False, swapped=True),
    "swapOutAmountTokenA" / BytesInteger(16, signed=False, swapped=True),
    "status" / Int8ul,
    "unknown_seq" / Array(7, Int8ul),
    "rewardInfos" / Array(3, REWARD_INFO),
    "tickArrayBitmap" / Array(16, Int64ul),
    "totalFeesTokenA" / Int64ul,
    "totalFeesClaimedTokenA" / Int64ul,
    "totalFeesTokenB" / Int64ul,
    "totalFeesClaimedTokenB" / Int64ul,
    "fundFeesTokenA" / Int64ul,
    "fundFeesTokenB" / Int64ul,
    "startTime" / Int64ul,
    "padding" / Array(57, Int64ul)
)

TICK_ARRAY_BITMAP_EXTENSION = Struct(
    Padding(8),
    "pool_id" / Bytes(32),
    "positive_tick_array_bitmap" / Array(
        EXTENSION_TICKARRAY_BITMAP_SIZE,
        Array(8, Int64ul)
    ),
    "negative_tick_array_bitmap" / Array(
        EXTENSION_TICKARRAY_BITMAP_SIZE,
        Array(8, Int64ul)
    )
)
