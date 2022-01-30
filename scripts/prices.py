from tkinter import E
from scripts.utils import (
    print_args_wrapped,
    fix_parameters_of_function,
    reverse_scalar_fun,
    get_account,
)
import numpy as np
from scipy.optimize import minimize_scalar, minimize
from copy import deepcopy
from brownie import network, interface, config


def find_optimal_borrow_amount_and_net_profit(_arbitrage_data):
    f = fix_parameters_of_function(
        _fun=get_net_profit_v3,
        _args_1_tuple=(_arbitrage_data,),
    )
    _f = reverse_scalar_fun(f)
    # FIXME: If using method='bound', this sometimes incorrectly returns the given upper bound
    res = minimize_scalar(
        _f, bounds=(0, _arbitrage_data.max_value_of_flashloan), method="bounded"
    )
    optimal_amount = res.x
    net_profit = f(optimal_amount)
    return optimal_amount, net_profit


def get_net_profit_v3(_amount_tkn1_to_borrow, _arbitrage_data):
    """
    Returns:
        float: net_profit
    """
    # TODO: Create a structure (a dictionary) for these arguments?

    buying_dex_data = _arbitrage_data.get_dex_data(_buying=True)
    selling_dex_data = _arbitrage_data.get_dex_data(_buying=False)
    amt_out_tkn0_selling_dex1 = get_dex_amount_out(
        _amount_tkn1_to_borrow,
        selling_dex_data,
    )
    amt_tkn0_to_return_dex0 = get_dex_amount_in(
        _amount_tkn1_to_borrow,
        buying_dex_data,
    )
    net_profit = amt_out_tkn0_selling_dex1 - amt_tkn0_to_return_dex0
    return net_profit


def get_dex_amount_out(_amount_in, dex_data):
    return _get_dex_amount_out(
        _amount_in,
        dex_data.reserves_in,
        dex_data.reserves_out,
        dex_data.fee,
        dex_data.slippage,
    )


def get_dex_amount_in(_amount_out, dex_data):
    return _get_dex_amount_in(
        _amount_out ,
        dex_data.reserves_in ,
        dex_data.reserves_out ,
        dex_data.fee,
        dex_data.slippage,
    ) 


# @print_args_wrapped
def _get_dex_amount_out(_amount_in, _reserve_in, _reserve_out, _dex_fee, _slippage=0):
    # Function from UniswapV2Library with slippage
    fee = 1 - _dex_fee / 100
    numerator = _amount_in * fee * _reserve_out
    denominator = _reserve_in + fee * _amount_in
    amount_out = numerator / denominator
    amount_out = amount_out * (1 - (_slippage / 100))
    return amount_out


def _get_dex_amount_in(_amount_out, _reserve_in, _reserve_out, _dex_fee, _slippage=0):
    # Function from UniswapV2Library with slippage
    # TODO: the fee here appears once instead of twice as above. Is this advantageous?
    fee = 1 - _dex_fee / 100
    numerator = _amount_out * _reserve_in
    denominator = _reserve_out - fee * _amount_out
    amount_out = numerator / denominator
    amount_out += 1  # this is in UniswapV2Library. Why?
    amount_out = amount_out * (1 - (_slippage / 100))
    return amount_out


def get_oracle_price(oracle=None, buying=True):
    if oracle is None:
        oracle_address = config["networks"][network.show_active()]["price_feed_address"]
        oracle = interface.AggregatorV3Interface(oracle_address)
    _, price, _, _, _ = oracle.latestRoundData({"from": get_account()})
    # TODO: implement correct general decimal formatting. Now assuming 8 decimals
    price /= 1e8
    if buying:
        return 1 / price
    else:
        return price


# DEPRECATED
# ----------------------------------------------------------------
# ----------------------------------------------------------------
# ----------------------------------------------------------------
# ----------------------------------------------------------------


def get_approx_price(_all_dex_reserves, _buying=True):
    prices = []
    for _dex_reserves in _all_dex_reserves:
        reserve0, reserve1 = _dex_reserves
        if _buying:
            prices.append(reserve0 / reserve1)
        else:
            prices.append(reserve1 / reserve0)
    return (prices[0] + prices[1]) / 2


