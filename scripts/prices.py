from tkinter import E
from scripts.utils import get_account, print_args_wrapped
from scripts.data import get_all_dex_to_pair_data
from brownie import interface, config, network
import bot_config
import numpy as np


def get_approx_price_spread(_pair_dex_data, _verbose=False):
    """[summary]

    Args:
        _pair_dex_data ([type]): [description]
        _verbose (bool, optional): [description]. Defaults to False.

    Returns:
        (float, int, int): (max_price_spread, most expensive dex, cheapest dex)
    """
    include_slippage = bot_config.include_slippage_in_prices
    amounts_out = []
    reserves = []
    amount_in = bot_config.amount_to_borrow_token0_wei
    amt_in_tkn0_0 = amount_in / 2
    for dex_index, dex_name in enumerate(bot_config.dex_names):
        # This includes the trading fees of the dexes and the price alterations of our
        # swap. It does not include slippage nor the fees from the flashloan.
        amount_out, reserve0, reserve1 = get_pair_price_via_pool_reserves(
            amt_in_tkn0_0, _pair_dex_data, dex_index, _verbose=True
        )
        amounts_out.append(amount_out)
        reserves.append((reserve0, reserve1))
        if _verbose:
            print(
                f"The token1/token0 price "
                f"in {dex_name} is approx (frictionless) "
                f"{get_approx_price(reserve0, reserve1)}"
            )
            if bot_config.debug_mode:
                # Currently just a placeholder for quick debugging
                print(f"The price in Coingecko is {bot_config.coingecko_price()}")
    max_index = np.argmax(amounts_out)
    min_index = np.argmin(amounts_out)

    # We take the maximum amount out possible. The buying dex is the one
    # with max_index, and the selling is the one with min_index
    amt_out_tkn1_0 = amounts_out[max_index]
    selling_dex_fee = bot_config.dex_fees[min_index]
    reserves_of_buying_dex = reserves[max_index]
    reserves_of_selling_dex = reserves[min_index]

    # Frictionless (IRL this will have been done before requesting the flashloan,
    # that's why we make this swap as frictionless)
    # FIXME:  Is it reasonable to use the best dex possible since this swap is
    # really done before the flashloan? I always can flashloan a little more
    # in order to make sure I have this amt_in_tok1 to sell at the best selling dex now
    amt_in_tkn1_1 = amt_in_tkn0_0 / get_approx_price(
        reserves_of_buying_dex[0], reserves_of_buying_dex[1]
    )

    # Sell amt_in_tokn1 in the selling dex
    amt_out_tkn0_1 = get_dex_ammount_out(
        reserves_of_selling_dex[1],
        reserves_of_selling_dex[0],
        amt_in_tkn1_1,
        selling_dex_fee,
        include_slippage,
    )

    amt_out_tkn0_0 = amt_out_tkn1_0 / get_approx_price(
        reserves_of_selling_dex[1], reserves_of_selling_dex[0]
    )

    # amount_out_after_arbitrage = max_amount_out / get_approx_price(
    #    reserves_selling_dex[1], reserves_selling_dex[0]
    # )
    final_profit_of_arbitrage = (
        -1
        + (
            (amt_out_tkn0_0 + amt_out_tkn0_1)
            - ((bot_config.lending_pool_fee / 100) * amount_in)
        )
        / amount_in
    ) * 100

    # max_delta = max(prices) - min(prices)
    # min_index = np.argmin(prices)
    # max_price_spread = 100 * max_delta / min(prices)
    if _verbose:
        print(f"Highest price in {bot_config.dex_names[min_index]}")
        print(f"Lowest price in {bot_config.dex_names[max_index]}")
        # print(f"Max delta: {max_delta}")
        print(f"Profit %: {final_profit_of_arbitrage}\n")
    return final_profit_of_arbitrage, max_index, min_index


def get_pair_price_full(_dex_index, _verbose=False):
    """Currently only used for testing
    *Probably outdated*

    Args:
        _dex_name ([type]): [description]
        _verbose (bool, optional): [description]. Defaults to False.

    Returns:
        float: the price of token1 with respect to to token0
    """
    data = get_all_dex_to_pair_data()
    return get_pair_price_via_pool_reserves(data, _dex_index, _verbose)


def get_dex_ammount_out(_reserve0, _reserve1, _amount_in, _dex_fee, _include_slippage):
    # This is derived from the x*y=k formula: the balances x',y' after the swap
    # have to satisgy x' * y' = k
    # print(_reserve0)
    numerator = _amount_in * (1 - _dex_fee / 100) * _reserve1
    denominator = _reserve0 +  (1 - _dex_fee / 100) * _amount_in
    amount_out = numerator / denominator
    if _include_slippage:
        amount_out *= 1 - (bot_config.approx_slippage / 100)
    return amount_out


def get_approx_price(_reserve0, _reserve1):
    return _reserve0 / _reserve1


def get_pair_price_via_pool_reserves(
    _amount_in, _pair_dex_data, _dex_index, _verbose=False
):
    # The way this function is designed is so that it is as fast as possible
    # when retrieving prices. The arguments of the function consist of precomputed
    # static data about the dex pairs and individual tokens
    account = get_account()
    pair_data = _pair_dex_data["pair_data"]
    token_data = _pair_dex_data["token_data"]
    pair, reversed_order = pair_data[bot_config.dex_names[_dex_index]]
    token0, name0, decimals0 = token_data[bot_config.token_names[0]]
    token1, name1, decimals1 = token_data[bot_config.token_names[1]]
    dex_fees = bot_config.dex_fees[_dex_index]
    include_slippage = bot_config.include_slippage_in_prices

    reserve0, reserve1, block_timestamp_last = pair.getReserves({"from": account})
    if reversed_order:
        _ = reserve0
        reserve0 = reserve1
        reserve1 = _
    reserve0 *= 10 ** (max(decimals0, decimals1) - decimals0)
    reserve1 *= 10 ** (max(decimals0, decimals1) - decimals1)

    amount_out = get_dex_ammount_out(
        reserve0,
        reserve1,
        _amount_in,
        include_slippage,
        dex_fees,
    )

    return amount_out, reserve0, reserve1
