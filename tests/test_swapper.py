from scripts.deploy import deploy_swapper
from scripts.prices import get_pair_price_full
import bot_config
from scripts.utils import (
    get_account,
    get_wallet_balances,
    deposit_eth_into_weth,
    ETH_NETWORKS,
    FTM_NETWORKS,
)
from brownie import network, config, interface
from web3 import Web3


def test_two_hop_arbitrage():
    account = get_account()
    active_net = network.show_active()
    swapper = deploy_swapper(bot_config.dex_names)

    network_addresses = config["networks"][active_net]
    weth_address = network_addresses["weth_address"]
    usdt_address = network_addresses["usdt_address"]
    weth = interface.IWeth(weth_address)
    usdt = interface.IERC20(usdt_address)

    if active_net in ETH_NETWORKS:
        amount_in = 0.001
    elif active_net in FTM_NETWORKS:
        amount_in = 0.1
    else:
        raise Exception("Network is not supported")

    deposit_eth_into_weth(amount_in)

    weth.approve(swapper.address, amount_in, {"from": account})

    amount_out = swapper.twoHopArbitrage(
        weth_address,  # token0_address,
        usdt_address,  # token1_address
        amount_in,
        0,  # min_amount_out0,
        0,  # min_amount_out1,
        0,  # router0_index
        1,  # router1_index,
        {"from": account},
    )


def test_swap_exact_input_single():
    account = get_account()
    active_net = network.show_active()
    swapper = deploy_swapper([bot_config.dex_names[0]])
    network_addresses = config["networks"][active_net]
    weth_address = network_addresses["weth_address"]
    usdt_address = network_addresses["usdt_address"]
    weth = interface.IWeth(weth_address)
    usdt = interface.IERC20(usdt_address)

    if active_net in ETH_NETWORKS:
        amount_weth_deposit = 0.001
        weth_amount_to_swap = 0.0001
    elif active_net in FTM_NETWORKS:
        amount_weth_deposit = 0.1
        weth_amount_to_swap = 0.1
    else:
        raise Exception("Network is not supported")

    deposit_eth_into_weth(_amount=Web3.toWei(amount_weth_deposit, "ether"))

    usdt_weth_price = get_pair_price_full(
        _dex_name=bot_config.dex_names[0], _verbose=True
    )
    weth_amount_to_swap = Web3.toWei(weth_amount_to_swap, "ether")
    print(f"weth amount to be swapped: {weth_amount_to_swap}")
    balances_before = get_wallet_balances(account, [weth, usdt])

    print("Approving spending...")
    tx = weth.approve(swapper.address, weth_amount_to_swap, {"from": account})
    tx.wait(1)
    print("Approved")

    print("Swapping...")
    min_amount_out = 0
    tx = swapper.swapExactTokensForTokens(
        weth, usdt, weth_amount_to_swap, min_amount_out, {"from": account}
    )
    tx.wait(1)
    print("Swapped!")

    balances_after = get_wallet_balances(account, [weth, usdt])
    usdt_before = balances_before[1]
    usdt_after = balances_after[1]
    difference = (usdt_after - usdt_before) / 10 ** usdt.decimals()
    target_gains = weth_amount_to_swap / (usdt_weth_price * 10 ** weth.decimals())
    print(f"Actual usdt gain: {difference}")
    print(f"Expected usdt gain: {target_gains}")
    assert difference <= target_gains + 1 and difference >= target_gains - 1
