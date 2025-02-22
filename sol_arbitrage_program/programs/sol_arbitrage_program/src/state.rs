use anchor_lang::prelude::*;

#[account]
#[derive(Default)]
pub struct SwapState {
    pub start_balance: u64,
    pub swap_input: u64,
    pub is_valid: bool,
}
