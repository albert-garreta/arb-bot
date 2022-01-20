from logging import raiseExceptions
from scripts.get_pair_price import (
    get_pair_price_via_pool_reserves,
    get_pair_price_via_result_of_swapping,
)
from scripts.utils import ETH_NETWORKS, get_token_addresses, FTM_NETWORKS, ETH_NETWORKS
from testconf import TOKEN_NAMES
import pytest
from brownie import network


def test_get_pair_price_via_pool_reserves():
    token_addresses = get_token_addresses(TOKEN_NAMES)
    price = get_pair_price_via_pool_reserves(*token_addresses, _verbose=True)
    print(f"The eth price via pool reserves is {price}")
    if network.show_active() in ETH_NETWORKS:
        lower_bound, upper_bound = 2500, 500
    elif network.show_active() in FTM_NETWORKS:
        lower_bound, upper_bound = 1, 5
    else:
        raiseExceptions("Network not supported")
    assert price >= lower_bound and price <= upper_bound


def test_get_pair_price_via_result_of_swapping():
    if network.show_active() in FTM_NETWORKS:
        pytest.skip()
    token_addresses = get_token_addresses(TOKEN_NAMES)
    price = get_pair_price_via_result_of_swapping(*token_addresses, _verbose=True)
    print(f"The eth price via pool reserves is {price}")
    assert price >= 2500 and price <= 4500
