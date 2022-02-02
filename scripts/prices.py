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
        _amount_out,
        dex_data.reserves_in,
        dex_data.reserves_out,
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
    # TODO: note the fee here appears once instead of twice as above.
    fee = 1 - _dex_fee / 100
    numerator = _amount_out * _reserve_in
    denominator = (_reserve_out - _amount_out) * fee
    _amount_in = numerator / denominator
    _amount_in += 1  # this is in UniswapV2Library. Why?
    _amount_in = _amount_in / (1 - (_slippage / 100))
    return _amount_in


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
