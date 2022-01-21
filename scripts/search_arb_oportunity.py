from scripts.get_pair_price import get_pair_price_via_pool_reserves, get_pair_info
import bot_config
from scripts.utils import get_token_addresses


def get_all_dex_to_pair_data(_token_names, _dexes):
    print("Retrieving all necessary pair contracts and data...")
    token_addresses = get_token_addresses(_token_names)
    dex_to_pair_data = dict()
    for dex_name in _dexes:
        pair_data = get_pair_info(*token_addresses, dex_name)
        dex_to_pair_data[dex_name] = pair_data
    print("Retrieved")
    return dex_to_pair_data


def search_arb_oportunity(_pair_dex_data, _verbose=False):
    prices = []
    for dex_name, pair_data in _pair_dex_data.items():
        usd_to_eth_price = get_pair_price_via_pool_reserves(*pair_data, _verbose=False)
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
