from solana.rpc.types import TxOpts

from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import MessageV0

from sol_arbitrage_bot.constants import UNIT_BUDGET, UNIT_PRICE
from sol_arbitrage_bot.accounts import *
from sol_arbitrage_bot.pool_base import LiquidityPool

from .solana_client import SolanaClient


def make_transaction_fee_instructions():
    return [
        set_compute_unit_limit(UNIT_BUDGET),
        set_compute_unit_price(UNIT_PRICE),
    ]

async def send_transaction(
    solana_client: SolanaClient,
    payer_keypair: Keypair,
    instructions: List[Instruction]
):
    latest_blockhash = await solana_client.get_latest_blockhash()
    if latest_blockhash is None:
        logging.error("error. no latest blockhash")
        return

    compiled_message = MessageV0.try_compile(
        payer_keypair.pubkey(),
        instructions,
        [],
        latest_blockhash.blockhash,
    )

    txn_sig = await solana_client.send_transaction(
        txn=VersionedTransaction(compiled_message, [payer_keypair]),
        opts=TxOpts(skip_preflight=True),
    )
    if txn_sig is None:
        logging.error("could not send transaction")
        return

    return txn_sig


async def arbitrage(
    solana_client: SolanaClient,
    buy_liquidity_pool: LiquidityPool,
    sell_liquidity_pool: LiquidityPool,
    payer_keypair: Keypair,
    base_in: float,
    base_mint: Pubkey = SOL_MINT,
):
    instructions = make_transaction_fee_instructions()

    quote_mint = buy_liquidity_pool.get_quote_mint(base_mint)
    if quote_mint is None:
        logging.error("invalid base mint")
        return

    base_quote_decimals = buy_liquidity_pool.get_base_quote_decimals(base_mint)
    if base_quote_decimals is None:
        logging.error("invalid base mint")
        return

    base_decimals, _ = base_quote_decimals
    base_in_count = int(base_in * (10 ** base_decimals))

    account_and_wsol_account_instructions = await create_and_init_wsol_account_instructions(
        solana_client, payer_keypair, base_in_count
    )
    if account_and_wsol_account_instructions is None:
        logging.error("Could not create and init wsol account while making buy instructions")
        return None

    wsol_token_account, wsol_account_instructions = account_and_wsol_account_instructions
    instructions.extend(wsol_account_instructions)

    token_account, create_token_account_instruction = await get_or_create_token_account(
        solana_client, payer_keypair, quote_mint
    )
    if create_token_account_instruction is not None:
        instructions.append(create_token_account_instruction)

    buy_instructions = await buy_liquidity_pool.make_buy_instructions(
        solana_client=solana_client,
        payer_keypair=payer_keypair,
        slippage=0.1,
        base_in=base_in,
        quote_token_account=token_account,
        base_token_account=wsol_token_account,
        base_mint=base_mint,
    )
    if buy_instructions is None:
        logging.error("could not create buy instruction")
        return

    instructions.extend(buy_instructions)

    sell_instructions = await sell_liquidity_pool.make_sell_instructions(
        solana_client=solana_client,
        payer_keypair=payer_keypair,
        slippage=1,
        percentage=100,
        quote_token_account=token_account,
        base_token_account=wsol_token_account,
        base_mint=SOL_MINT,
    )
    if sell_instructions is None:
        logging.error("could not create sell instruction")
        return

    instructions.extend(sell_instructions)

    instructions.append(close_account_instruction(wsol_token_account, payer_keypair))
    txn_sig = await send_transaction(solana_client, payer_keypair, instructions)
    return txn_sig

