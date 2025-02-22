#![allow(unexpected_cfgs)] // Suppress cfg warnings

use anchor_lang::prelude::*;
use anchor_lang::Accounts;
use anchor_spl::token::TokenAccount;

declare_id!("Fn52o2N4NS77kvXVyTeuDTSXRL1x9uCx6712sNonB62x");

pub mod error;
pub mod state;
pub mod swaps;

use crate::error::ErrorCode;
use crate::state::SwapState;

use swaps::*;

#[derive(Accounts)]
pub struct InitSwapState<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + 8 + 8 + 1,
        seeds = [b"swap_state"],
        bump,
    )]
    pub swap_state: Account<'info, SwapState>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct TokenAndSwapState<'info> {
    src: Account<'info, TokenAccount>,
    #[account(mut, seeds=[b"swap_state"], bump)]
    pub swap_state: Account<'info, SwapState>,
}

pub fn prepare_swap(swap_state: &Account<SwapState>) -> Result<u64> {
    require!(swap_state.is_valid, ErrorCode::InvalidState);

    let amount_in = swap_state.swap_input;
    msg!("swap amount in: {:?}", amount_in);

    Ok(amount_in)
}

#[program]
pub mod sol_arbitrage_program {
    use super::*;

    pub fn init_program(ctx: Context<InitSwapState>) -> Result<()> {
        let swap_state = &mut ctx.accounts.swap_state;
        swap_state.swap_input = 0;
        swap_state.is_valid = false;
        Ok(())
    }

    pub fn start_swap(ctx: Context<TokenAndSwapState>, swap_input: u64) -> Result<()> {
        let swap_state = &mut ctx.accounts.swap_state;
        swap_state.start_balance = ctx.accounts.src.amount;
        swap_state.swap_input = swap_input;
        swap_state.is_valid = true;
        Ok(())
    }

    pub fn profit_or_revert(ctx: Context<TokenAndSwapState>) -> Result<()> {
        let swap_state = &mut ctx.accounts.swap_state;
        swap_state.is_valid = false; // record end of swap

        let init_balance = swap_state.start_balance;
        let final_balance = ctx.accounts.src.amount;

        msg!(
            "old = {:?}; new = {:?}; diff = {:?}",
            init_balance,
            final_balance,
            final_balance - init_balance
        );

        // ensure profit or revert
        require!(final_balance > init_balance, ErrorCode::NoProfit);

        Ok(())
    }

    pub fn raydium_amm_v4_swap<'info>(
        ctx: Context<'_, '_, '_, 'info, RaydiumAmmV4Swap<'info>>,
    ) -> Result<()> {
        basic_pool_swap!(_raydium_amm_v4_swap, RaydiumAmmV4Swap<'info>)(ctx)
    }

    pub fn raydium_clmm_swap<'info>(
        ctx: Context<'_, '_, '_, 'info, RaydiumClmmSwap<'info>>,
    ) -> Result<()> {
        basic_pool_swap!(_raydium_clmm_swap, RaydiumClmmSwap<'info>)(ctx)
    }
}

pub fn end_swap(
    swap_state: &mut Account<SwapState>,
    user_dst: &mut Account<TokenAccount>,
) -> Result<()> {
    let dst_start_balance = user_dst.amount; // pre-swap balance
    user_dst.reload()?; // update underlying account

    let dst_end_balance = user_dst.amount; // post-swap balance
    let swap_amount_out = dst_end_balance - dst_start_balance;
    msg!("swap amount out: {:?}", swap_amount_out);

    swap_state.swap_input = swap_amount_out;

    Ok(())
}

#[macro_export]
macro_rules! basic_pool_swap {
    ($swap_fcn:expr, $typ:ident < $tipe:tt > ) => {{
        |ctx: Context<'_, '_, '_, 'info, $typ<$tipe>>| -> Result<()> {
            // save the amount of input swap
            let amount_in = prepare_swap(&ctx.accounts.swap_state).unwrap();

            // do swap
            $swap_fcn(&ctx, amount_in).unwrap();

            // update the swap output amount (to be used as input to next swap)
            let swap_state = &mut ctx.accounts.swap_state;
            let user_dst = &mut ctx.accounts.token_account_out;
            end_swap(swap_state, user_dst).unwrap();

            Ok(())
        }
    }};
}
