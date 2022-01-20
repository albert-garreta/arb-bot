from scripts.utils import get_account
from brownie import config, network, SwapperV2, SwapperV3


def deploy_swapper(_version="V2"):
    print(f"Deploying Swapper{_version}...")
    account = get_account()
    newtork_addresses = config["networks"][network.show_active()]
    swap_router_address = newtork_addresses[f"swap_router_{_version}_address"]
    if _version == "V2":
        swapper = SwapperV2.deploy(swap_router_address, {"from": account})
    elif _version == "V3":
        swapper = SwapperV3.deploy(swap_router_address, {"from": account})
    print("Deployed!")
    return swapper


def main():
    deploy_swapper()
