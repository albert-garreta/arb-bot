import bot_config
from brownie import interface, config, network
from scripts.utils import get_account, get_token_names_and_addresses
from scripts.data_structures.dotdict import dotdict


class GeneralData(dotdict):
    def __init__(self):
        self.num_tokens = 2
        self.num_dexes = 2
        self.tokens = []
        self.token_names = []
        self.decimals = []
        self.token_addresses = []
        self.dex_names = []
        self.dex_fees = []
        self.token_pairs_dexes = []
        self.dex_routers = []
        # FIXME:
        # It seems that the `Pair` sometimes interchanges the order of the tokens: eg in
        # in mainnet's uniswap, if you pass (WETH, USDT) they get registerd correctly,
        # but in ftm-main's spookyswap, if you pass (WFTM, USDC) they get registered
        # in the reverse order.
        self.reversed_orders = []
        self.max_value_of_flashloan = None
        self.summary_message = None
        self.fill_in_data()

    def fill_in_data(self):
        print("Retrieving all necessary pair contracts and data...")
        self.fill_in_basic_info()
        self.fill_in_tokens_and_decimals()
        self.fill_in_token_pairs_and_reversions()
        print("Retrieved")
        print("Token names", bot_config.token_names)
        print("Token decimals", bot_config.decimals)

    def fill_in_basic_info(self):
        token_names, token_addresses = get_token_names_and_addresses()
        self.token_addresses = token_addresses
        self.token_names = token_names
        self.dex_names = bot_config.dex_names
        self.dex_fees = bot_config.dex_fees
        self.dex_slippages = bot_config.slippages
        self.max_value_of_flashloan = bot_config.max_value_of_flashloan

    def fill_in_tokens_and_decimals(self):
        for token_address in self.token_addresses:
            token = interface.IERC20(token_address)
            decimals = token.decimals()
            self.tokens.append(token)
            self.decimals.append(decimals)

    def fill_in_token_pairs_and_reversions(self):
        for dex_name in self.dex_names:
            router, pair, reversed_order = self.get_dex_contracts_and_reversion_info(
                dex_name
            )
            self.dex_routers.append(router)
            self.token_pairs_dexes.append(pair)
            self.reversed_orders.append(reversed_order)

    def get_dex_contracts_and_reversion_info(self, _dex_num):
        account = get_account()
        router, factory = get_dex_router_and_factory(_dex_num)
        pair_address = factory.getPair(*self.token_addresses, {"from": account})
        pair = interface.IUniswapV2Pair(pair_address, {"from": account})
        reversed_order = order_has_reversed(self.token_addresses, pair)
        return router, pair, reversed_order



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
