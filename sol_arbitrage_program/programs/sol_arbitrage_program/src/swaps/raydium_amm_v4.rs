use anchor_lang::prelude::*;
use anchor_lang::solana_program::{
    instruction::{AccountMeta, Instruction},
    program::invoke,
};
use anchor_lang::Accounts;

use anchor_spl::token::{TokenAccount, ID};

use crate::state::SwapState;

pub const AMM_V4_PROGRAM_ID: Pubkey = pubkey!("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8");
pub const OPEN_BOOK_PROGRAM_ID: Pubkey = pubkey!("srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX");
pub const RAY_AUTHORITY_V4: Pubkey = pubkey!("5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1");

#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct RaydiumAmmV4SwapData {
    pub instruction: u8,
    pub amount_in: u64,
    pub minimum_amount_out: u64,
}

#[derive(Accounts)]
pub struct RaydiumAmmV4Swap<'info> {
    /// CHECK: This is the SPL Token program and its address is validated by the constraint.
    #[account(address = ID)]
    pub token_program: AccountInfo<'info>,

    /// CHECK: The liquidity pair account is not deserialized because only its key is needed.
    #[account(mut)]
    pub pair_address: AccountInfo<'info>,

    /// CHECK: The Raydium authority account is verified by the `address` constraint.
    #[account(address = RAY_AUTHORITY_V4)]
    pub ray_authority: AccountInfo<'info>,

    /// CHECK: Open orders account data is not required, so no type-check is performed.
    #[account(mut)]
    pub open_orders: UncheckedAccount<'info>,

    /// CHECK: Target orders account is unchecked since its inner data isn’t used.
    #[account(mut)]
    pub target_orders: UncheckedAccount<'info>,

    /// CHECK: Base vault’s key is used for CPI; its inner data isn’t required.
    #[account(mut)]
    pub base_vault: UncheckedAccount<'info>,

    /// CHECK: Quote vault’s key is sufficient for our purpose.
    #[account(mut)]
    pub quote_vault: UncheckedAccount<'info>,

    /// CHECK: The Open Book program account is validated by its address.
    #[account(address = OPEN_BOOK_PROGRAM_ID)]
    pub open_book_program: AccountInfo<'info>,

    /// CHECK: Only the account address is needed for the market, so no deserialization is done.
    #[account(mut)]
    pub market_id: AccountInfo<'info>,

    /// CHECK: Bids account is unchecked since its detailed data is not used.
    #[account(mut)]
    pub bids: UncheckedAccount<'info>,

    /// CHECK: Asks account is unchecked; its key is sufficient.
    #[account(mut)]
    pub asks: UncheckedAccount<'info>,

    /// CHECK: The event queue is not deserialized because its data is irrelevant to this instruction.
    #[account(mut)]
    pub event_queue: UncheckedAccount<'info>,

    /// CHECK: Market base vault is used only by its key.
    #[account(mut)]
    pub market_base_vault: UncheckedAccount<'info>,

    /// CHECK: Market quote vault is only used for its address.
    #[account(mut)]
    pub market_quote_vault: UncheckedAccount<'info>,

    /// CHECK: The authority account is unchecked as it is only used to derive the CPI call.
    pub authority: UncheckedAccount<'info>,

    // These two token accounts are deserialized into TokenAccount,
    // so their types guarantee correct data.
    #[account(mut)]
    pub token_account_in: Account<'info, TokenAccount>,

    #[account(mut)]
    pub token_account_out: Account<'info, TokenAccount>,

    // The owner is a Signer, which is checked automatically.
    pub owner: Signer<'info>,

    /// CHECK: The swap state is deserialized by its type; seeds and bump ensure its validity.
    #[account(mut, seeds = [b"swap_state"], bump)]
    pub swap_state: Account<'info, SwapState>,
}

pub fn _raydium_amm_v4_swap<'info>(
    ctx: &Context<'_, '_, '_, 'info, RaydiumAmmV4Swap<'info>>,
    amount_in: u64,
) -> Result<()> {
    let data = RaydiumAmmV4SwapData {
        instruction: 9,
        amount_in,
        minimum_amount_out: 0,
    };

    let instruction = Instruction {
        program_id: AMM_V4_PROGRAM_ID,
        accounts: vec![
            AccountMeta::new_readonly(ctx.accounts.token_program.key(), false),
            AccountMeta::new(ctx.accounts.pair_address.key(), false),
            AccountMeta::new_readonly(ctx.accounts.ray_authority.key(), false),
            AccountMeta::new(ctx.accounts.open_orders.key(), false),
            AccountMeta::new(ctx.accounts.target_orders.key(), false),
            AccountMeta::new(ctx.accounts.base_vault.key(), false),
            AccountMeta::new(ctx.accounts.quote_vault.key(), false),
            AccountMeta::new_readonly(ctx.accounts.open_book_program.key(), false),
            AccountMeta::new(ctx.accounts.market_id.key(), false),
            AccountMeta::new(ctx.accounts.bids.key(), false),
            AccountMeta::new(ctx.accounts.asks.key(), false),
            AccountMeta::new(ctx.accounts.event_queue.key(), false),
            AccountMeta::new(ctx.accounts.market_base_vault.key(), false),
            AccountMeta::new(ctx.accounts.market_quote_vault.key(), false),
            AccountMeta::new_readonly(ctx.accounts.authority.key(), false),
            AccountMeta::new(ctx.accounts.token_account_in.key(), false),
            AccountMeta::new(ctx.accounts.token_account_out.key(), false),
            AccountMeta::new_readonly(ctx.accounts.owner.key(), true),
        ],
        data: data.try_to_vec()?,
    };

    let account_infos = [
        ctx.accounts.token_program.to_account_info(),
        ctx.accounts.pair_address.to_account_info(),
        ctx.accounts.ray_authority.to_account_info(),
        ctx.accounts.open_orders.to_account_info(),
        ctx.accounts.target_orders.to_account_info(),
        ctx.accounts.base_vault.to_account_info(),
        ctx.accounts.quote_vault.to_account_info(),
        ctx.accounts.open_book_program.to_account_info(),
        ctx.accounts.market_id.to_account_info(),
        ctx.accounts.bids.to_account_info(),
        ctx.accounts.asks.to_account_info(),
        ctx.accounts.event_queue.to_account_info(),
        ctx.accounts.market_base_vault.to_account_info(),
        ctx.accounts.market_quote_vault.to_account_info(),
        ctx.accounts.authority.to_account_info(),
        ctx.accounts.token_account_in.to_account_info(),
        ctx.accounts.token_account_out.to_account_info(),
        ctx.accounts.owner.to_account_info(),
    ];

    invoke(&instruction, &account_infos)?;

    Ok(())
}
