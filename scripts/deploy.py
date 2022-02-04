from scripts.utils import get_account, get_token_names_and_addresses
from scripts.data_structures.static_data import get_all_dexes_and_factories
from brownie import BotSmartContract
import bot_config


def get_BotSmartContract():
    print(f"Deploying BotSmartContract... (length {len(BotSmartContract)})")
    if len(BotSmartContract) > 0:
        print("BotSmartContract was already deployed")
        return BotSmartContract[-1]
    else:
        return deploy_BotSmartContract()


def deploy_BotSmartContract():
    BotSmartContract.deploy({"from": get_account()})
    print("Deployed!")
    return BotSmartContract[-1]


def get_BotSmartContract_constructor_arguments():
    # Deprecated
    routers_and_factories = get_all_dexes_and_factories(bot_config.dex_names)
    token_names, token_addresses = get_token_names_and_addresses()
    # TODO: clean this up
    router_addresses = [dex_rf[0].address for dex_rf in routers_and_factories]
    factory_addresses = [dex_rf[1].address for dex_rf in routers_and_factories]
    return router_addresses, factory_addresses, token_addresses


def main():
    deploy_BotSmartContract()
