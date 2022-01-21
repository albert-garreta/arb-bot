from scripts.prices import (
    get_pair_price_full,
)
from scripts.utils import get_token_addresses, FTM_NETWORKS, ETH_NETWORKS
import bot_config
import pytest
from brownie import network

TOKEN_NAMES = bot_config.token_names
DEXES = bot_config.dex_names


def test_get_pair_price_via_pool_reserves():
    for dex_name in DEXES:
        usd_to_eth_price = get_pair_price_full(dex_name, _verbose=True)
        eth_price = 1 / usd_to_eth_price
        print(f"The eth price via pool reserves in {dex_name} is {eth_price}")
        if network.show_active() in ETH_NETWORKS:
            lower_bound, upper_bound = 2500, 5000
        elif network.show_active() in FTM_NETWORKS:
            lower_bound, upper_bound = 1, 5
        else:
            raise Exception("Network not supported")
        assert eth_price >= lower_bound and eth_price <= upper_bound
