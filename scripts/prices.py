from tkinter import E
from scripts.utils import get_account, print_args_wrapped
import bot_config
import numpy as np
from scipy.optimize import minimize_scalar
from brownie import interface, config, network


def get_arbitrage_profit_info(
    _reserves,
    _price_tkn1_to_tkn0,
    _dex_fees,
    _slippages,
    _lending_pool_fee,
    _verbose=False,
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

    if bot_config.force_actions:
        _reserves = bot_config.forced_reserves

    buying_dex_index, opt_amount_in, opt_amount_out = get_buying_dex_and_amounts_in_out(
        _reserves,
        _price_tkn1_to_tkn0,
        _dex_fees,
        _slippages,
        _lending_pool_fee,
        _verbose,
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
        print(f"Optimal amount in: {opt_amount_in/(10**bot_config.decimals[0])}")
        print(f"Final amount out: {opt_amount_out/(10**bot_config.decimals[0])}")
        print(f"Profit %: {final_profit_ratio}\n")
    return (
        final_profit_ratio,
        opt_amount_in,
        opt_amount_out,
        buying_dex_index,
        (buying_dex_index + 1) % 2,
    )


def get_buying_dex_and_amounts_in_out(
    _reserves,
    _price_tkn1_to_tkn0,
    _dex_fees,
    _slippages,
    _lending_pool_fee,
    _verbose=False,
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
            _price_tkn1_to_tkn0,
            bot_config.max_value_of_flashloan,
            _return_optimal_amount_out=True,
            _verbose=False,
        )

        opt_amounts_in.append(opt_amount_in)
        opt_amounts_out.append(opt_amount_out)
        if _verbose:
            print(
                f"The token1/token0 price "
                f"in {dex_name} is approx (frictionless) "
                f"{_price_tkn1_to_tkn0}"
                # f"Optimal amount in: {opt_amount_in/(10**bot_config.decimals[0])}\n"
                # f"Optimal amount out: {opt_amount_out/(10**bot_config.decimals[0])}"
            )

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

    amt_in_tkn0_0 = _amount_in / 2

    amt_out_tkn1_0 = get_dex_ammount_out(
        *_reserves_buying_dex, amt_in_tkn0_0, _fees_buy_dex, _slippage_buy_dex
    )
    # Frictionless (IRL this will have been done before requesting the flashloan,
    # that's why we make this swap as frictionless)
    # FIXME:  Is it reasonable to use the best dex possible since this swap is
    # really done before the flashloan? I always can flashloan a little more
    # in order to make sure I have this amt_in_tok1 to sell at the best selling dex now

    amt_in_tkn1_1 = amt_in_tkn0_0 / _price_tkn1_to_tkn0

    # amt_in_tkn0_0 / get_approx_price(
    #     [_reserves_buying_dex, _reserves_selling_dex], _buying=True
    # )

    # Sell amt_in_tokn1 in the selling dex
    amt_out_tkn0_1 = get_dex_ammount_out(
        _reserves_selling_dex[1],
        _reserves_selling_dex[0],
        amt_in_tkn1_1,
        _fees_sell_dex,
        _slippage_sell_dex,
    )

    amt_out_tkn0_0 = amt_out_tkn1_0 / get_approx_price(
        [_reserves_buying_dex, _reserves_selling_dex], _buying=False
    )
    amt_out_tkn0_0 = amt_out_tkn1_0 * _price_tkn1_to_tkn0

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


def get_approx_price(_all_dex_reserves, _buying=True):
    # if bot_config.get_frictionless_price_from_oracle:
    #     return get_oracle_price(buying=_buying)
    prices = []
    for _dex_reserves in _all_dex_reserves:
        reserve0, reserve1 = _dex_reserves
        if _buying:
            prices.append(reserve0 / reserve1)
        else:
            prices.append(reserve1 / reserve0)
    return (prices[0] + prices[1]) / 2


# def get_oracle_price(oracle=None, buying=True):
#     if oracle is None:
#         oracle_address = config["networks"][network.show_active()]["price_feed_address"]
#         oracle = interface.AggregatorV3Interface(oracle_address)
#     # price = oracle.getLatestPrice({"from": get_account()})  # FTM to USD
#     _, price, _, _, _ = oracle.latestRoundData({"from": get_account()})  # FTM to USD
#     # TODO: check decimals for other feeds
#     price /= 1e8
#     if buying:
#         return 1 / price
#     else:
#         return price


def get_optimal_amount_in(
    _reserves_buying_dex,
    _reserves_selling_dex,
    _fees_buy_dex,
    _fees_sell_dex,
    _slippage_buy_dex,
    _slippage_sell_dex,
    _lending_fee,
    _price_tkn1_to_tkn0,
    _max_value_of_flashloan,
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
        _price_tkn1_to_tkn0,
    )

    def reverse(fun):
        def _fun(x):
            return -fun(x)

        return _fun

    _f = reverse(f)

    res = minimize_scalar(_f, bounds=(0, _max_value_of_flashloan), method="bounded")
    optimal_amount = res.x
    # optimal_amount_tkn1 = optimal_amount_tkn0*0.5 /_price_tkn1_to_tkn0
    if _verbose:
        print(f"Optimal initial amount: {optimal_amount}")
    if not _return_optimal_amount_out:
        return (optimal_amount,)
    else:
        return optimal_amount, f(optimal_amount)


# DEPRECATED


def get_net_profit2(
    _amt_tkn0,
    _amt_tkn1,
    _reserves_buying_dex,
    _reserves_selling_dex,
    _fees_buy_dex,
    _fees_sell_dex,
    _slippage_buy_dex,
    _slippage_sell_dex,
    _lending_fee,
    _rate_tkn1_to_tkn0,
):
    amt_out_tkn1_0 = get_dex_ammount_out(
        *_reserves_buying_dex,
        _amt_tkn0,
        _fees_buy_dex,
        _slippage_buy_dex,
    )
    amt_out_tkn0_1 = get_dex_ammount_out(
        _reserves_selling_dex[1],
        _reserves_selling_dex[0],
        _amt_tkn1,
        _fees_sell_dex,
        _slippage_sell_dex,
    )
    net_tkn0_out = amt_out_tkn0_1 - _amt_tkn0 - _amt_tkn0 * (_lending_fee / 100)
    net_tkn1_out = amt_out_tkn1_0 - _amt_tkn1 - _amt_tkn1 * (_lending_fee / 100)
    net_tkn1_out_in_tkn0 = _rate_tkn1_to_tkn0 * net_tkn1_out
    net_profit = net_tkn0_out + net_tkn1_out_in_tkn0
    return net_profit


def get_net_profit2_functional(*args):
    def f(
        _amt_tkn0,
        _amt_tkn1,
    ):
        return get_net_profit2(_amt_tkn0, _amt_tkn1, *args)

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
