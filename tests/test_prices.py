from re import A
from scripts.prices import (
    get_pair_price_full,
    get_dex_ammount_out,
    get_approx_price,
    get_pair_price_via_pool_reserves,
)
from scripts.utils import get_token_addresses, FTM_NETWORKS, ETH_NETWORKS
from scripts.data import get_all_dex_to_pair_data
import bot_config
import pytest
from brownie import network
import random
import seaborn as sbn
import matplotlib.pyplot as plt

TOKEN_NAMES = bot_config.token_names
DEXES = bot_config.dex_names
amount_in = bot_config.amount_to_borrow_token0_wei



def test_get_dex_amount_out_and_get_approx_price():
    def inner_fun(
        reserve0, reserve1, amount_in, fee=0.2, slippage=bot_config.approx_slippage
    ):
        amt_out = get_dex_ammount_out(
            reserve0, reserve1, amount_in, fee, bot_config.approx_slippage
        )
        # Price taking into account the changes of balances in the LP pool
        print(amount_in / amt_out)

        approx_price = get_approx_price(reserve0, reserve1)
        print(approx_price)
        print("")

    inner_fun(100e18, 100e18, 1e18)
    inner_fun(200e18, 100e18, 1e18)
    inner_fun(100e18, 200e18, 1e18)

    # Note how the price computed with amount_dex_out_becomes disproportionate
    # due to the imbalance created in the pool.
    inner_fun(100e18, 100e18, 1000000000e18)
    # The price approaxes the approx price plus fees when amount in tends to 0
    inner_fun(100e18, 100e18, 1)


def test_get_pair_price_via_pool_reserves():
    pair_dex_data = get_all_dex_to_pair_data()
    number_points = 10
    scale = 2
    amount_in_rndn = random.choices(range(1, 1000, scale), k=number_points)
    amounts_out = []
    for amount_in in amount_in_rndn:
        amount_out, reserve0, reserve1 = get_pair_price_via_pool_reserves(
            amount_in * 1e21, pair_dex_data, _dex_index=0, _verbose=True
        )
        out = amount_out / 1e18
        amounts_out.append(out)
    print("Reserves: ", reserve0, reserve1)
    sbn.scatterplot(x=amount_in_rndn, y=amount_out)
    plt.show()
