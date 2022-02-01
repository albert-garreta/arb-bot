from scripts.utils import get_account, get_address, get_token_names_and_addresses
from scripts.data_structures.general_data import get_all_dexes_and_factories
from brownie import config, network, Actor, ActorV2
import bot_config


def get_actor_V2():
    print(f"Deploying Actor... (length {len(ActorV2)})")
    if len(ActorV2) > 0:
        print("Actor was already deployed")
        return ActorV2[-1]
    else:
        return deploy_actor_V2()


def deploy_actor_V2():
    args = get_actorV2_constructor_arguments()
    print(args)
    ActorV2.deploy(*args, {"from": get_account()})
    print("Deployed!")
    return ActorV2[-1]


def get_actorV2_constructor_arguments():
    routers_and_factories = get_all_dexes_and_factories(bot_config.dex_names)
    token_names, token_addresses = get_token_names_and_addresses()
    # TODO: clean this up
    router_addresses = [dex_rf[0].address for dex_rf in routers_and_factories]
    factory_addresses = [dex_rf[1].address for dex_rf in routers_and_factories]
    return router_addresses, factory_addresses, token_addresses


def deploy_actor_V1(dex_list=bot_config.dex_names, _swapper_version="V2"):
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


def main():
    deploy_actor_V1()
    get_actor_V2()
