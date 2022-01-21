from scripts.data import get_pair_info
from scripts.prices import get_pair_price_via_pool_reserves
import bot_config


def search_arb_oportunity(_pair_dex_data, _verbose=False):
    prices = []
    for dex_name in bot_config.dex_names:
        usd_to_eth_price = get_pair_price_via_pool_reserves(_pair_dex_data, dex_name)
        # switch to normal
        eth_price = 1 / usd_to_eth_price
        prices.append(eth_price)
        if _verbose:
            print(f"The eth price via pool reserves in {dex_name} is {eth_price}")

    max_delta = max(prices) - min(prices)
    profit_ratio = 100 * max_delta / min(prices)
    if _verbose:
        print(f"Max delta: {max_delta}")
        print(f"Profit %: {profit_ratio}\n")
    return profit_ratio


def main():
    search_arb_oportunity(bot_config.token_names, bot_config.dexes, True)
