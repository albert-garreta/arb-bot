from distutils import file_util
import seaborn as sbn
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scripts.prices.prices import (
    get_dex_amount_out,
    get_optimal_amounts,
    get_optimal_amount_in_2,
    get_net_profit2_functional,
    get_net_profit_v3,
)
from scripts.data_structures.arbitrage_data import ArbitrageData
import bot_config
import random
from scripts.utils import fix_parameters_of_function, mult_list_by_scalar

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

# RESERVE00, RESERVE10 = (1e24, 2e24)
# RESERVE01, RESERVE11 = (1e24, 1e24)
# #
# #
# RESERVE00, RESERVE10 = (41759559903779263272976120, 86414868068791000000000000)
# RESERVE01, RESERVE11 = (9850776171633736222979217, 20382135814464000000000000)
#
#
# RESERVE00, RESERVE10 = (
#     8_630_299_609_75356_62734_89277,
#     20_171_672_196_59000_00000_00000,
# )
# RESERVE01, RESERVE11 = (36711476243152243255560989, 85201866459307000000000000)
RESERVE01, RESERVE11 = (9876383326981423223975222, 20475145224676000000000000)
RESERVE00, RESERVE10 = (42674423402917740499711141, 88918120395739000000000000)

RESERVE01, RESERVE11 = [41992995.7626512, 87488447.455042]
RESERVE00, RESERVE10 = [11541179.030419603, 24067739.750079002]

# RESERVE01, RESERVE11 = [42033065.39828595,  87383634.83551401]
# RESERVE00, RESERVE10 = [11536786.090149844, 24026265.452085003]


def plot_final_profits():
    # Observe how there is an optimal amount in!
    number_points = 100
    scale = 1
    amount_in_rndn = random.choices(range(-100, 100, scale), k=number_points)
    amounts_out = []
    arb_data = ArbitrageData()
    arb_data.update_given_buy_dex_and_reserves(
        _buy_dex_index=0,
        _reserves=[
            mult_list_by_scalar([RESERVE01, RESERVE11], 1e18),
            mult_list_by_scalar([RESERVE00, RESERVE10], 1e18),
        ],
    )

    f = fix_parameters_of_function(get_net_profit_v3, (arb_data,))

    for amount_in in amount_in_rndn:
        final_amount_out = f(amount_in * 1e21)
        print(final_amount_out / 1e18)
        # amounts_out.append(final_profit_ratio**2)
        amounts_out.append(final_amount_out / 1e18)
    opt, prof = arb_data.get_optimal_borrow_amount_and_net_profit()
    print(f(19e21) / 1e18)
    print(opt)
    print("Optimal amount", opt / 1e21, prof / 1e18)
    sbn.scatterplot(x=amount_in_rndn, y=amounts_out)
    plt.show()


def main():
    # plot_get_dex_amount_fun()
    plot_final_profits()
