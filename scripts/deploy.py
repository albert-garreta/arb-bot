from scripts.utils import get_account
from brownie import Bot


def deploy_bot():
    account = get_account()
    bot = Bot.deploy({"from": account})


def main():
    deploy_bot()
