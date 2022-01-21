from scripts.utils import get_account, get_dex_router_and_factory
from brownie import config, network, SwapperV2, SwapperV3


def deploy_swapper(_version="V2"):
    print(f"Deploying Swapper{_version}...")
    account = get_account()
    router, _ = get_dex_router_and_factory()

    if _version == "V2":
        if len(SwapperV2) <= 0:
            SwapperV2.deploy(router.address, {"from": account})
            print("Deployed!")
        else:
            print("Swapper was already deployed")
        return SwapperV2[-1]
    elif _version == "V3":
        if len(SwapperV3) <= 0:
            SwapperV3.deploy(router.address, {"from": account})
            print("Deployed!")
        else:
            print("Swapper was already deployed")
        return SwapperV3[-1]


def main():
    deploy_swapper()
