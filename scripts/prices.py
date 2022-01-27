from tkinter import E
from scripts.utils import get_account, print_args_wrapped
import bot_config
import numpy as np
from scipy.optimize import minimize_scalar


def get_arbitrage_profit_info(
    _reserves, _dex_fees, _slippages, _lending_pool_fee, _verbose=False
):
    """[summary]

    Args:
        _pair_dex_data ([type]): [description]
        _verbose (bool, optional): [description]. Defaults to False.

    Returns:
        final_profit_ratio,
        opt_amount_in,
        opt_amount_out,
        buying_dex_index,
        (buying_dex_index + 1) % 2,
    """

    # buying/selling dex: dex_names[max/min_index]

    # We take the maximum amount out possible. The buying dex is the one
    # with max_index, and the selling is the one with min_index

    # FIXME: what is a good amount in to pass here? (Amount in may affect the choice of
    # buying dex)
    buying_dex_index, opt_amount_in, opt_amount_out = get_buying_dex_and_amounts_in_out(
        _reserves, _dex_fees, _slippages, _lending_pool_fee, _verbose
    )

    reserves_buying_dex = _reserves[buying_dex_index]
    reserves_selling_dex = _reserves[(buying_dex_index + 1) % 2]

    final_profit_ratio = ((opt_amount_out / opt_amount_in)) * 100

    # max_delta = max(prices) - min(prices)
    # min_index = np.argmin(prices)
    # max_price_spread = 100 * max_delta / min(prices)
    if _verbose:
        print(f"Buying dex: {bot_config.dex_names[buying_dex_index]}")
        print(f"Selling dex: {bot_config.dex_names[(buying_dex_index + 1) % 2]}")
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
        (buying_dex_index + 1) % 2,
    )


def get_buying_dex_and_amounts_in_out(
    _reserves, _dex_fees, _slippages, _lending_pool_fee, _verbose=False
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

    opt_amounts_in = []
    opt_amounts_out = []
    for dex_index, dex_name in enumerate(bot_config.dex_names):
        # Check the two combinatios of buying/selling dexes and see with wich one
        # we get better net profits

        reserve0, reserve1 = _reserves[
            dex_index
        ]  # get_reserves(_pair_dex_data, dex_index, _verbose=True)
        reserves_buying_dex = _reserves[dex_index]
        reserves_selling_dex = _reserves[(dex_index + 1) % 2]
        fees_buying_dex = _dex_fees[dex_index]
        fees_selling_dex = _dex_fees[(dex_index + 1) % 2]
        slippage_buy_dex = _slippages[dex_index]
        slippage_sell_dex = _slippages[(dex_index + 1) % 2]

        opt_amount_in, opt_amount_out = get_optimal_amount_in(
            reserves_buying_dex,
            reserves_selling_dex,
            fees_buying_dex,
            fees_selling_dex,
            slippage_buy_dex,
            slippage_sell_dex,
            _lending_pool_fee,
            bot_config.max_amount_in,
            _return_optimal_amount_out=True,
            _verbose=False,
        )

        opt_amounts_in.append(opt_amount_in)
        opt_amounts_out.append(opt_amount_out)
        if _verbose:
            print(
                f"The token1/token0 price "
                f"in {dex_name} is approx (frictionless) "
                f"{get_approx_price(_reserves[dex_index], buying=True)}\n"
                f"Optimal amount in: {opt_amount_in/1e18}\n"
                f"Optimal amount out: {opt_amount_out/1e18}"
            )
            if bot_config.debug_mode:
                # Currently just a placeholder for quick debugging
                # print(f"The price in Coingecko is {bot_config.coingecko_price()}")
                pass

    buying_dex_index = np.argmax(opt_amounts_out)
    optimal_amount_in = opt_amounts_in[buying_dex_index]
    optimal_amount_out = opt_amounts_out[buying_dex_index]

    return buying_dex_index, optimal_amount_in, optimal_amount_out


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
    """[summary]

    Args:
        _amount_in ([type]): [description]
        _reserves_buying_dex ([type]): [description]
        _reserves_selling_dex ([type]): [description]
        _fees_buy_dex ([type]): [description]
        _fees_sell_dex ([type]): [description]
        _slippage_buy_dex ([type]): [description]
        _slippage_sell_dex ([type]): [description]
        _lending_fee ([type]): [description]

    Returns:
        float: net_profit
    """
    # TODO: Create a structure (a dictionary) for these arguments?

    # TODO: FIXME: instead of splitting into two halves, can we optimize the split ratio?
    amt_in_tkn0_0 = _amount_in / 2

    amt_out_tkn1_0 = get_dex_ammount_out(
        *_reserves_buying_dex, amt_in_tkn0_0, _fees_buy_dex, _slippage_buy_dex
    )
    # Frictionless (IRL this will have been done before requesting the flashloan,
    # that's why we make this swap as frictionless)
    # FIXME:  Is it reasonable to use the best dex possible since this swap is
    # really done before the flashloan? I always can flashloan a little more
    # in order to make sure I have this amt_in_tok1 to sell at the best selling dex now

    amt_in_tkn1_1 = amt_in_tkn0_0 / get_approx_price(_reserves_buying_dex, buying=True)

    # Sell amt_in_tokn1 in the selling dex
    amt_out_tkn0_1 = get_dex_ammount_out(
        _reserves_selling_dex[1],
        _reserves_selling_dex[0],
        amt_in_tkn1_1,
        _fees_sell_dex,
        _slippage_sell_dex,
    )

    amt_out_tkn0_0 = amt_out_tkn1_0 / get_approx_price(
        _reserves_selling_dex, buying=False
    )
    final_amount_out = amt_out_tkn0_0 + amt_out_tkn0_1
    final_amount_out -= (1 + (_lending_fee / 100)) * _amount_in
    return final_amount_out


def get_dex_ammount_out(_reserve0, _reserve1, _amount_in, _dex_fee, _slippage=0):
    # This is derived from the x*y=k formula: the balances x',y' after the swap
    # have to satisgy x' * y' = k
    # print(_reserve0)
    numerator = _amount_in * (1 - _dex_fee / 100) * _reserve1
    denominator = _reserve0 + (1 - _dex_fee / 100) * _amount_in
    amount_out = numerator / denominator
    amount_out = amount_out * (1 - (_slippage / 100))
    return amount_out


def get_approx_price(_dex_reserves, buying=True):
    reserve0, reserve1 = _dex_reserves
    if buying:
        return reserve0 / reserve1
    else:
        return reserve1 / reserve0


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
    _max_amount_in,
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

    res = minimize_scalar(_f, bounds=(0, _max_amount_in), method="bounded")
    optimal_amount_in = res.x
    if _verbose:
        print(f"Optimal initial amount: {optimal_amount_in}")
    if not _return_optimal_amount_out:
        return optimal_amount_in
    else:
        return optimal_amount_in, f(optimal_amount_in)
