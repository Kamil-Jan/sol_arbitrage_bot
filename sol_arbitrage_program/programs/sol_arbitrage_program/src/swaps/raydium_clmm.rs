use anchor_lang::prelude::*;
use anchor_lang::solana_program::{
    instruction::{AccountMeta, Instruction},
    program::invoke,
};
use anchor_lang::Accounts;

use anchor_spl::token::{TokenAccount, ID as TOKEN_PROGRAM_ID};

use crate::state::SwapState;

pub const CLMM_PROGRAM_ID: Pubkey = pubkey!("CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK");
pub const TOKEN_2022_PROGRAM_ID: Pubkey = pubkey!("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb");
pub const MEMO_PROGRAM_V2: Pubkey = pubkey!("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr");

#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct RaydiumClmmSwapData {
    /// Fixed 8-byte discriminator for SWAP V2 (hex: 2b04ed0b1ac91e62)
    pub instruction: [u8; 8],
    pub amount_in: u64,
    pub minimum_amount_out: u64,
    /// 16 bytes of extra zeros
    pub extra: [u8; 16],
    pub flag: bool,
}

#[derive(Accounts)]
pub struct RaydiumClmmSwap<'info> {
    /// CHECK: The owner must sign the transaction. No additional checks are needed because
    /// Anchor verifies that this account is a signer.
    #[account(mut)]
    pub owner: Signer<'info>,

    /// CHECK: This is the AMM config account. Its data is not deserialized here;
    /// only its address is used for CPI, so no further checks are necessary.
    pub amm_config: UncheckedAccount<'info>,

    /// CHECK: The pair address is only used for its key in the CPI call.
    #[account(mut)]
    pub pair_address: UncheckedAccount<'info>,

    // These accounts are deserialized into TokenAccount, ensuring data integrity.
    #[account(mut)]
    pub token_account_in: Account<'info, TokenAccount>,

    #[account(mut)]
    pub token_account_out: Account<'info, TokenAccount>,

    /// CHECK: The input vault is not deserialized because only its address is used.
    #[account(mut)]
    pub input_vault: UncheckedAccount<'info>,

    /// CHECK: The output vault is not deserialized because only its address is used.
    #[account(mut)]
    pub output_vault: UncheckedAccount<'info>,

    /// CHECK: The observation_id account is only needed for its key.
    #[account(mut)]
    pub observation_id: UncheckedAccount<'info>,

    /// CHECK: This is the SPL Token program. Its address is enforced via the constraint.
    #[account(address = TOKEN_PROGRAM_ID)]
    pub token_program: AccountInfo<'info>,

    /// CHECK: This is the Token 2022 program. Its address is enforced via the constraint.
    #[account(address = TOKEN_2022_PROGRAM_ID)]
    pub token_2022_program: AccountInfo<'info>,

    /// CHECK: This is the Memo program (v2). Its address is enforced via the constraint.
    #[account(address = MEMO_PROGRAM_V2)]
    pub memo_program: AccountInfo<'info>,

    /// CHECK: The input mint account is only used for its key.
    pub input_mint: UncheckedAccount<'info>,

    /// CHECK: The output mint account is only used for its key.
    pub output_mint: UncheckedAccount<'info>,

    /// CHECK: The current tick array account is used solely by its key.
    #[account(mut)]
    pub current_tick_array: UncheckedAccount<'info>,

    /// CHECK: The bitmap extension account is used solely by its key.
    #[account(mut)]
    pub bitmap_extension: UncheckedAccount<'info>,

    /// CHECK: The next tick array A is used solely by its key.
    #[account(mut)]
    pub next_tick_array_a: UncheckedAccount<'info>,

    /// CHECK: The next tick array B is used solely by its key.
    #[account(mut)]
    pub next_tick_array_b: UncheckedAccount<'info>,

    /// CHECK: The swap state account is validated via its seeds and bump; its data is
    /// deserialized as a SwapState.
    #[account(mut, seeds = [b"swap_state"], bump)]
    pub swap_state: Account<'info, SwapState>,
}

pub fn _raydium_clmm_swap<'info>(
    ctx: &Context<'_, '_, '_, 'info, RaydiumClmmSwap<'info>>,
    amount_in: u64,
) -> Result<()> {
    // The instruction field is fixed to hex: 2b04ed0b1ac91e62.
    let data = RaydiumClmmSwapData {
        instruction: [0x2b, 0x04, 0xed, 0x0b, 0x1a, 0xc9, 0x1e, 0x62],
        amount_in,
        minimum_amount_out: 0,
        extra: [0u8; 16],
        flag: true,
    };

    let instruction = Instruction {
        program_id: CLMM_PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(ctx.accounts.owner.key(), true),
            AccountMeta::new_readonly(ctx.accounts.amm_config.key(), false),
            AccountMeta::new(ctx.accounts.pair_address.key(), false),
            AccountMeta::new(ctx.accounts.token_account_in.key(), false),
            AccountMeta::new(ctx.accounts.token_account_out.key(), false),
            AccountMeta::new(ctx.accounts.input_vault.key(), false),
            AccountMeta::new(ctx.accounts.output_vault.key(), false),
            AccountMeta::new(ctx.accounts.observation_id.key(), false),
            AccountMeta::new_readonly(ctx.accounts.token_program.key(), false),
            AccountMeta::new_readonly(ctx.accounts.token_2022_program.key(), false),
            AccountMeta::new_readonly(ctx.accounts.memo_program.key(), false),
            AccountMeta::new_readonly(ctx.accounts.input_mint.key(), false),
            AccountMeta::new_readonly(ctx.accounts.output_mint.key(), false),
            AccountMeta::new(ctx.accounts.current_tick_array.key(), false),
            AccountMeta::new(ctx.accounts.bitmap_extension.key(), false),
            AccountMeta::new(ctx.accounts.next_tick_array_a.key(), false),
            AccountMeta::new(ctx.accounts.next_tick_array_b.key(), false),
        ],
        data: data.try_to_vec()?,
    };

    let account_infos = [
        ctx.accounts.owner.to_account_info(),
        ctx.accounts.amm_config.to_account_info(),
        ctx.accounts.pair_address.to_account_info(),
        ctx.accounts.token_account_in.to_account_info(),
        ctx.accounts.token_account_out.to_account_info(),
        ctx.accounts.input_vault.to_account_info(),
        ctx.accounts.output_vault.to_account_info(),
        ctx.accounts.observation_id.to_account_info(),
        ctx.accounts.token_program.to_account_info(),
        ctx.accounts.token_2022_program.to_account_info(),
        ctx.accounts.memo_program.to_account_info(),
        ctx.accounts.input_mint.to_account_info(),
        ctx.accounts.output_mint.to_account_info(),
        ctx.accounts.current_tick_array.to_account_info(),
        ctx.accounts.bitmap_extension.to_account_info(),
        ctx.accounts.next_tick_array_a.to_account_info(),
        ctx.accounts.next_tick_array_b.to_account_info(),
    ];

    invoke(&instruction, &account_infos)?;

    Ok(())
}
