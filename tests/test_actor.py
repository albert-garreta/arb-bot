from scripts.deploy_actor import deploy_actor
from scripts.utils import (
    get_account,
    get_wallet_balances,
    deposit_eth_into_weth,
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS,
)
from brownie import network, config, interface
from web3 import Web3


def test_actor():
    account = get_account()
    actor = deploy_actor()

    addresses = [config["networks"][network.show_active()]["weth_address"]]

    eth_to_borrow = 10
    amounts = [Web3.toWei(eth_to_borrow, "ether")]
    weth = interface.IWeth(addresses[0])

    initial_deposit = Web3.toWei(0.009, "ether")  # for fees
    deposit_eth_into_weth(initial_deposit)

    # for information purposes only, prints the weth balance of account
    _ = get_wallet_balances(account, [weth], verbose=True)

    # REMEMBER:
    # If you flash 100 AAVE, the 9bps fee is 0.09 AAVE
    # If you flash 500,000 DAI, the 9bps fee is 450 DAI
    # If you flash 10,000 LINK, the 9bps fee is 45 LINK
    # All of these fees need to be sitting ON THIS CONTRACT before you execute this batch flash.
    tx = weth.transfer(actor.address, initial_deposit, {"from": account})
    tx.wait(1)

    weth_balance_of_Actor = weth.balanceOf(actor.address, {"from": account})
    print(
        f"WETH balance of Actor contract: {Web3.fromWei(weth_balance_of_Actor, 'ether')}"
    )
    assert weth_balance_of_Actor == initial_deposit

    print("Requesting flash loan and acting...")
    tx = actor.requestFlashLoanAndAct(addresses, amounts, {"from": account})
    tx.wait(1)
    print("Success!")

    # ! In brownie access to state arrays  are done with (index).
    # ! Access to state variables are done with ()
    pre_loan_balance = actor.preLoanBalances(0)
    print(f"Pre loan token balance: {Web3.fromWei(pre_loan_balance, 'ether')}")
    assert pre_loan_balance == initial_deposit

    amount_flashloaned = actor.amountsLoanReceived(0)
    print(
        f"Amount of loan received during the flash loan: "
        f"{Web3.fromWei(amount_flashloaned,'ether')}"
    )
    assert amount_flashloaned == amounts[0]
