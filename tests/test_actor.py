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

DEPOSIT_AMOUNT_TOKEN0 = bot_config.amount_for_fees + bot_config.extra_cover
# We pass 10% of the eth we could borrow just to rule out the possibility that the test
# fails because actor has not enough funds after the twoHopArbitrage function
TOKEN0_TO_BORROW = bot_config.amount_to_borrow * 1  # 0.01
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
    print(price_in_dex0, price_in_dex1)

    print("Requesting flash loan and acting...")

    tx = actor.requestFlashLoanAndAct(
        token_addresses,
        [Web3.toWei(TOKEN0_TO_BORROW, "ether"), 0],
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
    do_transfer_from = True
    tx = actor.swapExactTokensForTokens(
        token0,
        token1,
        initial_deposit,
        min_amount_out,
        router_index,
        do_transfer_from,
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


def test_two_hop_arbitrage_python():
    account = get_account()
    swapper = deploy_swapper(bot_config.dex_names)
    token_addresses = get_token_addresses(TOKEN_NAMES)
    token0 = interface.IERC20(token_addresses[0])
    usdt = interface.IERC20(token_addresses[1])

    amount_in = Web3.toWei(DEPOSIT_AMOUNT_TOKEN0, "ether")
    deposit_main_token_into_wrapped_version(amount_in)
    token0_balance = token0.balanceOf(account, {"from": account})
    assert token0_balance == amount_in
    print(f"token0 balance: {token0_balance}")

    # We now are copying the code from the function `two_hop_arbitrage`
    # and testing step by step

    token0.approve(swapper.address, amount_in, {"from": account})
    allowance_of_swapper = token0.allowance(
        account.address, swapper.address, {"from": account}
    )
    print(
        f"Allowance of swapper: {allowance_of_swapper}",
    )
    assert allowance_of_swapper == amount_in

    _swapper = swapper
    _token0 = token0
    _token1 = usdt
    _amount_in = amount_in
    _min_amount_out0 = 0
    _min_amount_out1 = 1
    _router0_index = 0
    _router1_index = 1

    print("Balances before the two hop arbitrabe swaps:")
    balances = get_wallet_balances(account, [_token0, _token1], verbose=True)
    print("")

    initial_token0_balance = balances[0]

    tx = _swapper.swapExactTokensForTokens(
        _token0.address,
        _token1.address,
        _amount_in,
        _min_amount_out0,
        _router0_index,
    )
    tx.wait(1)

    print("Balances after the first swap:")
    balances = get_wallet_balances(account, [_token0, _token1], verbose=True)
    print("")

    amount_out_first_swap = _swapper.amountOutFromSwap()
    assert amount_out_first_swap == balances[1]

    _token1.approve(_swapper.address, amount_out_first_swap, {"from": account})
    tx = _swapper.swapExactTokensForTokens(
        _token1.address,
        _token0.address,
        amount_out_first_swap,
        _min_amount_out1,
        _router1_index,
    )
    tx.wait(1)

    print("Balances after the second swap:")
    balances = get_wallet_balances(account, [_token0, _token1], verbose=True)
    print(
        f"\nDelta of token0 balance: {(balances[0] - initial_token0_balance)/(10**_token0.decimals())}"
    )
