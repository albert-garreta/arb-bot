from scripts.utils import get_account
from brownie import config, network, Actor


def deploy_actor(_swapper_version="V2"):
    print(f"Deploying Actor... (length {len(Actor)})")
    if len(Actor) <= 0:
        account = get_account()
        network_addresses = config["networks"][network.show_active()]

        # address[] memory _token_addresses,
        # address _swap_router_address,
        # address _lendingPoolAddressesProviderAddress
        Actor.deploy(
            network_addresses[f"swap_router_{_swapper_version}_address"],
            network_addresses["lending_pool_addresses_provider_address"],
            {"from": account},
        )
        print("Deployed!")
    else:
        print("Actor was already deployed")
    return Actor[-1]


def main():
    deploy_actor()
