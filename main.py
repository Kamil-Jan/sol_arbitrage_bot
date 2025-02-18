import json
import asyncio
import argparse

from solders.pubkey import Pubkey
from solders.keypair import Keypair

from sol_arbitrage_bot.solana_client import SolanaClient
from sol_arbitrage_bot.raydium.raydium_fetcher import RaydiumFetcher
from sol_arbitrage_bot.raydium.liquidity_pool import fetch_liquidity_pool
from sol_arbitrage_bot.arbitrage import *
from sol_arbitrage_bot.accounts import *
from sol_arbitrage_bot.constants import SOL_RPC_URL


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Arbitrage bot")
    parser.add_argument(
        "--wallet",
        "-w",
        type=str,
        required=True,
        help="Path to wallet's keypair file"
    )
    parser.add_argument(
        "--rpc-url",
        "-r",
        type=str,
        required=False,
        default=SOL_RPC_URL,
        help="Solana RPC"
    )
    return parser.parse_args()


async def main(wallet: str, rpc_url: str):
    with open(wallet, 'r') as file:
        wallet_keypair_data = json.load(file)
    payer_keypair = Keypair.from_bytes(bytes(wallet_keypair_data))
    print("payer pubkey", payer_keypair.pubkey())

    snai_token_mint = "Hjw6bEcHtbHGpQr8onG3izfJY5DJiWdt7uk2BfdSpump"
    griffain_token_mint = "KENJSUYLASHUMfHyy5o4Hp2FdNqZg1AsUPhfH2kYvEP"
    usdc_token_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    token_mint = snai_token_mint
    async with SolanaClient(rpc_url=rpc_url) as solana_client:
        async with RaydiumFetcher() as raydium_fetcher:
            for token_mint in [snai_token_mint]:
                pools = await raydium_fetcher.fetch_top_lp_for_mint(token_mint, 3, 1)
                if not pools or len(pools) == 0:
                    raise Exception()

        print("token mint", token_mint)
        pool = pools[0]
        pair_address = Pubkey.from_string(pool["id"])
        liquidity_pool = await fetch_liquidity_pool(solana_client, pair_address)
        if liquidity_pool is None:
            print("could not fetch liquidity pool")
            return

        #price = await liquidity_pool.get_token_price(solana_client)
        #print("price", price)

        instructions = make_transaction_fee_instructions()
        account_and_wsol_account_instructions = await create_and_init_wsol_account_instructions(
            solana_client, payer_keypair, 0
        )
        if account_and_wsol_account_instructions is None:
            print("Could not create and init wsol account while making buy instructions")
            return None
        wsol_token_account, wsol_account_instructions = account_and_wsol_account_instructions
        instructions.extend(wsol_account_instructions)

        token_account, create_token_account_instruction = await get_or_create_token_account(
            solana_client, payer_keypair, Pubkey.from_string(token_mint)
        )
        if create_token_account_instruction is not None:
            print("no such token")
            return None

        sell_instructions = await liquidity_pool.make_sell_instructions(
            solana_client=solana_client,
            payer_keypair=payer_keypair,
            slippage=1,
            percentage=100,
            quote_token_account=token_account,
            base_token_account=wsol_token_account,
            base_mint=SOL_MINT,
        )
        if sell_instructions is None:
            print("cannot create sell instructions")
            return

        instructions.extend(sell_instructions)
        instructions.append(close_wsol_account_instruction(wsol_token_account, payer_keypair))
        txn_sig = await send_transaction(solana_client, payer_keypair, instructions)
        print("okay", txn_sig)


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.wallet, args.rpc_url))

