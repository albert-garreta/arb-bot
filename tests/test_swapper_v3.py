from scripts.deploy import deploy_swapper_v3
from scripts.utils import (
    get_account,
    get_balances,
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS,
)
from brownie import network, config, interface
from web3 import Web3


def test_swap_exact_input_single():
    account = get_account()
    example_swap = deploy_swapper_v3()
    newtork_addresses = config["networks"][network.show_active()]
    weth_address = newtork_addresses["weth_address"]
    usdt_address = newtork_addresses["usdt_address"]
    weth = interface.IWeth(weth_address)
    usdt = interface.IERC20(usdt_address)

    if (
        network.show_active()
        in LOCAL_BLOCKCHAIN_ENVIRONMENTS + NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS
    ):
        print("Depositing ETH into WETH...")
        tx = weth.deposit({"from": account, "value": Web3.toWei(0.001, "ether")})
        tx.wait(1)
        print("Deposit done")

    weth_amount_in = 0.0001
    weth_amount_in = Web3.toWei(weth_amount_in, "ether")
    print(f"weth amount in {weth_amount_in}")
    balances_before = get_balances(account, [weth, usdt])

    print("Approving spending...")
    tx = weth.approve(example_swap, weth_amount_in, {"from": account})
    tx.wait(1)
    print("Approved")

    print("Swapping...")
    tx = example_swap.swapExactInputSingle(weth_amount_in, {"from": account})
    tx.wait(1)
    print("Swapped!")

    balances_after = get_balances(account, [weth, usdt])
    usdt_before = balances_before[0]
    usdt_after = balances_after[1]
    difference = usdt_after - usdt_before
    assert difference > 3000 * weth_amount_in and difference < 4000 * weth_amount_in
