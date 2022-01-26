from distutils import file_util
import seaborn as sbn
import matplotlib.pyplot as plt

from scripts.prices import (
    get_dex_ammount_out,
    get_arbitrage_profit_info,
    get_approx_price,
    get_optimal_amount_in,
    get_net_profit_functional,
)
from scripts.data import get_all_dex_to_pair_data
import bot_config
import random


RESERVE00 = 31541731643070439008914621  # taken from spookyswap WFTM/USDC
RESERVE10 = 76802364798781000000000000  # taken from spookyswap WFTM/USDC
RESERVE01 = 8210664415695057284341437
RESERVE11 = int(1 * 19920334106416000000000000)


RESERVE01, RESERVE11 = (35640837096872919682071582, 84808247586144000000000000)
RESERVE00, RESERVE10 = (8543926433719342649572441, 20349583704137000000000000)


def plot_get_dex_amount_fun():
    number_points = 100
    scale = 10
    amount_in_rndn = random.choices(range(1, 1000, scale), k=number_points)
    amounts_out = []
    for amount_in in amount_in_rndn:
        amount_out = get_dex_ammount_out(
            RESERVE00,
            RESERVE11,
            amount_in * 1e21,
            _dex_fee=0.2,
            _slippage=0,
        )
        print(amount_in, amount_out)
        # price = (amount_in * 1e21)/ amount_out
        amounts_out.append(amount_out / 1e18)
    sbn.scatterplot(x=amount_in_rndn, y=amounts_out)
    plt.show()


def plot_final_profits():
    # Observe how there is an optimal amount in!
    number_points = 100
    scale = 1
    amount_in_rndn = random.choices(range(-100, 100, scale), k=number_points)
    amounts_out = []
    args = (
        (RESERVE00, RESERVE10),
        (RESERVE01, RESERVE11),
        0.2,
        0.3,
        0.01,
        0.05,
        0.09,
    )

    f = get_net_profit_functional(*args)

    for amount_in in amount_in_rndn:
        final_amount_out = f(amount_in * 1e21)

        # (
        #     final_profit_ratio,
        #     final_amount_out,
        #     max_index,
        #     min_index,
        # ) = get_arbitrage_profit_info(
        #     amount_in * 1e21,
        #     [0.2, 0.2],
        #     0.0,
        #     0.0,
        #     [
        #         (RESERVE00, RESERVE10),
        #         (RESERVE01, RESERVE11),
        #     ],
        # )
        print(final_amount_out / 1e18)
        # amounts_out.append(final_profit_ratio**2)
        amounts_out.append(final_amount_out / 1e18)
    opt = get_optimal_amount_in(*args)
    print(f(19e21) / 1e18)
    print("Optimal amount", opt / 1e21, f(opt) / 1e18)
    sbn.scatterplot(x=amount_in_rndn, y=amounts_out)
    plt.show()


def main():
    # plot_get_dex_amount_fun()
    plot_final_profits()
