import bot_config
from brownie import interface, config, network
from scripts.utils import (
    get_account,
    get_token_names_and_addresses,
    swap_if_true_flag,
    convert_to_wei,
)
import pycoingecko

cg = pycoingecko.CoinGeckoAPI()


class dotdict(dict):
    """Any class inheriting from this will be a dictionary whose attributes can be accessed with .dot notation"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class StaticPairData(dotdict):
    """This data structure stores all the necessary static information the bot needs
    about a *pair of tokens* and a pair of dexes.

    A further class called `StateData` inherits from this.
    The latter manages all information that is variable through time (such as dex's reserves).

    """

    def __init__(self, index0, index1):
        self.num_dexes = 2
        self.tokens = []
        self.token_names = []
        self.decimals = []
        self.token_addresses = []
        self.dex_names = []
        self.dex_fees = []
        self.pair_contracts = []
        self.dex_routers = []
        self.dex_factories = []
        self.ordered_token_name_pairs = []
        # `UniswapV2Pair` sometimes uses a token order different than ours
        self.reversed_orders = []
        self.max_value_of_flashloan = None
        self.summary_message = None
        self.reserves = []
        self.dict_info_token_pairs = None
        self.token_coingecko_ids = None
        # This is the minimum expected net profit in token0 that we require
        # before starting and arbitrage operation
        self.min_net_profit = None
        self.fill_in_data(index0, index1)

    """----------------------------------------------------------------
    Fill in functions
    ----------------------------------------------------------------"""

    def fill_in_data(self, index0, index1):
        # Fills in all the attributes declared in the __init__ method
        self.fill_in_basic_info(index0, index1)
        self.fill_in_token_contracts_and_decimals()
        self.fill_in_dex_routers_and_factories()
        self.fill_all_pair_contracts_and_reversions()
        self.fill_in_min_net_profit()

    def fill_in_basic_info(self, index0, index1):
        token_names, token_addresses = get_token_names_and_addresses()
        self.token_addresses = [token_addresses[index0], token_addresses[index1]]
        self.token_names = [token_names[index0], token_names[index1]]
        self.dex_names = bot_config.dex_names
        self.dex_fees = bot_config.dex_fees
        self.dex_slippages = bot_config.slippages
        self.max_value_of_flashloan = bot_config.max_value_of_flashloan
        cg_api_ids = config["networks"][network.show_active()]["coingecko_ids"]
        self.token_coingecko_ids = [cg_api_ids[index0], cg_api_ids[index1]]

    def fill_in_token_contracts_and_decimals(self):
        for token_address in self.token_addresses:
            token = interface.IERC20(token_address)
            decimals = token.decimals()
            self.tokens.append(token)
            self.decimals.append(decimals)

    def fill_in_dex_routers_and_factories(self):
        for dex_name in self.dex_names:
            router, factory = get_dex_router_and_factory(dex_name)
            self.dex_routers.append(router)
            self.dex_factories.append(factory)

    def fill_all_pair_contracts_and_reversions(self):
        for _dex_index in range(self.num_dexes):
            pair, reversed_order = self.get_pair_contract_and_reversion_info(_dex_index)
            self.pair_contracts.append(pair)
            self.reversed_orders.append(reversed_order)

    def get_pair_contract_and_reversion_info(self, _dex_index):
        account = get_account()
        pair_address = self.dex_factories[_dex_index].getPair(
            *self.token_addresses, {"from": account}
        )
        pair = interface.IUniswapV2Pair(pair_address)
        reversed_order = order_has_reversed(self.token_addresses, pair)
        return pair, reversed_order

    def fill_in_min_net_profit(self):
        # min_net_profit is the minimum expected net profit in token0 that we require
        # before starting and arbitrage operation
        price0 = cg.get_price(self.token_coingecko_ids[0], vs_currencies="usd")[
            self.token_coingecko_ids[0]
        ]["usd"]
        price0 = float(price0)
        self.min_net_profit = bot_config.min_net_profits_in_usd / price0

    """----------------------------------------------------------------
    End of fill-in methods.
    Beginning of reserve-updating methods
    ----------------------------------------------------------------"""

    def update_all_dexes_reserves(self) -> tuple[tuple[int, int]]:
        # Gets [token0_reserves, token1_reserves] for each dex
        if bot_config.force_actions and bot_config.forced_reserves:
            # This is used only for testing purposes
            self.reserves = bot_config.forced_reserves
        else:
            self.reserves = [
                self.get_dex_reserves(dex_index) for dex_index in range(self.num_dexes)
            ]

    def get_dex_reserves(self, _dex_index):
        # Gets [token0_reserves, token1_reserves] for a given dex's index
        pair = self.pair_contracts[_dex_index]
        reserve0, reserve1, block_timestamp_last = pair.getReserves(
            {"from": get_account()}
        )
        return self.prepare_reserves(reserve0, reserve1, _dex_index)

    def prepare_reserves(self, _reserve0, _reserve1, _dex_index):
        # 1: Reorders the reserves in case the stored token0, token1 order in the
        # pair contract does not match our conventions
        # 2: Sets all reserves decimals to 18 (wei)
        reversed_order = self.reversed_orders[_dex_index]
        reserve0, reserve1 = swap_if_true_flag(_reserve0, _reserve1, reversed_order)
        return self.update_reserves_decimals(reserve0, reserve1)

    def update_reserves_decimals(self, _reserve0, _reserve1):
        # Sets all reserves decimals to 18 (wei)
        decimals0, decimals1 = self.decimals
        _reserve0 = convert_to_wei(_reserve0, decimals0)
        _reserve1 = convert_to_wei(_reserve1, decimals1)
        return _reserve0, _reserve1


def order_has_reversed(_stored_token_addresses, _pair):
    # Given a list of two token addresses and an LP pair contract with these
    # addresses, returns True if the recorded orders on the list and the LP
    # does not match. Otherwise returns False
    account = get_account()
    token0_address_in_pair = _pair.token0({"from": account})
    token1_address_in_pair = _pair.token1({"from": account})
    if (
        token0_address_in_pair == _stored_token_addresses[1]
        and token1_address_in_pair == _stored_token_addresses[0]
    ):
        return True
    elif (
        token0_address_in_pair == _stored_token_addresses[0]
        and token1_address_in_pair == _stored_token_addresses[1]
    ):
        return False
    else:
        raise Exception


def get_all_dexes_and_factories(_dex_list):
    # Returns a list containing, for every dex, a tuple (router, factory) with the dex's
    # corresponding router and factory contracts.
    routers_and_factories = []
    for dex_name in _dex_list:
        routers_and_factories.append(get_dex_router_and_factory(dex_name))
    return routers_and_factories


def get_dex_router_and_factory(_dex_name):
    network_addresses = config["networks"][network.show_active()]
    dex_addresses = network_addresses["dexes"][_dex_name]
    # TODO: (minor detail) Do I need to instantiate them, or would it be enough to just pass the address?
    router = interface.IUniswapV2Router02(dex_addresses["swap_router_V2_address"])
    factory = interface.IUniswapV2Factory(dex_addresses["uniswap_factory_address"])
    return router, factory
