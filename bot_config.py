from web3 import Web3
import numpy as np
import sys, getopt


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

# Number of blocks to wait between epochs. In fantom a block takes around 0.85s to
# be mined as of Jan 2022
blocks_to_wait = 0
time_between_epoch_due_checks = 0.1
dex_names = ["spookyswap", "spiritswap"]
# TODO: change the way tokens are named
token_names = ["token0", "token1"]
dex_fees = [0.2, 0.3]
lending_pool_fee = 0.09  # Cream: 0.03. GEIST's and AAVE's: 0.09.

# NOTE: I am currently estimating slippages as the price % change
# if swapping $10k of value
approx_slippages = [0.04, 0.2]

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
min_final_amount_out = 2  # 2WFTM

# The max amount of token0 dedicated to paying fees.
# Determines max amount borrowable
# This max amount is splitted latter between token0 and token1 equally in value
amount_for_fees = 40_000 * 1e18

# An extra amount of token0 that we will transfer just to have some extra margin
extra_cover = 0.03 * 1e18


max_amount_in = amount_for_fees * 100 / lending_pool_fee

# Currently just a placeholder for quick debugging
from pycoingecko import CoinGeckoAPI

cg = CoinGeckoAPI()


def coingecko_price():
    coin = "fantom"
    return 1 / cg.get_price(ids=coin, vs_currencies="usd")[coin]["usd"]


# for arg, value in zip(arguments, values):
#     bot_config[arg] = value
