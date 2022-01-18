from scripts.utils import get_account
from brownie import config, network, interface, ExampleSwapV3


def deploy():
    print("Deploying...")
    account = get_account()
    newtork_addresses = config["networks"][network.show_active()]
    weth_address = newtork_addresses["weth_address"]
    usdt_address = newtork_addresses["usdt_address"]
    swap_router_address = newtork_addresses["swap_router_address"]
    example_swap = ExampleSwapV3.deploy(
        [weth_address, usdt_address], swap_router_address, {"from": account}
    )
    print("Deployed!")
    return example_swap


def main():
    deploy()
