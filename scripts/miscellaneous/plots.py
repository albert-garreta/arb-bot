from distutils import file_util
import seaborn as sbn
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scripts.prices import (
    get_dex_ammount_out,
    get_optimal_amount_in,
    get_net_profit_functional,
    get_optimal_amounts,
    get_net_profit2_functional,
)
from scripts.data import get_all_dex_to_pair_data
import bot_config
import random

# TODO: Improve readability of this script

RESERVE00 = 31541731643070439008914621  # taken from spookyswap WFTM/USDC
RESERVE10 = 76802364798781000000000000  # taken from spookyswap WFTM/USDC
RESERVE01 = 8210664415695057284341437
RESERVE11 = int(1 * 19920334106416000000000000)


RESERVE00, RESERVE10 = (
    8_630_299_609_75356_62734_89277,
    20_171_672_196_59000_00000_00000,
)
RESERVE01, RESERVE11 = (36711476243152243255560989, 85201866459307000000000000)


RESERVE00, RESERVE10 = (8812813628410115267563602, 19738137454139000000000000)
RESERVE01, RESERVE11 = (38403585201566284827432565, 85967388690746000000000000)



RESERVE00, RESERVE10 = (1e24, 2e24)
RESERVE01, RESERVE11 = (1e24, 1e24)


#RESERVE00, RESERVE10 = (41759559903779263272976120, 86414868068791000000000000)
#RESERVE01, RESERVE11 = (9850776171633736222979217, 20382135814464000000000000)


# RESERVE00, RESERVE10 = (
#     8_630_299_609_75356_62734_89277,
#     20_171_672_196_59000_00000_00000,
# )
# RESERVE01, RESERVE11 = (36711476243152243255560989, 85201866459307000000000000)

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
        0.3,
        0.2,
        0.05,
        0.01,
        0.09,
    )
    max_value_of_flashloan = 20 * 1e21
    f = get_net_profit_functional(*args)

    for amount_in in amount_in_rndn:
        final_amount_out = f(amount_in * 1e21)
        print(final_amount_out / 1e18)
        # amounts_out.append(final_profit_ratio**2)
        amounts_out.append(final_amount_out / 1e18)
    opt = get_optimal_amount_in(*args, max_value_of_flashloan)
    print(f(19e21) / 1e18)
    print("Optimal amount", opt / 1e21, f(opt) / 1e18)
    sbn.scatterplot(x=amount_in_rndn, y=amounts_out)
    plt.show()


def plot_final_profits_2():
    # Observe how there is an optimal amount in!
    number_points = 10
    scale = 1
    amounts_in_rndn = [
        tuple(random.choices(range(0, 15, scale), k=2)) for _ in range(number_points)
    ]
    amounts_in_rndn = [ (x[0], 1) for x in amounts_in_rndn ]
    for _ in range(10):
        amounts_in_rndn += [(x[0], _) for x in amounts_in_rndn ]
    amounts_out = []
    args = (
        (RESERVE00, RESERVE10),
        (RESERVE01, RESERVE11),
        0.25,
        0.25,
        0.01,
        0.01,
        0.09,
        #1/2.13
        #RESERVE01 / RESERVE11
        #max([RESERVE00/ RESERVE10, RESERVE01/ RESERVE11])
        (0.5* (RESERVE00/ RESERVE10 + RESERVE01/ RESERVE11)),
    )
    max_value_of_flashloan = 20 * 1e21
    f = get_net_profit2_functional(*args)

    for x, y in amounts_in_rndn:
        final_amount_out = f(x * 1e21, y * 1e21)
        print(x, y, final_amount_out / 1e18)
        # amounts_out.append(final_profit_ratio**2)
        amounts_out.append(final_amount_out / 1e18)
    opt = get_optimal_amounts(*args)
    # print(f(19e21) / 1e18)
    print("Optimal amount", opt[0] / 1e18, opt[1] / 1e18, f(*opt) / 1e18)
    print(  (0.5* (RESERVE00/ RESERVE10 + RESERVE01/ RESERVE11)))
    print(f(10e18,20e18))
    print(f(10e21,10e21))
    print(f(10e21,21e21))
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(
        xs=[p[0] for p in amounts_in_rndn],
        ys=[p[1] for p in amounts_in_rndn],
        zs=amounts_out,
    )
    ax.set_xlabel("tkn0")
    ax.set_ylabel("tkn1")
    ax.set_zlabel("profit")
    
    plt.show()


def main():
    #plot_get_dex_amount_fun()
    plot_final_profits()
