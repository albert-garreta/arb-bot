from tkinter import E
from scripts.utils import (
    get_account,
    get_dex_router_and_factory,
    get_token_names_and_addresses,
)
from brownie import interface, network
import bot_config


# TODO: Create a class for the data structure used
class dotdict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def get_arbitrage_data(_buy_dex_index, _reserves):
    sell_dex_index = (_buy_dex_index + 1) % 2
    arb_data = ArbitrageData()
    arb_data.sell_dex_index = sell_dex_index
    arb_data.reserves_buying_dex = _reserves[_buy_dex_index]
    arb_data.reserves_selling_dex = _reserves[sell_dex_index]
    arb_data.fees_buy_dex = bot_config.dex_fees[_buy_dex_index]
    arb_data.fees_sell_dex = bot_config.dex_fees[sell_dex_index]
    arb_data.slippage_buy_dex = bot_config.slippages[_buy_dex_index]
    arb_data.slippage_sell_dex = bot_config.slippages[sell_dex_index]
    return arb_data


class ArbitrageData(dotdict):
    def __init__(self):
        self.reserves_buying_dex = None
        self.reserves_selling_dex = None
        self.fees_buy_dex = None
        self.fees_sell_dex = None
        self.slippage_buy_dex = None
        self.slippage_sell_dex = None
        self.lending_fee = None
        self._max_value_of_flashloan = None
        self.buy_dex_index = None
        self.sell_dex_index = None
        self.optimal_borrow_amount = None
        self.net_profit = None

    def get_dex_info(self, _buying):
        if _buying:
            return self.get_buy_dex_data()
        else:
            return self.get_sell_dex_data()

    def get_buy_dex_data(self):
        dex_data = dotdict()
        dex_data.reserves_in = self.reserves_buying_dex["token0"]
        dex_data.reserves_out = self.reserves_buying_dex["token1"]
        dex_data.fee = self.fees_buy_dex
        dex_data.slippage = self.slippage_buy_dex

    def get_sell_dex_data(self):
        dex_data = dotdict()
        dex_data.reserves_in = self.reserves_selling_dex["token1"]
        dex_data.reserves_out = self.reserves_selling_dex["token0"]
        dex_data.fee = self.fees_sell_dex
        dex_data.slippage = self.slippage_sell_dex

    def get_profit_ratio(self):
        return 100 * (self.net_profit / self.borrow_amount - 1)

    def print_summary(self):

        if pass_arbitrage_requirements(net_profit, profit_ratio):
            msg = f"ACT\n"
            msg += f"Reserves buying dex: {_reserves_all_dexes[buying_dex_index]}\n"
            msg += f"Reserves selling dex: {_reserves_all_dexes[selling_dex_index]}\n"
            msg += f"Profit ratio {final_profit_ratio}.\n"
            msg += (
                f"Optimal amount in {optimal_amount_in/(10**bot_config.decimals[0])}\n"
            )
            msg += (
                f"Gains (in token0) {final_amount_out/(10**bot_config.decimals[0])}\n\n"
            )

            print_and_log(msg, bot_config.log_searches_path)
            tkn0_to_buy = 0.5 * optimal_amount_in
            tkn1_to_sell = 0.5 * optimal_amount_in / _price_tkn1_to_tkn0

        if _verbose:
            print(f"Buying dex: {bot_config.dex_names[arb_data.buy_dex_index]}")
            print(f"Reserves buying dex: {arb_data.reserves_buying_dex}")
            print(f"Reserves selling dex: {arb_data.reserves_selling_dex}")
            print(
                f"Optimal amount to borrow: {arb_data.optimal_borrow_amount/(10**bot_config.decimals[0])}"
            )
            print(f"Net profit: {arb_data.net_profit/(10**bot_config.decimals[0])}")
            print(f"Profit %: {arb_data.get_profit_ratio()}\n")


def get_dex_reserves(_pair_dex_data, _dex_index, _verbose=False):
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


def get_all_dex_reserves(_pair_dex_data) -> tuple[tuple[int, int]]:
    if bot_config.force_actions:
        return bot_config.forced_reserves
    else:
        return [
            get_dex_reserves(_pair_dex_data, dex_index)
            for dex_index in range(len(bot_config.dex_names))
        ]


def get_all_dex_to_pair_data():
    # TODO: should this and the following be placed here?

    # Use a class for the data structure we are creating?
    print("Retrieving all necessary pair contracts and data...")
    # print(f"Token names: {bot_config.token_names}")
    dex_to_pair_data = dict()
    dex_to_pair_data["pair_data"] = {}
    token_names, token_addresses = get_token_names_and_addresses()

    for dex_name in bot_config.dex_names:
        pair, reversed_order = get_pair_info(dex_name, token_addresses)
        dex_to_pair_data["pair_data"][dex_name] = [
            pair,
            reversed_order,
        ]
    dex_to_pair_data["token_data"] = {}
    for token_name, token_address in zip(token_names, token_addresses):
        token = interface.IERC20(token_address)
        print(token.name())
        decimals = token.decimals()
        bot_config.decimals.append(decimals)
        bot_config.token_names.append(token_name)
        name = token.name()
        dex_to_pair_data["token_data"][token_name] = [
            token,
            name,
            decimals,
        ]

    print("Retrieved")
    print("Token names", bot_config.token_names)
    print("Token decimals", bot_config.decimals)
    return dex_to_pair_data


def get_pair_info(_dex_name, token_addresses, _version="V2"):
    account = get_account()

    _, factory = get_dex_router_and_factory(_dex_name)

    pair_address = factory.getPair(*token_addresses, {"from": account})
    # Note: getReserves can also be called from the UniswapV2Library (see function below)
    pair = interface.IUniswapV2Pair(pair_address, {"from": account})

    # FIXME:
    # It seems that the `Pair` sometimes interchanges the order of the tokens: eg in
    # in mainnet's uniswap, if you pass (WETH, USDT) they get registerd correctly,
    # but in ftm-main's spookyswap, if you pass (WFTM, USDC) they get registered
    # in the reverse order.
    reversed_order = order_has_reversed(token_addresses, pair)

    return pair, reversed_order


def order_has_reversed(_token_addresses, _pair):
    account = get_account()
    token0_address_in_pair = _pair.token0({"from": account})
    token1_address_in_pair = _pair.token1({"from": account})
    if (
        token0_address_in_pair == _token_addresses[1]
        and token1_address_in_pair == _token_addresses[0]
    ):
        return True
    elif (
        token0_address_in_pair == _token_addresses[0]
        and token1_address_in_pair == _token_addresses[1]
    ):
        return False
    else:
        raise Exception
