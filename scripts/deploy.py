from scripts.utils import get_account
from brownie import BotSmartContract


def get_BotSmartContract():
    print("Deploying BotSmartContract...")
    if len(BotSmartContract) > 0:
        print("BotSmartContract was already deployed")
        return BotSmartContract[-1]
    else:
        return deploy_BotSmartContract()


def deploy_BotSmartContract():
    BotSmartContract.deploy({"from": get_account()})
    print("Deployed!")
    return BotSmartContract[-1]


def main():
    deploy_BotSmartContract()
