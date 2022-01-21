from tkinter import E
from scripts.utils import get_account
from scripts.data import get_all_dex_to_pair_data
from brownie import interface, config, network
import bot_config


def get_pair_price_full(_dex_name, _verbose=False):
    data = get_all_dex_to_pair_data()
    return get_pair_price_via_pool_reserves(data, _dex_name, _verbose)


def get_pair_price_via_pool_reserves(_pair_dex_data, dex_name, _verbose=False):
    pair_data = _pair_dex_data["pair_data"]
    token_data = _pair_dex_data["token_data"]
    pair, reversed_order = pair_data[dex_name]
    token0, name0, decimals0 = _pair_dex_data["token_data"][bot_config.token_names[0]]
    token1, name1, decimals1 = _pair_dex_data["token_data"][bot_config.token_names[1]]

    account = get_account()

    # The way this function is designed is so that it is as fast as possible
    # when retrieving prices: since it is static, we want all the info wr are
    # passing in the arguments to be computed only once
    reserve0, reserve1, block_timestamp_last = pair.getReserves({"from": account})

    if not reversed_order:
        reserve0 *= 10 ** (max(decimals0, decimals1) - decimals0)
        reserve1 *= 10 ** (max(decimals0, decimals1) - decimals1)
        price = reserve0 / reserve1
    else:
        reserve1 *= 10 ** (max(decimals0, decimals1) - decimals0)
        reserve0 *= 10 ** (max(decimals0, decimals1) - decimals1)
        price = reserve1 / reserve0

    # Now we can compute de price
    # See uniswap v2 withepaper
    if _verbose:
        print(f"{name0} amount {reserve0}\n{name1} amount {reserve1}")
        print(f"The price (via reserve balances) is {price}")

    return price


def get_pair_price_via_result_of_swapping(
    _token_in_address, _token_out_address, _version="V2", _verbose=False
):
    # !!! This does not work because the method `getAmountsOut` is internal

    # Here we calculate the price by checking what we would get from swapping
    # 1 of _token_in by token_out. The code comes from examining the function
    # swapExactTokensForTokens from the UniswapV2Router0.2 contract

    account = get_account()
    if _version == "V3":
        raise Exception("V3 is not supported")

    network_addresses = config["networks"][network.show_active()]
    factory = interface.IUniswapV2Factory(network_addresses["uniswap_factory_address"])
    library = interface.IUniswapV2Library(network_addresses["uniswap_library_address"])
    amount = library.getAmountsOut(
        factory, 1, [_token_in_address, _token_out_address], {"from": account}
    )
    price = 1 / amount
    if _verbose:
        print(f"Amount out if swapped: {amount}\nPrice {price}")
    return price
