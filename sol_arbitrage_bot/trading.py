import logging

from spl.token.instructions import (
    CloseAccountParams,
    InitializeAccountParams,
    close_account,
    create_associated_token_account,
    get_associated_token_address,
    initialize_account,
)

from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.system_program import (
    CreateAccountWithSeedParams,
    create_account_with_seed,
)

from .solana_client import SolanaClient


async def get_token_account(solana_client: SolanaClient, payer_keypair: Keypair, token_mint: Pubkey) -> Pubkey:
    token_account_check = await solana_client.get_token_accounts_by_owner(
        payer_keypair.pubkey(), token_mint,
    )
    if token_account_check is None:
        logging.error(f"Could not fetch owner's accounts {token_mint}")
        return None

    if token_account_check.value:
        token_account = token_account_check.value[0].pubkey
        create_token_account_instruction = None
        logging.info(f"Token account for {token_mint} found.")
    else:
        token_account = get_associated_token_address(payer_keypair.pubkey(), token_mint)
        create_token_account_instruction = create_associated_token_account(
            payer_keypair.pubkey(), payer_keypair.pubkey(), token_mint
        )
        logging.info(f"No existing token account for {token_mint} found; creating associated token account.")

    # TODO
