import logging
import base64
import os
from typing import Tuple, Optional

from spl.token.instructions import (
    CloseAccountParams,
    InitializeAccountParams,
    close_account,
    create_associated_token_account,
    get_associated_token_address,
    initialize_account,
)
from spl.token.client import AsyncToken

from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.system_program import (
    CreateAccountWithSeedParams,
    create_account_with_seed,
)

from .solana_client import SolanaClient
from .constants import SOL_MINT, TOKEN_PROGRAM_ID, ACCOUNT_LAYOUT_LEN


async def get_or_create_token_account(solana_client: SolanaClient, payer_keypair: Keypair, mint: Pubkey) -> Tuple[Pubkey, Optional[object]]:
    token_account_check = await solana_client.get_token_accounts_by_owner(
        payer_keypair.pubkey(), mint,
    )
    if token_account_check is not None:
        logging.info(f"Token account for {mint} found")
        token_account = token_account_check[0].pubkey
        return token_account, None
    else:
        logging.info(f"Token account for {mint} is not found. Creating instruction")
        token_account = get_associated_token_address(payer_keypair.pubkey(), mint)
        create_instruction = create_associated_token_account(
            payer_keypair.pubkey(), payer_keypair.pubkey(), mint
        )
        return token_account, create_instruction


async def create_and_init_wsol_account(solana_client: SolanaClient, payer_keypair: Keypair, mint: Pubkey, amount_in: int) -> Tuple[Pubkey, object, object]:
    seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
    wsol_token_account = Pubkey.create_with_seed(
        payer_keypair.pubkey(), seed, TOKEN_PROGRAM_ID
    )
    balance_needed = await AsyncToken.get_min_balance_rent_for_exempt_for_account(solana_client.client)
    if balance_needed is None:
        logging.error(f"Could not get get_min_balance_rent_for_exempt_for_account")
        return None

    create_wsol_instruction = create_account_with_seed(
        CreateAccountWithSeedParams(
            from_pubkey=payer_keypair.pubkey(),
            to_pubkey=wsol_token_account,
            base=payer_keypair.pubkey(),
            seed=seed,
            lamports=int(balance_needed + amount_in),
            space=ACCOUNT_LAYOUT_LEN,
            owner=TOKEN_PROGRAM_ID,
        )
    )
    init_wsol_instruction = initialize_account(
        InitializeAccountParams(
            program_id=TOKEN_PROGRAM_ID,
            account=wsol_token_account,
            mint=SOL_MINT,
            owner=payer_keypair.pubkey(),
        )
    )
    return wsol_token_account, create_wsol_instruction, init_wsol_instruction
