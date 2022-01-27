from web3 import Web3
import numpy as np
import sys, getopt
from brownie.network.gas.strategies import GasNowStrategy
from brownie import network
from scripts.utils import ETH_NETWORKS, FTM_NETWORKS
import os

# TODO: integrate with the config file?


class dotdict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


# bot_config = dotdict()


def process_line_commands():
    long_options = ["slippage=", "lending_fee="]
    short_options = "s:lf:"
    try:
        arguments, values = getopt.getopt(sys.argv[1:], short_options, long_options)
    except getopt.error as err:
        # Output error, and return with an error code
        print(str(err))
        sys.exit(2)


debug_mode = False  # prevents executing the function act()
rebooter_bot = False  # bot reboots automatically in case of an error
force_actions = False
if network.show_active() in FTM_NETWORKS:
    forced_tkn0_to_buy = 10e18
    forced_tkn1_to_sell = 20e18
elif network.show_active() in ETH_NETWORKS:
    forced_tkn0_to_buy = 0.001e18
    forced_tkn1_to_sell = 3e18
else:
    raise Exception

# Number of blocks to wait between epochs. In fantom a block takes around 0.85s to
# be mined as of Jan 2022
blocks_to_wait = 0
time_between_epoch_due_checks = 0.1

if network.show_active() in FTM_NETWORKS:
    dex_names = ["spookyswap", "spiritswap"]
elif network.show_active() in ETH_NETWORKS:
    dex_names = ["uniswap", "sushiswap"]
else:
    raise Exception

# TODO: change the way tokens are named
token_names = ["token0", "token1"]
dex_fees = [0.2, 0.3]
lending_pool_fee = 0.09  # Cream: 0.03. GEIST's and AAVE's: 0.09.

# NOTE: I am currently estimating slippages as the price % change
# if swapping $10k of value
#approx_slippages = [0.04, 0.2]
approx_slippages = [0.02, 0.1]

# min_spread = 0.1 + sum(dex_fees) + lending_pool_fee
# The following is a correct estimate of the min spread needed
# (0.1 is to account for slippage)
# the estimate commented above is incorrect because the 2nd swap
# incurs less fees because our capital is reduced through the fees of
# of the first swap. The lending pool fee also needs consideration
# In any case, this estimate in practice is almost the same as the
# one commented above.
# It is between 0.0001 and 0.0025 larger approx

# min_spread = 0.1 + 100 * (-1 + (1 + lending_pool_fee) / (np.prod(dex_fees)))
min_final_profit_ratio = 0.01

if network.show_active() in FTM_NETWORKS:
    min_final_amount_out = 2.5  # WFTM
elif network.show_active() in ETH_NETWORKS:
    min_final_amount_out = 0.001
else:
    raise Exception
# The max amount of token0 dedicated to paying fees.
# Determines max amount borrowable
# This max amount is splitted latter between token0 and token1 equally in value
amount_for_fees = 0.1  # 10
amount_for_fees *= 1e18
# An extra amount of token0 that we will transfer just to have some extra margin
extra_cover = 0.01  # 1
extra_cover *= 1e18

# TODO: call it max_value_of_flashloan?
max_amount_in = amount_for_fees * 100 / lending_pool_fee


directory = f"./logs/{network.show_active()}/"
if not os.path.exists(directory):
    os.makedirs(directory)
log_actions_path = directory + "_action_logs.txt"
log_searches_path = directory + "_searches_logs.txt"

# set to an integer to set a constant gas price
# NOTE: this is only used for the flashloan call of actor
# gas_strategy = GasNowStrategy("fast")
if network.show_active() in FTM_NETWORKS:
    gas_strategy = 1000  # GasNowStrategy("fast")
elif network.show_active() in ETH_NETWORKS:
    gas_strategy = 50
# this is based on a successful run of the flashloan call
gas_limit = 1_800_000


# Currently just a placeholder for quick debugging
from pycoingecko import CoinGeckoAPI

cg = CoinGeckoAPI()


def coingecko_price():
    coin = "fantom"
    return 1 / cg.get_price(ids=coin, vs_currencies="usd")[coin]["usd"]


# for arg, value in zip(arguments, values):
#     bot_config[arg] = value
