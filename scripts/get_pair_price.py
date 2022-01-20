from tkinter import E
from scripts.utils import get_account
from brownie import interface, config, network


def get_pair_price_via_pool_reserves(
    _token_in_address, _token_out_address, _version="V2", _verbose=False
):
    account = get_account()
    if _version == "V3":
        raise Exception("V3 is not supported")
    factory = interface.IUniswapV2Factory(
        config["networks"][network.show_active()]["uniswap_factory_address"]
    )
    pair_address = factory.getPair(
        _token_in_address, _token_out_address, {"from": account}
    )
    # Note: getReserves can also be called from the UniswapV2Library (see function below)
    pair = interface.IUniswapV2Pair(pair_address, {"from": account})

    # !!!
    # It seems that the `Pair` sometimes interchanges the order of the tokens: eg in
    # in mainnet's uniswap, if you pass (WETH, USDT) they get registerd correctly,
    # but in ftm-main's spookyswap, if you pass (WFTM, USDC) they get registered
    # in the reverse order.
    reversed_order = order_has_reversed(_token_in_address, _token_out_address, pair)

    reserve0, reserve1, block_timestamp_last = pair.getReserves({"from": account})

    # We now need to make sure that the two tokens are using the same number of decimals
    decimals0 = interface.IERC20(pair.token0()).decimals()
    decimals1 = interface.IERC20(pair.token1()).decimals()
    reserve0 *= 10 ** (max(decimals0, decimals1) - decimals0)
    reserve1 *= 10 ** (max(decimals0, decimals1) - decimals1)

    # Now we can compute de price
    # See uniswap v2 withepaper
    price = reserve0 / reserve1
    if reversed_order:
        price = 1 / price
    if _verbose:
        name0 = interface.IERC20(pair.token0()).name()
        name1 = interface.IERC20(pair.token1()).name()
        print(f"{name0} amount {reserve0}\n{name1} amount {reserve1}")
        print(f"The price (via reserve balances) is {price}")

    return price


def order_has_reversed(token0_address, token1_address, pair):
    token0_address_in_pair = pair.token0()
    token1_address_in_pair = pair.token1()
    if (
        token0_address_in_pair == token1_address
        and token1_address_in_pair == token0_address
    ):
        return True
    elif (
        token0_address_in_pair == token0_address
        and token1_address_in_pair == token1_address
    ):
        return False
    else:
        raise Exception


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
