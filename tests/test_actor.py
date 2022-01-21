from webbrowser import get
from brownie import interface
from web3 import Web3
from scripts.deploy import deploy_actor
import bot_config
from scripts.utils import (
    get_account,
    get_token_addresses,
    get_wallet_balances,
    deposit_eth_into_weth,
)

# the tests are currently perfomrmed assuming the only asset flashloaned is WETH

DEPOSIT_AMOUNT_ETH = bot_config.amount_for_fees + bot_config.extra_cover
ETH_TO_BORROW = bot_config.amount_to_borrow
TOKEN_NAMES = bot_config.token_names


def test_actor():
    account = get_account()
    token_addresses = get_token_addresses(TOKEN_NAMES)
    actor = deploy_actor()
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
        [token_addresses[0]],
        [Web3.toWei(ETH_TO_BORROW, "ether")],
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
