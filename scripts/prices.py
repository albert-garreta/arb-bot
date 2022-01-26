from tkinter import E
from scripts.utils import get_account, print_args_wrapped
from scripts.data import get_all_dex_to_pair_data
import bot_config
import numpy as np
from scipy.optimize import minimize_scalar

# @print_args_wrapped


def get_arbitrage_profit_info(
    _amount_in, _reserves, _dex_fees, _slippages, _lending_pool_fee, _verbose=False
):
    """[summary]

    Args:
        _pair_dex_data ([type]): [description]
        _verbose (bool, optional): [description]. Defaults to False.

    Returns:
        (float, int, int): (max_price_spread, most expensive dex, cheapest dex)
    """

    # buying/selling dex: dex_names[max/min_index]

    # We take the maximum amount out possible. The buying dex is the one
    # with max_index, and the selling is the one with min_index

    # FIXME: what is a good amount in to pass here? (Amount in may affect the choice of
    # buying dex)
    buying_dex_index, selling_dex_index = determine_buying_and_selling_dex(
        _amount_in, _reserves, _dex_fees, _slippages, _lending_pool_fee, _verbose
    )
    buying_dex_fee = _dex_fees[buying_dex_index]
    selling_dex_fee = _dex_fees[selling_dex_index]
    reserves_buying_dex = _reserves[buying_dex_index]
    reserves_selling_dex = _reserves[selling_dex_index]
    slippage_buy_dex = _slippages[buying_dex_index]
    slippage_sell_dex = _slippages[selling_dex_index]

    opt_amount_in, opt_amount_out = get_optimal_amount_in(
        reserves_buying_dex,
        reserves_selling_dex,
        buying_dex_fee,
        selling_dex_fee,
        slippage_buy_dex,
        slippage_sell_dex,
        _lending_pool_fee,
        _return_optimal_amount_out=True,
        _verbose=_verbose,
    )

    final_profit_ratio = ((opt_amount_out / opt_amount_in)) * 100

    # max_delta = max(prices) - min(prices)
    # min_index = np.argmin(prices)
    # max_price_spread = 100 * max_delta / min(prices)
    if _verbose:
        print(f"Buying dex: {bot_config.dex_names[buying_dex_index]}")
        print(f"Selling dex: {bot_config.dex_names[selling_dex_index]}")
        print(f"Reserves buing dex: {reserves_buying_dex}")
        print(f"Reserves selling dex: {reserves_selling_dex}")
        print(f"Optimal amount in: {opt_amount_in/1e18}")
        print(f"Final amount out: {opt_amount_out/1e18}")
        print(f"Profit %: {final_profit_ratio}\n")
    return (
        final_profit_ratio,
        opt_amount_in,
        opt_amount_out,
        buying_dex_index,
        selling_dex_index,
    )


def determine_buying_and_selling_dex(
    _amount_in, _reserves, _dex_fees, _slippages, _lending_pool_fee, _verbose=False
):
    """[summary]

    Args:
        _amount_in ([type]): [description]
        _dex_fees ([type]): [description]
        _lending_pool_fee ([type]): [description]
        _slippage ([type]): [description]
        _reserves ([type]): [description]

    Returns:
        (int, int): (index of the buying dex, index of the selling dex)
    """

    # Does the buying/selling dex depend on the amount in?
    # ANSWER: It does: see my notes.
    # FIXME: Are my notes wrong? Should we make the calculation
    # using the function `get net profit` instead? The problem is
    # roughly, that in my notes I don't take into consideration
    # that the amount sold also affects the price.
    # NOTE: It may be best to use an initial estimate
    # for the amount in when determining the buying/selling dex

    amounts_out = []
    amount_in = _amount_in
    amt_in_tkn0_0 = amount_in / 2
    for dex_index, dex_name in enumerate(bot_config.dex_names):
        # This includes the trading fees of the dexes and the price alterations of our
        # swap. It does not include slippage nor the fees from the flashloan.
        reserve0, reserve1 = _reserves[
            dex_index
        ]  # get_reserves(_pair_dex_data, dex_index, _verbose=True)

        amount_out = get_dex_ammount_out(
            reserve0,
            reserve1,
            amt_in_tkn0_0,
            _dex_fees[dex_index],
            _slippages[dex_index],
        )

        amounts_out.append(amount_out)
        if _verbose:
            print(
                f"The token1/token0 price "
                f"in {dex_name} is approx (frictionless) "
                f"{get_approx_price(reserve0, reserve1)}\n"
                f"Amount out: {amount_out/1e18}"
            )
            if bot_config.debug_mode:
                # Currently just a placeholder for quick debugging
                # print(f"The price in Coingecko is {bot_config.coingecko_price()}")
                pass
    max_index = np.argmax(amounts_out)
    min_index = np.argmin(amounts_out)

    return max_index, min_index


