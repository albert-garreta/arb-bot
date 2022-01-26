from webbrowser import get
from brownie import interface
from web3 import Web3
from scripts.deploy import deploy_actor
from scripts.prices import get_pair_price_full
import bot_config
import pytest
from scripts.utils import (
    get_account,
    get_token_addresses,
    get_wallet_balances,
    deposit_main_token_into_wrapped_version,
)


# NOTE: All thests are done assuming that token0 is the Wrapped Main Token of the network

DEPOSIT_AMOUNT_TOKEN0 = bot_config.amount_for_fees_token0 + bot_config.extra_cover
# We pass 10% of the eth we could borrow just to rule out the possibility that the test
# fails because actor has not enough funds after the twoHopArbitrage function
TOKEN0_TO_BORROW = bot_config.amount_to_borrow_token0 * 0.01  # 0.01
TOKEN_NAMES = bot_config.token_names


@pytest.fixture(autouse=True)
def prepare():
    # TODO: add
    pass


def test_two_hop_arbitrage_solidity(prepare):
    account = get_account()
    token_addresses = get_token_addresses(TOKEN_NAMES)
    initial_deposit = Web3.toWei(DEPOSIT_AMOUNT_TOKEN0, "ether")  # for fees
    actor = deploy_actor(dex_list=bot_config.dex_names)
    token0 = interface.IERC20(token_addresses[0])
    deposit_main_token_into_wrapped_version(initial_deposit)
    wei_to_transfer = Web3.toWei(DEPOSIT_AMOUNT_TOKEN0, "ether")
    tx = token0.approve(actor.address, wei_to_transfer, {"from": account})
    tx.wait(1)
    #!!! Careful: this needs to be called by actor, not me
    # TODO: Check if I can just use transfer here instead of transferFrom
    tx = token0.transferFrom(
        account.address, actor.address, wei_to_transfer, {"from": actor.address}
    )
    tx.wait(1)

    #!!! Careful: this needs to be called by actor, not me
    tx = actor.twoHopArbitrage(
        *token_addresses, wei_to_transfer, 0, 0, 0, 1, {"from": account}
    )
    tx.wait(1)

    swapReturns0 = actor.swapReturns(0)
    swapReturns1 = actor.swapReturns(1)
    print(swapReturns0 / (10 ** interface.IERC20(token_addresses[1]).decimals()))
    print(swapReturns1 / (10 ** token0.decimals()))
    assert swapReturns1 == token0.balanceOf(actor.address, {"from": account})


