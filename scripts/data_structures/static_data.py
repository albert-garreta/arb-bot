import bot_config
from brownie import interface, config, network
from scripts.utils import get_account, get_token_names_and_addresses
import pycoingecko

cg = pycoingecko.CoinGeckoAPI()


class dotdict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class StaticPairData(dotdict):
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
        # FIXME:
        # The `UniswapV2Pair` sometimes interchanges the order of the tokens: eg in
        # in mainnet's uniswap, if you pass (WETH, USDT) they get registerd correctly,
        # but in ftm-main's spookyswap, if you pass (WFTM, USDC) they get registered
        # in the reverse order.
        self.reversed_orders = []
        self.max_value_of_flashloan = None
        self.summary_message = None
        self.reserves = []
        self.dict_info_token_pairs = None
        self.token_coingecko_ids = None
        self.min_net_profit = None
        self.fill_in_data(index0, index1)

    def fill_in_data(self, index0, index1):
        # print("Retrieving all necessary pair contracts and data...")
        self.fill_in_basic_info(index0, index1)
        self.fill_in_token_contracts_and_decimals()
        self.fill_in_dex_routers_and_factories()
        self.fill_all_pair_contracts_and_reversions()
        self.fill_in_min_net_profits()
        print("Retrieved")
        # print("Token names", bot_config.token_names)
        # print("Token decimals", bot_config.decimals)

    def fill_in_basic_info(self, index0, index1):
        token_names, token_addresses = get_token_names_and_addresses()
        self.token_addresses = [token_addresses[index0], token_addresses[index1]]
        self.token_names = [token_names[index0], token_names[index1]]
        self.dex_names = bot_config.dex_names
        self.dex_fees = bot_config.dex_fees
        self.dex_slippages = bot_config.slippages
        self.max_value_of_flashloan = bot_config.max_value_of_flashloan
        cg_api_ids = config["networks"][network.show_active()]["coingecko_ids"]
        print(cg_api_ids)
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
        pair = interface.IUniswapV2Pair(pair_address, {"from": account})
        reversed_order = order_has_reversed(self.token_addresses, pair)
        return pair, reversed_order

    def fill_in_min_net_profits(self):
        price0 = cg.get_price(self.token_coingecko_ids[0], vs_currencies="usd")[
            self.token_coingecko_ids[0]
        ]["usd"]
        price0 = float(price0)
        self.min_net_profit = bot_config.min_net_profits_in_usd / price0
        print(self.token_coingecko_ids)
        print(price0)
        print(bot_config.min_net_profits_in_usd)
        print(self.min_net_profit)

    def update_all_dexes_reserves(self) -> tuple[tuple[int, int]]:
        if bot_config.force_actions and bot_config.forced_reserves:
            self.reserves = bot_config.forced_reserves
        else:
            self.reserves = [
                self.get_dex_reserves(dex_index)
                for dex_index in range(len(bot_config.dex_names))
            ]

    def get_dex_reserves(self, _dex_index):
        pair = self.pair_contracts[_dex_index]
        reserve0, reserve1, block_timestamp_last = pair.getReserves(
            {"from": get_account()}
        )
        return self.prepare_reserves(reserve0, reserve1, _dex_index)

    def prepare_reserves(self, _reserve0, _reserve1, _dex_index):
        reversed_order = self.reversed_orders[_dex_index]
        reserve0, reserve1 = update_reserves_if_reversed_order(
            _reserve0, _reserve1, reversed_order
        )
        return update_reserves_decimals(reserve0, reserve1, self.decimals)


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


def get_all_dexes_and_factories(dex_list):
    routers_and_factories = []
    for dex_name in dex_list:
        routers_and_factories.append(get_dex_router_and_factory(dex_name))
    return routers_and_factories


def get_dex_router_and_factory(_dex_name):
    network_addresses = config["networks"][network.show_active()]
    # dex_name = network_addresses["dexes"]["names"][_dex_num]
    dex_addresses = network_addresses["dexes"][_dex_name]
    # Do I need to instantiate them, or would it be enough to just pass the address?
    router = interface.IUniswapV2Router02(dex_addresses["swap_router_V2_address"])
    factory = interface.IUniswapV2Factory(dex_addresses["uniswap_factory_address"])
    return router, factory
