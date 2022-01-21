from scripts.get_pair_price import (
    get_pair_price_via_pool_reserves,
)
from scripts.utils import get_token_addresses, FTM_NETWORKS, ETH_NETWORKS
from testconf import TOKEN_NAMES, DEXES
import pytest
from brownie import network


def test_get_pair_price_via_pool_reserves():
    token_addresses = get_token_addresses(TOKEN_NAMES)
    for dex_name in DEXES:
        usd_to_eth_price = get_pair_price_via_pool_reserves(
            *token_addresses, dex_name, _verbose=False
        )
        eth_price = 1 / usd_to_eth_price
        prices.append(eth_price)
        print(f"The eth price via pool reserves in {dex_name} is {eth_price}")
        if network.show_active() in ETH_NETWORKS:
            lower_bound, upper_bound = 2500, 5000
        elif network.show_active() in FTM_NETWORKS:
            lower_bound, upper_bound = 1, 5
        else:
            raise Exception("Network not supported")
        assert eth_price >= lower_bound and eth_price <= upper_bound
