from brownie import network, interface, config
from scripts.utils import get_account, get_address, get_dex_router_and_factory

# I could not find some token addresses in some testnets like ftm-test
# This scripts does it the hard way


def main():

    # we get the weth address in the active network used
    account = get_account()
    router = interface.IUniswapV2Router02(get_address("swap_router_V2_address"))
    weth = router.WETH({"from": account})
    print("wrapped main token: ", weth)

    _, factory = get_dex_router_and_factory()

    with open("./ftm_testnet_token_addresses.txt", "w") as f:
        f.write("FTM TESTNET TOKEN ADDRESSES\n\n")

    # Find the addresses of the tokens in the first 10 LP's deposited to spookyswap
    for lp_num in range(1000):
        pair_address = factory.allPairs(lp_num, {"from": account})
        pair = interface.IUniswapV2Pair(pair_address)
        address0 = pair.token0()
        address1 = pair.token1()
        token0 = interface.IERC20(address0)
        token1 = interface.IERC20(address1)
        with open("./ftm_testnet_token_addresses.txt", "a") as f:
            f.write(f"{token0.name()}, {address0}\n")
            f.write(f"{token1.name()}, {address1}\n")
