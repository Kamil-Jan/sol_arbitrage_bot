import base58
from solana.rpc.types import TxOpts

from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.system_program import transfer, TransferParams
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import MessageV0

from jito_async import JitoJsonRpcSDK

from sol_arbitrage_bot.constants import UNIT_BUDGET, UNIT_PRICE
from sol_arbitrage_bot.accounts import *
from sol_arbitrage_bot.pool_base import LiquidityPool

from .solana_client import SolanaClient


def make_transaction_fee_instructions():
    return [
        set_compute_unit_limit(UNIT_BUDGET),
        set_compute_unit_price(UNIT_PRICE),
    ]


def compile_transaction(
    payer_keypair: Keypair,
    instructions: List[Instruction],
    latest_blockhash,
) -> VersionedTransaction:

    compiled_message = MessageV0.try_compile(
        payer_keypair.pubkey(),
        instructions,
        [],
        latest_blockhash.blockhash,
    )

    return VersionedTransaction(compiled_message, [payer_keypair])


async def create_tip_instruction(
    jito_client: JitoJsonRpcSDK,
    payer_keypair: Keypair,
    tip_amount: int,
) -> Optional[Instruction]:
    tip_account_str = await jito_client.get_random_tip_account()
    if tip_account_str is None:
        return None

    tip_account = Pubkey.from_string(tip_account_str)

    transfer_ix = transfer(
        TransferParams(
            from_pubkey=payer_keypair.pubkey(),
            to_pubkey=tip_account,
            lamports=tip_amount
        )
    )

    return transfer_ix


async def send_bundle_transaction(
    jito_client: JitoJsonRpcSDK,
    txns: List[VersionedTransaction],
    tip_txn: VersionedTransaction,
):
    # Serialize and base58-encode each transaction.
    encoded_txns = [
        base58.b58encode(bytes(tx)).decode("ascii")
        for tx in txns
    ]
    # Serialize and encode the tip transaction.
    encoded_tip = base58.b58encode(bytes(tip_txn)).decode("utf-8")
    # Append the tip as the last transaction.
    encoded_txns.append(encoded_tip)

    # Use the client to send the bundle.
    bundle_id = await jito_client.send_bundle(encoded_txns)
    return bundle_id


async def create_token_account(
    solana_client: SolanaClient,
    payer_keypair: Keypair,
    mint: Pubkey,
):
    instructions = make_transaction_fee_instructions()
    _, create_token_account_instruction = await get_or_create_token_account(
        solana_client, payer_keypair, mint
    )
    if create_token_account_instruction is None:
        print("token account already created")
        return

    latest_blockhash = await solana_client.get_latest_blockhash()
    if latest_blockhash is None:
        logging.error("error. no latest blockhash")
        return

    txn = compile_transaction(payer_keypair, instructions, latest_blockhash)

    instructions.append(create_token_account_instruction)
    txn_sig = await solana_client.send_transaction(txn, TxOpts(skip_preflight=True))
    return txn_sig


async def arbitrage(
    solana_client: SolanaClient,
    jito_client: JitoJsonRpcSDK,
    buy_liquidity_pool: LiquidityPool,
    sell_liquidity_pool: LiquidityPool,
    payer_keypair: Keypair,
    base_in: float,
    base_mint: Pubkey = SOL_MINT,
    bundle: bool = False,
):
    buy_arb_instructions = make_transaction_fee_instructions()

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
    buy_arb_instructions.extend(wsol_account_instructions)

    token_account, create_token_account_instruction = await get_or_create_token_account(
        solana_client, payer_keypair, quote_mint
    )
    if create_token_account_instruction is not None:
        logging.error("Create quote token account")
        return

    min_quote_out_buy_instructions = await buy_liquidity_pool.make_buy_instructions(
        solana_client=solana_client,
        payer_keypair=payer_keypair,
        slippage=0,
        base_in=base_in,
        quote_token_account=token_account,
        base_token_account=wsol_token_account,
        base_mint=base_mint,
    )
    if min_quote_out_buy_instructions is None:
        logging.error("could not create buy instruction")
        return

    min_quote_out, buy_instructions = min_quote_out_buy_instructions
    buy_arb_instructions.extend(buy_instructions)

    print(base_in, min_quote_out)

    """ # sell transaction """
    sell_arb_instructions = make_transaction_fee_instructions()

    sell_instructions = await sell_liquidity_pool.make_sell_instructions(
        solana_client=solana_client,
        payer_keypair=payer_keypair,
        slippage=0,
        quote_in=min_quote_out * 0.95,
        quote_token_account=token_account,
        base_token_account=wsol_token_account,
        base_mint=SOL_MINT,
    )
    if sell_instructions is None:
        logging.error("could not create sell instruction")
        return

    sell_arb_instructions.extend(sell_instructions)
    sell_arb_instructions.append(close_account_instruction(wsol_token_account, payer_keypair))

    if bundle:
        tip_instruction = await create_tip_instruction(jito_client, payer_keypair, 1000)
        if tip_instruction is None:
            return
        sell_arb_instructions.append(tip_instruction)

    latest_blockhash = await solana_client.get_latest_blockhash()
    if latest_blockhash is None:
        logging.error("error. no latest blockhash")
        return

    buy_arb_txn = compile_transaction(
        payer_keypair,
        buy_arb_instructions,
        latest_blockhash
    )
    sell_arb_txn = compile_transaction(
        payer_keypair,
        sell_arb_instructions,
        latest_blockhash
    )
    arb_txns = [buy_arb_txn, sell_arb_txn]

    if bundle:
        encoded_txns = [
            base58.b58encode(bytes(arb_txn)).decode("ascii")
            for arb_txn in arb_txns
        ]

        bundle_id = await jito_client.send_bundle(encoded_txns)
        return bundle_id

    for txn in arb_txns:
        txn_sig = await solana_client.send_transaction(
            txn,
            TxOpts(skip_preflight=True)
        )
        print(txn_sig)


