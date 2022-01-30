from tkinter import E
from scripts.utils import get_account, print_args_wrapped
import numpy as np
from brownie import interface, network
import bot_config
from copy import deepcopy


# TODO: Most functions here should be methods of ArbitrageData, I think


def update_arbitrage_data(_arbitrage_data):
    # NOTE: I think this is the most expensive call in an epoch without action.
    _all_reserves = get_all_dex_reserves(_arbitrage_data)
    return get_best_possible_arb_data(_arbitrage_data, _all_reserves)


def get_best_possible_arb_data(_arbitrage_data, _reserves):
    """
    Check the two combinatios of buying/selling dexes and see with which one
    we get better net profits"""
    best_metrics = get_best_metrics(_arbitrage_data, _reserves)
    return recover_best_arb_data_from_best_metrics(
        _arbitrage_data, best_metrics, _reserves
    )


def get_best_metrics(_arbitrage_data, _reserves):
    best_metrics = {
        "borrow_amount": -np.inf,
        "net_profit": -np.inf,
        "buy_dex_index": 0,
    }
    for buy_dex_index in range(_arbitrage_data.num_dexes):
        _arbitrage_data.update_given_buy_dex_and_reserves(buy_dex_index, _reserves)
        best_metrics = update_best_metrics(_arbitrage_data, best_metrics)
    return best_metrics


def update_best_metrics(_arb_data, _best_metrics):
    borrow_amt, net_profit = _arb_data.get_optimal_borrow_amount_and_net_profit()
    if net_profit > _best_metrics["net_profit"]:
        _best_metrics["net_profit"] = net_profit
        _best_metrics["borrow_amount"] = borrow_amt
    return _best_metrics


def recover_best_arb_data_from_best_metrics(_arbitrage_data, _best_metrics, _reserves):
    # TODO: this is inefficient because we already ran this method.
    # At least we are not reoptimizing the net_profit function
    buy_dex_index = _best_metrics["buy_dex_index"]
    net_profit = _best_metrics["net_profit"]
    borrow_amount = _best_metrics["borrow_amount"]
    _arbitrage_data.update_given_buy_dex_and_reserves(buy_dex_index, _reserves)
    _arbitrage_data.update_optimal_borrow_amount_and_net_profit(
        borrow_amount, net_profit
    )
    return _arbitrage_data


def get_all_dex_reserves(_arbitrage_data) -> tuple[tuple[int, int]]:
    if bot_config.force_actions:
        return bot_config.forced_reserves
    else:
        return [
            get_dex_reserves(_arbitrage_data, dex_index)
            for dex_index in range(len(bot_config.dex_names))
        ]


def get_dex_reserves(_arbitrage_data, _dex_index):
    # The way this function is designed is so that it is as fast as possible
    # when retrieving prices. The arguments of the function consist of precomputed
    # static data about the dex pairs and individual tokens
    pair = _arbitrage_data.token_pairs_dexes[_dex_index]
    reserve0, reserve1, block_timestamp_last = pair.getReserves({"from": get_account()})
    return prepare_reserves(reserve0, reserve1, _arbitrage_data, _dex_index)


def prepare_reserves(_reserve0, _reserve1, _arbitrage_data, _dex_index):
    reversed_order = _arbitrage_data.reversed_orders[_dex_index]
    reserve0, reserve1 = update_reserves_if_reversed_order(
        _reserve0, _reserve1, reversed_order
    )
    return update_reserves_decimals(reserve0, reserve1, _arbitrage_data.decimals)


def update_reserves_if_reversed_order(reserve0, reserve1, reversed_order):
    if reversed_order:
        _ = reserve0
        reserve0 = reserve1
        reserve1 = _
    return reserve0, reserve1


def update_reserves_decimals(reserve0, reserve1, decimals):
    decimals0, decimals1 = decimals
    reserve0 *= 10 ** (max(decimals0, decimals1) - decimals0)
    reserve1 *= 10 ** (max(decimals0, decimals1) - decimals1)
    return reserve0, reserve1
