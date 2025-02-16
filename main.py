import json
import asyncio
import argparse

from solana.rpc.types import TxOpts
from solders.transaction import VersionedTransaction
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.message import MessageV0
from solders.keypair import Keypair

from sol_arbitrage_bot.solana_client import SolanaClient
from sol_arbitrage_bot.raydium.raydium_fetcher import RaydiumFetcher
from sol_arbitrage_bot.raydium.liquidity_pool import fetch_liquidity_pool

from sol_arbitrage_bot.constants import SOL_DECIMALS, UNIT_BUDGET, UNIT_PRICE
from sol_arbitrage_bot.accounts import *



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Arbitrage bot")
    parser.add_argument(
        "--wallet",
        "-w",
        type=str,
        required=True,
        help="Path to wallet's keypair file"
    )
    return parser.parse_args()


async def main(wallet: str):
    with open(wallet, 'r') as file:
        wallet_keypair_data = json.load(file)
    payer_keypair = Keypair.from_bytes(bytes(wallet_keypair_data))
    print(payer_keypair.pubkey())

    amount_in = int(0.005 * (10 ** SOL_DECIMALS))
    async with SolanaClient() as solana_client:
        wsol_token_account, create_wsol_account_instruction, init_wsol_account_instruction = await create_and_init_wsol_account_instructions(
            solana_client, payer_keypair, amount_in,
        )
        if wsol_token_account is None:
            print("error. could not create wsol token account")
            return

        latest_blockhash = await solana_client.get_latest_blockhash()
        if latest_blockhash is None:
            print("error. no latest blockhash")
            return

        instructions = [
            set_compute_unit_limit(UNIT_BUDGET),
            set_compute_unit_price(UNIT_PRICE),
            create_wsol_account_instruction,
            init_wsol_account_instruction,
            close_wsol_account_instruction(wsol_token_account, payer_keypair),
        ]

        compiled_message = MessageV0.try_compile(
            payer_keypair.pubkey(),
            instructions,
            [],
            latest_blockhash.blockhash,
        )

        print("Sending transaction...")
        txn_sig = await solana_client.send_transaction(
            txn=VersionedTransaction(compiled_message, [payer_keypair]),
            opts=TxOpts(skip_preflight=True),
        )
        if txn_sig is None:
            print("error. could not send transaction")
            return

        print("Transaction Signature:", txn_sig)

    """ snai_token_mint = "Hjw6bEcHtbHGpQr8onG3izfJY5DJiWdt7uk2BfdSpump" """
    """ griffain_token_mint = "KENJSUYLASHUMfHyy5o4Hp2FdNqZg1AsUPhfH2kYvEP" """
    """ usdc_token_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" """
    """ token_mint = snai_token_mint """
    """ async with SolanaClient() as solana_client: """
    """     async with RaydiumFetcher() as raydium_fetcher: """
    """         for token_mint in [snai_token_mint]: """
    """             pools = await raydium_fetcher.fetch_top_lp_for_mint(token_mint, 3, 1) """
    """             if not pools: """
    """                 raise Exception() """
    """"""
    """             print(token_mint) """
    """             for pool in pools: """
    """                 pair_address = Pubkey.from_string(pool["id"]) """
    """                 liquidity_pool = await fetch_liquidity_pool(solana_client, pair_address) """
    """                 if liquidity_pool is not None: """
    """                     price = await liquidity_pool.get_token_price(solana_client) """
    """                     print("  ", price) """


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.wallet))
