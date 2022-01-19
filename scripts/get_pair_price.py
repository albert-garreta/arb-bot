from logging import raiseExceptions
from scripts.utils import get_account
from brownie import interface, config, network


def get_pair_price_via_pool_reserves(
    _token_in_address, _token_out_address, _version="V2", _verbose=False
):
    account = get_account()
    if _version == "V3":
        raiseExceptions("V3 is not supported")
    factory = interface.IUniswapV2Factory(
        config["networks"][network.show_active()]["uniswap_factory_address"]
    )
    pair_address = factory.getPair(
        _token_in_address, _token_out_address, {"from": account}
    )
    # Note: getReserves can also be called from the UniswapV2Library (see function below)
    pair = interface.IUniswapV2Pair(pair_address, {"from": account})
    reserve0, reserve1, block_timestamp_last = pair.getReserves({"from": account})

    # We now need to make sure that the two tokens are using the same number of decimals
    decimals0 = interface.IERC20(_token_in_address).decimals()
    decimals1 = interface.IERC20(_token_out_address).decimals()
    reserve0 *= 10 ** (18 - decimals0)
    reserve1 *= 10 ** (18 - decimals1)

    # Now we can compute de price
    # See uniswap v2 withepaper
    price = reserve1 / reserve0
    if _verbose:
        print(f"Reserve0 amount {reserve0}\nReserve1 amount {reserve1}")
        print(f"The price (via reserve balances) is {price}")

    return price


def get_pair_price_via_result_of_swapping(
    _token_in_address, _token_out_address, _version="V2", _verbose=False
):
    # Here we calculate the price by checking what we would get from swapping
    # 1 of _token_in by token_out. The code comes from examining the function
    # swapExactTokensForTokens from the UniswapV2Router0.2 contract

    account = get_account()
    if _version == "V3":
        raiseExceptions("V3 is not supported")

    network_addresses = config["networks"][network.show_active()]
    factory = interface.IUniswapV2Factory(network_addresses["uniswap_factory_address"])
    library = interface.IUniswapV2Library(network_addresses["uniswap_library_address"])
    amount = library.getAmountsOut(
        factory, amountIn=1, path=[_token_in_address, _token_out_address]
    )
    price = 1 / amount
    if _verbose:
        print(f"Amount out if swapped: {amount}\nPrice {price}")
    return price
