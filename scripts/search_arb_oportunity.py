from xmlrpc.server import SimpleXMLRPCRequestHandler
from scripts.data import get_pair_info
from scripts.prices import get_pair_price_via_pool_reserves
import bot_config
import numpy as np


def get_price_spread(_pair_dex_data, _verbose=False):
    """[summary]

    Args:
        _pair_dex_data ([type]): [description]
        _verbose (bool, optional): [description]. Defaults to False.

    Returns:
        (float, int, int): (max_price_spread, most expensive dex, cheapest dex)
    """
    prices = []
    for dex_name in bot_config.dex_names:
        price = get_pair_price_via_pool_reserves(_pair_dex_data, dex_name)
        # switch to normal
        prices.append(price)
        if _verbose:
            print(f"The token1/token0 price via pool reserves in {dex_name} is {price}")
            if bot_config.dex_names:
                # Currently just a placeholder for quick debugging
                print(f"The price in Coingecko is {bot_config.coingecko_price()}")
    max_delta = max(prices) - min(prices)
    max_index = np.argmax(prices)
    min_index = np.argmin(prices)
    max_price_spread = 100 * max_delta / min(prices)
    if _verbose:
        print(f"Highest price in {bot_config.dex_names[max_index]}")
        print(f"Lowest price in {bot_config.dex_names[min_index]}")
        print(f"Max delta: {max_delta}")
        print(f"Profit %: {max_price_spread}\n")
    return max_price_spread, max_index, min_index


def main():
    search_arb_oportunity(bot_config.token_names, bot_config.dexes, True)
