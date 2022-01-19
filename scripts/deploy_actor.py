from scripts.utils import get_account, get_token_addresses, TOKEN_NAMES
from brownie import config, network, Actor


def deploy_actor():
    print("Deploying Actor...")
    account = get_account()
    network_addresses = config["networks"][network.show_active()]

    # address[] memory _token_addresses,
    # address _swap_router_address,
    # address _lendingPoolAddressesProviderAddress
    actor = Actor.deploy(
        network_addresses["swap_router_address"],
        network_addresses["lending_pool_addresses_provider_address"],
        {"from": account},
    )
    print("Deployed!")
    return actor


def main():
    deploy_actor()
