from distutils import file_util
import seaborn as sbn
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scripts.prices import get_net_profit_v3
from scripts.data_structures.variable_pair_data import VariablePairData
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

RESERVE01, RESERVE11 = [42033065.39828595, 87383634.83551401]
RESERVE00, RESERVE10 = [11536786.090149844, 24026265.452085003]

RESERVE01, RESERVE11 = [39658714.96042994, 75878131.847931]
RESERVE00, RESERVE10 = [12025438.053268697, 23157867.74271]


RESERVE00, RESERVE10 = [1151821.397824686, 364090452.64579535]
RESERVE01, RESERVE11 = [258486.8937923908, 82755716.72664398]

# RESERVE01, RESERVE11 = [10749301.949475199, 21647267.204137005]
# RESERVE00, RESERVE10 = [41531458.45993912, 83620371.86791101]


# RESERVE00, RESERVE10 = [2746.6223452757727, 2742.3830625500564]
# RESERVE01, RESERVE11 = [95719120.08327186, 94784938.37744634]


# RESERVE01, RESERVE11 =[38781318.59228811, 80733540.513515]
# RESERVE00, RESERVE10 = [11380023.156515732, 23692960.259842]


def plot_final_profits():
    # Observe how there is an optimal amount in!
    number_points = 100
    scale = 1
    amount_in_rndn = random.choices(range(0, 100, scale), k=number_points)
    amounts_out = []
    arb_data = VariablePairData(0,1)
    arb_data.reserves = [
        mult_list_by_scalar([RESERVE00, RESERVE10], 1e18),
        mult_list_by_scalar([RESERVE01, RESERVE11], 1e18),
    ]
    arb_data.update_given_buy_dex(_buy_dex_index=1)

    f = fix_parameters_of_function(get_net_profit_v3, (arb_data,))

    for amount_in in amount_in_rndn:
        final_amount_out = f(amount_in * 1e21)
        print(amount_in, final_amount_out / 1e18)
        # amounts_out.append(final_profit_ratio**2)
        amounts_out.append(final_amount_out / 1e18)
    opt = arb_data.get_optimal_borrow_amount()
    prof = arb_data.profit_function(opt)
    print(f(19e21) / 1e18)
    print(opt)
    print("Optimal amount", opt / 1e21, prof / 1e18)

    buy_price = arb_data.get_dex_price(arb_data.reserves[0])
    sell_price = arb_data.get_dex_price(arb_data.reserves[1])
    ratio = buy_price / sell_price
    print(f"Price ratios {ratio}, {1/ratio}")
    #print(arb_data.profit_function(252.29617785267552 * 1e21)/1e18)
    #print(arb_data.profit_function(260.29617785267552 *1e21)/1e18)
    sbn.scatterplot(x=amount_in_rndn, y=amounts_out)
    plt.show()


def main():
    # plot_get_dex_amount_fun()
    plot_final_profits()