def get_net_profit(
    _amount_in,
    _reserves_buying_dex,
    _reserves_selling_dex,
    _fees_buy_dex,
    _fees_sell_dex,
    _slippage_buy_dex,
    _slippage_sell_dex,
    _lending_fee,
    _price_tkn1_to_tkn0,
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

    amt_in_tkn0_0 = _amount_in

    amt_out_tkn1_0 = get_dex_amount_out(
        *_reserves_buying_dex, amt_in_tkn0_0, _fees_buy_dex, _slippage_buy_dex
    )
    # Frictionless (IRL this will have been done before requesting the flashloan,
    # that's why we make this swap as frictionless)
    # FIXME:  Is it reasonable to use the best dex possible since this swap is
    # really done before the flashloan? I always can flashloan a little more
    # in order to make sure I have this amt_in_tok1 to sell at the best selling dex now

    # amt_in_tkn1_1 = amt_in_tkn0_0 / _price_tkn1_to_tkn0

    # Sell amt_in_tokn1 in the selling dex
    amt_out_tkn0_1 = get_dex_amount_out(
        _reserves_selling_dex[1],
        _reserves_selling_dex[0],
        amt_out_tkn1_0,
        _fees_sell_dex,
        _slippage_sell_dex,
    )

    # amt_out_tkn0_0 = amt_out_tkn1_0 / get_approx_price(
    #    [_reserves_buying_dex, _reserves_selling_dex], _buying=False
    # )
    # amt_out_tkn0_0 = amt_out_tkn1_0 * _price_tkn1_to_tkn0

    # final_amount_out = amt_out_tkn0_0 + amt_out_tkn0_1
    final_amount_out = amt_out_tkn0_1
    final_amount_out -= (1 + (_lending_fee / 100)) * _amount_in
    return final_amount_out


def get_optimal_amount_in_2(
    _reserves_buying_dex,
    _reserves_selling_dex,
    _fees_buy_dex,
    _fees_sell_dex,
    _slippage_buy_dex,
    _slippage_sell_dex,
    _lending_fee,
    _price_tkn1_to_tkn0,
    _max_value_of_flashloan=np.inf,
    _return_optimal_amount_out=False,
    _verbose=False,
):
    """The function has the form (ax)/(bx+c) + (a'x)/(b'x+c') -kx
    where x=_amt_in
    """

    # TODO: What does it mean when the optimal initial amount is negative?

    f = get_net_profit2_functional(
        _reserves_buying_dex,
        _reserves_selling_dex,
        _fees_buy_dex,
        _fees_sell_dex,
        _slippage_buy_dex,
        _slippage_sell_dex,
        _lending_fee,
        _price_tkn1_to_tkn0,
    )

    def reverse(fun):
        def _fun(x):
            return -fun(x)

        return _fun

    _f = reverse(f)

    res = minimize(
        _f,
        x0=np.array([5e21, 11e21]),
        method="Nelder-Mead",
        tol=1e-6,
        bounds=[(0, 10e21), (0, 30e21)],
    )
    optimal_amount = res.x
    # optimal_amount_tkn1 = optimal_amount_tkn0*0.5 /_price_tkn1_to_tkn0
    if _verbose:
        print(f"Optimal initial amount: {optimal_amount}")
    if not _return_optimal_amount_out:
        return optimal_amount
    else:
        return optimal_amount, f(optimal_amount)


def get_net_profit2(
    _amts,
    _reserves_buying_dex,
    _reserves_selling_dex,
    _fees_buy_dex,
    _fees_sell_dex,
    _slippage_buy_dex,
    _slippage_sell_dex,
    _lending_fee,
    _rate_tkn1_to_tkn0,
):
    _amt_tkn0 = _amts[0]
    _amt_tkn1 = _amts[1]
    amt_out_tkn1_0 = get_dex_amount_out(
        *_reserves_buying_dex,
        _amt_tkn0,
        _fees_buy_dex,
        _slippage_buy_dex,
    )
    amt_out_tkn0_1 = get_dex_amount_out(
        _reserves_selling_dex[1],
        _reserves_selling_dex[0],
        _amt_tkn1,
        _fees_sell_dex,
        _slippage_sell_dex,
    )
    net_tkn0_out = amt_out_tkn0_1 - _amt_tkn0 - _amt_tkn0 * (_lending_fee / 100)
    net_tkn1_out = amt_out_tkn1_0 - _amt_tkn1 - _amt_tkn1 * (_lending_fee / 100)
    # return net_tkn0_out, net_tkn1_out
    net_tkn1_out_in_tkn0 = _rate_tkn1_to_tkn0 * net_tkn1_out
    net_profit = net_tkn0_out + net_tkn1_out_in_tkn0
    return net_profit


def get_net_profit2_functional(*args):
    def f(amts):
        return get_net_profit2(amts, *args)

    return f


@print_args_wrapped
def get_optimal_amounts(
    _reserves_buying_dex,
    _reserves_selling_dex,
    _fees_buy_dex,
    _fees_sell_dex,
    _slippage_buy_dex,
    _slippage_sell_dex,
    _lending_fee,
    _rate_tkn1_to_tkn0,
    _max_tkn0=np.inf,
    _max_tkn1=np.inf,
):
    lambda1 = 0
    lambda2 = 0
    alpha = _rate_tkn1_to_tkn0
    k = 100 / _lending_fee

    a_ = (
        (1 - _fees_buy_dex / 100)
        * (1 - _slippage_buy_dex / 100)
        * _reserves_buying_dex[1]
    )
    b_ = 1 - _fees_buy_dex / 100
    c_ = _reserves_buying_dex[0]
    opt_tokn0_amount = (1 / (b_ * k)) * (
        -c_ + np.sqrt((alpha - lambda2) * a_ * c_ / (1 - lambda1) * (k + 1))
    )
    opt_tokn0_amount = min(_max_tkn0, opt_tokn0_amount)

    a = (
        (1 - _fees_sell_dex / 100)
        * (1 - _slippage_sell_dex / 100)
        * _reserves_selling_dex[0]
    )
    b = 1 - _fees_sell_dex / 100
    c = _reserves_selling_dex[1]
    opt_tokn1_amount = (1 / (b * k)) * (
        -c + np.sqrt((1 - lambda1) * a * c / (alpha - lambda2) * (k + 1))
    )
    opt_tokn1_amount = min(_max_tkn1, opt_tokn1_amount)

    return opt_tokn0_amount, opt_tokn1_amount
