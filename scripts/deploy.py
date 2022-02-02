from scripts.utils import get_account, get_address, get_token_names_and_addresses
from scripts.data_structures.static_data import get_all_dexes_and_factories
from brownie import Actor
import bot_config


def get_actor():
    print(f"Deploying Actor... (length {len(Actor)})")
    if len(Actor) > 0:
        print("Actor was already deployed")
        return Actor[-1]
    else:
        return deploy_actor()


def deploy_actor():
    args = get_actor_constructor_arguments()
    print(args)
    Actor.deploy(*args, {"from": get_account()})
    print("Deployed!")
    return Actor[-1]


def get_actor_constructor_arguments():
    routers_and_factories = get_all_dexes_and_factories(bot_config.dex_names)
    token_names, token_addresses = get_token_names_and_addresses()
    # TODO: clean this up
    router_addresses = [dex_rf[0].address for dex_rf in routers_and_factories]
    factory_addresses = [dex_rf[1].address for dex_rf in routers_and_factories]
    return router_addresses, factory_addresses, token_addresses


def main():
    deploy_actor()
