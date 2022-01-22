from scripts.utils import get_account, get_address, get_all_dexes_and_factories
from brownie import config, network, Actor, SwapperV2
import bot_config


def deploy_actor(dex_list=bot_config.dex_names, _swapper_version="V2"):
    print(f"Deploying Actor... (length {len(Actor)})")
    if len(Actor) <= 0:
        account = get_account()
        routers_and_factories = get_all_dexes_and_factories(dex_list)
        router_addresses = [r.address for (r, f) in routers_and_factories]
        lending_pool_address_provider_address = get_address(
            "lending_pool_addresses_provider_address"
        )
        Actor.deploy(
            router_addresses,
            lending_pool_address_provider_address,
            
            {"from": account},
        )
        print("Deployed!")
    else:
        print("Actor was already deployed")
    return Actor[-1]


def deploy_swapper(dex_list=bot_config.dex_names, _version="V2"):
    print(f"Deploying Swapper{_version}...")
    account = get_account()
    routers_and_factories = get_all_dexes_and_factories(dex_list)
    router_addresses = [r.address for (r, f) in routers_and_factories]
    if _version == "V2":
        if len(SwapperV2) <= 0:
            SwapperV2.deploy(router_addresses, {"from": account})
            print("Deployed!")
        else:
            print("Swapper was already deployed")
        return SwapperV2[-1]
    # elif _version == "V3":
    #     if len(SwapperV3) <= 0:
    #         SwapperV3.deploy(router.address, {"from": account})
    #         print("Deployed!")
    #     else:
    #         print("Swapper was already deployed")
    #     return SwapperV3[-1]


def main():
    deploy_actor()
    deploy_swapper()
