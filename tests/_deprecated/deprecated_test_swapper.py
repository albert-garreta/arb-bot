from scripts.deploy import deploy_swapper
from scripts.prices.prices import get_pair_price_full
import bot_config
from scripts.utils import (
    get_account,
    get_wallet_balances,
    get_wallet_balances,
    deposit_main_token_into_wrapped_version,
    ETH_NETWORKS,
    FTM_NETWORKS,
)
from brownie import network, config, interface
from web3 import Web3

# NOTE: Tests written assuming token0 is the wrapped main token of the network


def test_swap_exact_input_single():
    account = get_account()
    active_net = network.show_active()
    swapper = deploy_swapper(bot_config.dex_names)
    network_addresses = config["networks"][active_net]
    token0_address = network_addresses["token0"]
    token1_address = network_addresses["token1"]
    token0 = interface.IERC20(token0_address)
    token1 = interface.IERC20(token1_address)

    if active_net in ETH_NETWORKS:
        amount_token0_deposit = 0.001
        token0_amount_to_swap = 0.0001
    elif active_net in FTM_NETWORKS:
        amount_token0_deposit = 0.1
        token0_amount_to_swap = 0.1
    else:
        raise Exception("Network is not supported")

    deposit_main_token_into_wrapped_version(
        _amount=Web3.toWei(amount_token0_deposit, "ether")
    )

    token1_token0_price = get_pair_price_full(
        _dex_name=bot_config.dex_names[0], _verbose=True
    )
    token0_amount_to_swap = Web3.toWei(token0_amount_to_swap, "ether")
    print(f"token0 amount to be swapped: {token0_amount_to_swap}")
    balances_before = get_wallet_balances(account, [token0, token1])

    print("Approving spending...")
    tx = token0.approve(swapper.address, token0_amount_to_swap, {"from": account})
    tx.wait(1)
    print("Approved")

    print("Swapping...")
    min_amount_out = 0
    router_index = 0
    do_transfer_from = True
    tx = swapper.swapExactTokensForTokens(
        token0,
        token1,
        token0_amount_to_swap,
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
    target_gains = token0_amount_to_swap / (
        token1_token0_price * 10 ** token0.decimals()
    )
    print(f"Actual token1 gain: {difference}")
    print(f"Expected token1 gain: {target_gains}")
    assert difference <= target_gains + 1 and difference >= target_gains - 1
