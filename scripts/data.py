from tkinter import E
from scripts.utils import get_account, get_dex_router_and_factory, get_token_addresses
from brownie import interface
import bot_config


# TODO: Create a class for the data structure used
class dotdict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def unpack(self):
        pair_data = self["pair_data"]
        token_data = self["token_data"]
        pair, reversed_order = pair_data[dex_name]
        token0, name0, decimals0 = self["token_data"][bot_config.token_names[0]]
        token1, name1, decimals1 = self["token_data"][bot_config.token_names[1]]


def get_all_dex_to_pair_data():
    # TODO: should this and the following be placed here?

    # Use a class for the data structure we are creating?
    print("Retrieving all necessary pair contracts and data...")
    # print(f"Token names: {bot_config.token_names}")
    dex_to_pair_data = dict()
    dex_to_pair_data["pair_data"] = {}
    for dex_name in bot_config.dex_names:
        pair, reversed_order = get_pair_info(dex_name)
        dex_to_pair_data["pair_data"][dex_name] = [
            pair,
            reversed_order,
        ]
    dex_to_pair_data["token_data"] = {}
    token_names = bot_config.token_names
    for token_name, token_address in zip(token_names, get_token_addresses(token_names)):
        token = interface.IERC20(token_address)
        print(token.name())
        decimals = token.decimals()
        name = token.name()
        dex_to_pair_data["token_data"][token_name] = [
            token,
            name,
            decimals,
        ]

    print("Retrieved")
    return dex_to_pair_data


def get_pair_info(_dex_name, _version="V2"):
    account = get_account()
    token_addresses = get_token_addresses(bot_config.token_names)

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
