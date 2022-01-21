from scripts.utils import get_account, get_dex_router_and_factory
from brownie import config, network, Actor


def deploy_actor(_swapper_version="V2"):
    print(f"Deploying Actor... (length {len(Actor)})")
    if len(Actor) <= 0:
        account = get_account()
        router, factory = get_dex_router_and_factory()
        Actor.deploy(
            router.address,
            factory.address,
            {"from": account},
        )
        print("Deployed!")
    else:
        print("Actor was already deployed")
    return Actor[-1]


def main():
    deploy_actor()
