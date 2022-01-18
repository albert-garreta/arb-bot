from scripts.utils import get_account
from brownie import config, network, Actor


def deploy_actor():
    print("Deploying Actor...")
    account = get_account()
    network_addresses = config["networks"][network.show_active()]
    token_addresses = [
        network_addresses["weth_address"],
        network_addresses["usdt_address"],
    ]

    # address[] memory _token_addresses,
    # address _swap_router_address,
    # address _lendingPoolAddressesProviderAddress
    actor = Actor.deploy(
        token_addresses,
        network_addresses["swap_router_address"],
        network_addresses["lending_pool_addresses_provider_address"],
        {"from": account},
    )
    print("Deployed!")
    return actor


def main():
    deploy_actor()