def get_net_profit_functional(*args):
    def f(_amount_in):
        return get_net_profit(_amount_in, *args)

    return f


def get_net_profit(
    _amount_in,
    _reserves_buying_dex,
    _reserves_selling_dex,
    _fees_buy_dex,
    _fees_sell_dex,
    _slippage_buy_dex,
    _slippage_sell_dex,
    _lending_fee,
):
    # TODO: Create a structure (a dictionary) for these arguments?
    amt_in_tkn0_0 = _amount_in / 2

    amt_out_tkn1_0 = get_dex_ammount_out(
        *_reserves_buying_dex, amt_in_tkn0_0, _fees_buy_dex, _slippage_buy_dex
    )
    # Frictionless (IRL this will have been done before requesting the flashloan,
    # that's why we make this swap as frictionless)
    # FIXME:  Is it reasonable to use the best dex possible since this swap is
    # really done before the flashloan? I always can flashloan a little more
    # in order to make sure I have this amt_in_tok1 to sell at the best selling dex now

    # FIXME: Note that this amount has already been computed once when determining
    # the buying and selling dex. It is a small computation and probably
    # it is unnecessary to address this
    amt_in_tkn1_1 = amt_in_tkn0_0 / get_approx_price(
        _reserves_buying_dex[0], _reserves_buying_dex[1]
    )

    # Sell amt_in_tokn1 in the selling dex
    amt_out_tkn0_1 = get_dex_ammount_out(
        _reserves_selling_dex[1],
        _reserves_selling_dex[0],
        amt_in_tkn1_1,
        _fees_sell_dex,
        _slippage_sell_dex,
    )

    amt_out_tkn0_0 = amt_out_tkn1_0 / get_approx_price(
        _reserves_selling_dex[1], _reserves_selling_dex[0]
    )
    final_amount_out = amt_out_tkn0_0 + amt_out_tkn0_1
    final_amount_out -= (1 + (_lending_fee / 100)) * _amount_in
    return final_amount_out


def get_dex_ammount_out(_reserve0, _reserve1, _amount_in, _dex_fee, _slippage):
    # This is derived from the x*y=k formula: the balances x',y' after the swap
    # have to satisgy x' * y' = k
    # print(_reserve0)
    numerator = _amount_in * (1 - _dex_fee / 100) * _reserve1
    denominator = _reserve0 + (1 - _dex_fee / 100) * _amount_in
    amount_out = numerator / denominator
    amount_out = amount_out * (1 - (_slippage / 100))
    return amount_out


def get_approx_price(_reserve0, _reserve1):
    return _reserve0 / _reserve1


def get_reserves(_pair_dex_data, _dex_index, _verbose=False):
    # The way this function is designed is so that it is as fast as possible
    # when retrieving prices. The arguments of the function consist of precomputed
    # static data about the dex pairs and individual tokens
    account = get_account()
    pair_data = _pair_dex_data["pair_data"]
    token_data = _pair_dex_data["token_data"]
    pair, reversed_order = pair_data[bot_config.dex_names[_dex_index]]
    token0, name0, decimals0 = token_data[bot_config.token_names[0]]
    token1, name1, decimals1 = token_data[bot_config.token_names[1]]

    reserve0, reserve1, block_timestamp_last = pair.getReserves({"from": account})
    if reversed_order:
        _ = reserve0
        reserve0 = reserve1
        reserve1 = _
    reserve0 *= 10 ** (max(decimals0, decimals1) - decimals0)
    reserve1 *= 10 ** (max(decimals0, decimals1) - decimals1)

    return reserve0, reserve1


def get_optimal_amount_in(
    _reserves_buying_dex,
    _reserves_selling_dex,
    _fees_buy_dex,
    _fees_sell_dex,
    _slippage_buy_dex,
    _slippage_sell_dex,
    _lending_fee,
    _return_optimal_amount_out=False,
    _verbose=False,
):
    """The function has the form (ax)/(bx+c) + (a'x)/(b'x+c') -kx
    where x=_amt_in
    """

    # TODO: What does it mean when the optimal initial amount is negative?

    f = get_net_profit_functional(
        _reserves_buying_dex,
        _reserves_selling_dex,
        _fees_buy_dex,
        _fees_sell_dex,
        _slippage_buy_dex,
        _slippage_sell_dex,
        _lending_fee,
    )

    def reverse(fun):
        def _fun(x):
            return -fun(x)

        return _fun

    _f = reverse(f)

    res = minimize_scalar(_f, bounds=(0, 1e30), method="bounded")
    optimal_amount_in = res.x
    if _verbose:
        print(f"Optimal initial amount: {optimal_amount_in}")
    if not _return_optimal_amount_out:
        return optimal_amount_in
    else:
        return optimal_amount_in, f(optimal_amount_in)
