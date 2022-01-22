from webbrowser import get
from brownie import interface
from web3 import Web3
from scripts.deploy import deploy_actor, deploy_swapper
import bot_config
from scripts.utils import (
    get_account,
    get_token_addresses,
    get_wallet_balances,
    deposit_eth_into_weth,
)

# the tests are currently perfomrmed assuming the only asset flashloaned is WETH

DEPOSIT_AMOUNT_ETH = bot_config.amount_for_fees + bot_config.extra_cover
# We pass 10% of the eth we could borrow just to rule out the possibility that the test
# fails because actor has not enough funds after the twoHopArbitrage function
ETH_TO_BORROW = bot_config.amount_to_borrow * 0.1
TOKEN_NAMES = bot_config.token_names


def test_two_hop_arbitrage_solidity():
    account = get_account()
    token_addresses = get_token_addresses(TOKEN_NAMES)
    actor = deploy_actor(dex_list=bot_config.dex_names)
    weth = interface.IWeth(token_addresses[0])
    initial_deposit = Web3.toWei(DEPOSIT_AMOUNT_ETH, "ether")  # for fees
    deposit_eth_into_weth(initial_deposit)
    wei_to_transfer = Web3.toWei(DEPOSIT_AMOUNT_ETH, "ether")
    tx = weth.approve(actor.address, wei_to_transfer, {"from": account})
    tx.wait(1)
    #!!! Careful: this needs to be called by actor, not me
    # TODO: Check if I can just use transfer here instead of transferFrom
    tx = weth.transferFrom(
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
    print(swapReturns1 / (10 ** weth.decimals()))
    assert swapReturns1 == weth.balanceOf(actor.address, {"from": account})


def test_request_flashloan_and_act():
    account = get_account()
    token_addresses = get_token_addresses(TOKEN_NAMES)
    actor = deploy_actor(dex_list=bot_config.dex_names)
    weth = interface.IWeth(token_addresses[0])

    initial_deposit = Web3.toWei(DEPOSIT_AMOUNT_ETH, "ether")  # for fees
    deposit_eth_into_weth(initial_deposit)
    # for information purposes only, prints the weth balance of account
    _ = get_wallet_balances(account, [weth], verbose=True)

    # REMEMBER:
    # If you flash 100 AAVE, the 9bps fee is 0.09 AAVE
    # If you flash 500,000 DAI, the 9bps fee is 450 DAI
    # If you flash 10,000 LINK, the 9bps fee is 45 LINK
    # All of these fees need to be sitting ON THIS CONTRACT before you execute this batch flash.
    # !! transferFrom and approve since we are transfering from an external account (ours)
    wei_to_transfer = Web3.toWei(DEPOSIT_AMOUNT_ETH, "ether")
    print(f"Approving {wei_to_transfer} for transfering...")
    tx = weth.approve(actor.address, wei_to_transfer, {"from": account})
    tx.wait(1)
    print("Approved")

    assert weth.allowance(account.address, actor.address) == wei_to_transfer
    assert weth.balanceOf(account.address) >= wei_to_transfer

    print("Transferring weth to Actor...")
    #!!! Careful: this needs to be called by actor, not me
    tx = weth.transferFrom(
        account.address, actor.address, wei_to_transfer, {"from": actor.address}
    )
    # tx = weth.transfer(actor.address, wei_to_transfer, {"from": account})
    tx.wait(1)
    print("Transfer done")
    weth_balance_of_Actor = weth.balanceOf(actor.address, {"from": account})
    print(
        f"WETH balance of Actor contract: {Web3.fromWei(weth_balance_of_Actor, 'ether')}"
    )

    print("Requesting flash loan and acting...")

    tx = actor.requestFlashLoanAndAct(
        token_addresses,
        [Web3.toWei(ETH_TO_BORROW, "ether"), 0],
        {"from": account},
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
    assert amount_flashloaned == Web3.toWei(ETH_TO_BORROW, "ether")

    weth_final_owner_balance = weth.balanceOf(account, {"from": account})
    weth_final_actor_balance = weth.balanceOf(actor.address, {"from": account})
    weth_final_owner_balance = Web3.fromWei(weth_final_owner_balance, "ether")
    weth_final_actor_balance = Web3.fromWei(weth_final_actor_balance, "ether")
    print(f"Owner final weth balance: {weth_final_owner_balance}")
    print(f"Actor final weth balance: {weth_final_actor_balance}")

    assert weth_final_actor_balance == 0


def test_two_hop_arbitrage_python():
    account = get_account()
    swapper = deploy_swapper(bot_config.dex_names)
    token_addresses = get_token_addresses(TOKEN_NAMES)
    weth = interface.IWeth(token_addresses[0])
    usdt = interface.IERC20(token_addresses[1])

    amount_in = Web3.toWei(DEPOSIT_AMOUNT_ETH, "ether")
    deposit_eth_into_weth(amount_in)
    weth_balance = weth.balanceOf(account, {"from": account})
    assert weth_balance == amount_in
    print(f"Weth balance: {weth_balance}")

    # We now are copying the code from the function `two_hop_arbitrage`
    # and testing step by step

    weth.approve(swapper.address, amount_in, {"from": account})
    allowance_of_swapper = weth.allowance(
        account.address, swapper.address, {"from": account}
    )
    print(
        f"Allowance of swapper: {allowance_of_swapper}",
    )
    assert allowance_of_swapper == amount_in

    _swapper = swapper
    _token0 = weth
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
