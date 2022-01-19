from scripts.get_pair_price import (
    get_pair_price_via_pool_reserves,
    get_pair_price_via_result_of_swapping,
)
from scripts.utils import get_token_addresses, TOKEN_NAMES


def test_get_pair_price_via_pool_reserves():
    token_addresses = get_token_addresses(TOKEN_NAMES)
    price = get_pair_price_via_pool_reserves(*token_addresses, _verbose=True)
    print(f"The eth price via pool reserves is {price}")
    assert price >= 2500 and price <= 4500


def test_get_pair_price_via_result_of_swapping():
    token_addresses = get_token_addresses(TOKEN_NAMES)
    price = get_pair_price_via_result_of_swapping(*token_addresses, _verbose=True)
    print(f"The eth price via pool reserves is {price}")
    assert price >= 2500 and price <= 4500