def test_request_flashloan_and_act():
    account = get_account()
    token_addresses = get_token_addresses(TOKEN_NAMES)
    actor = deploy_actor(dex_list=bot_config.dex_names)
    token0 = interface.IERC20(token_addresses[0])

    initial_deposit = Web3.toWei(DEPOSIT_AMOUNT_TOKEN0, "ether")  # for fees
    deposit_main_token_into_wrapped_version(initial_deposit)
    # for information purposes only, prints the token0 balance of account
    _ = get_wallet_balances(account, [token0], verbose=True)

    # REMEMBER:
    # If you flash 100 AAVE, the 9bps fee is 0.09 AAVE
    # If you flash 500,000 DAI, the 9bps fee is 450 DAI
    # If you flash 10,000 LINK, the 9bps fee is 45 LINK
    # All of these fees need to be sitting ON THIS CONTRACT before you execute this batch flash.
    # !! transferFrom and approve since we are transfering from an external account (ours)
    wei_to_transfer = Web3.toWei(DEPOSIT_AMOUNT_TOKEN0, "ether")
    print(f"Approving {wei_to_transfer} for transfering...")
    tx = token0.approve(actor.address, wei_to_transfer, {"from": account})
    tx.wait(1)
    print("Approved")

    assert token0.allowance(account.address, actor.address) == wei_to_transfer
    assert token0.balanceOf(account.address) >= wei_to_transfer

    print("Transferring token0 to Actor...")
    #!!! Careful: this needs to be called by actor, not me
    tx = token0.transferFrom(
        account.address, actor.address, wei_to_transfer, {"from": actor.address}
    )
    # tx = token0.transfer(actor.address, wei_to_transfer, {"from": account})
    tx.wait(1)
    print("Transfer done")
    token0_balance_of_Actor = token0.balanceOf(actor.address, {"from": account})
    print(
        f"token0 balance of Actor contract: {Web3.fromWei(token0_balance_of_Actor, 'ether')}"
    )

    price_in_dex0 = get_pair_price_full(bot_config.dex_names[0])
    price_in_dex1 = get_pair_price_full(bot_config.dex_names[1])
    prices = [price_in_dex0, price_in_dex1]
    print(f"Prices: {prices}")
    max_spread = (max(prices) - min(prices)) / min(prices)
    print(f"Max spread: {max_spread}")

    print("Requesting flash loan and acting...")

    tx = actor.requestFlashLoanAndAct(
        token_addresses,
        [Web3.toWei(TOKEN0_TO_BORROW, "ether"), 0],
        0,  # min_dex_index
        {"from": account},  # , "gas_price": 5000},
    )
    tx.wait(1)
    print("Success!")
    # ! In brownie access to state arrays  are done with (index).
    # ! Access to state variables are done with ()
    pre_loan_balance = actor.preLoanBalances(0)
    print(f"Pre loan token balance: {Web3.fromWei(pre_loan_balance, 'ether')}")
    # assert pre_loan_balance == initial_deposit
    amount_flashloaned = actor.amountsLoanReceived(0)
    print(
        f"Amount of loan received during the flash loan: "
        f"{Web3.fromWei(amount_flashloaned,'ether')}"
    )
    assert amount_flashloaned == Web3.toWei(TOKEN0_TO_BORROW, "ether")

    token0_final_owner_balance = token0.balanceOf(account, {"from": account})
    token0_final_actor_balance = token0.balanceOf(actor.address, {"from": account})
    token0_final_owner_balance = Web3.fromWei(token0_final_owner_balance, "ether")
    token0_final_actor_balance = Web3.fromWei(token0_final_actor_balance, "ether")
    print(f"Owner final token0 balance: {token0_final_owner_balance}")
    print(f"Actor final token0 balance: {token0_final_actor_balance}")

    assert token0_final_actor_balance == 0


def test_swap_exact_input_single():

    account = get_account()
    token_addresses = get_token_addresses(TOKEN_NAMES)
    initial_deposit = Web3.toWei(DEPOSIT_AMOUNT_TOKEN0, "ether")  # for fees
    actor = deploy_actor(dex_list=bot_config.dex_names)
    token0 = interface.IERC20(token_addresses[0])
    deposit_main_token_into_wrapped_version(initial_deposit)
    token1 = interface.IERC20(token_addresses[1])

    token1_token0_price = get_pair_price_full(
        _dex_name=bot_config.dex_names[0], _verbose=True
    )
    print(f"token0 amount to be swapped: {initial_deposit}")
    balances_before = get_wallet_balances(account, [token0, token1])

    print("Approving spending...")
    tx = token0.approve(actor.address, initial_deposit, {"from": account})
    tx.wait(1)
    print("Approved")

    print("Swapping...")
    min_amount_out = 0
    router_index = 0
    tx = actor.swapExactTokensForTokens(
        token0,
        token1,
        initial_deposit,
        min_amount_out,
        router_index,
        {"from": account},
    )
    tx.wait(1)
    print("Swapped!")

    balances_after = get_wallet_balances(account, [token0, token1])
    token1_before = balances_before[1]
    token1_after = balances_after[1]
    difference = (token1_after - token1_before) / 10 ** token1.decimals()
    target_gains = initial_deposit / (token1_token0_price * 10 ** token0.decimals())
    print(f"Actual token1 gain: {difference}")
    print(f"Expected token1 gain: {target_gains}")
    assert difference <= target_gains + 1 and difference >= target_gains - 1
