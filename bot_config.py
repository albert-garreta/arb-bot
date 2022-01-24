from web3 import Web3
import numpy as np

debug_mode = True  # prevents executing the function act()

# Number of blocks to wait between epochs. In fantom a block takes around 0.85s to
# be mined as of Jan 2022
blocks_to_wait = 0
time_between_epoch_due_checks = 0.1
dex_names = ["spookyswap", "spiritswap"]
# TODO: change the way tokens are named
token_names = ["token0", "token1"]
dex_fees = [0.2, 0.04]
lending_pool_fee = 0.03  # Cream: 0.03. GEIST's and AAVE's: 0.09.
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
min_spread = 0.4

# The amount of token0 we expect to pay as fee for the flashloan
amount_for_fees = 10
# An extra amount of token0 that we will transfer just to have some extra margin
extra_cover = 0.1
# The amount of token0 that we will borrow with the flashloan.
# It's the amount x such that the `lending_pool_fee`` % of x is the `amount_for_fees`
amount_to_borrow = 0.01 * amount_for_fees * 100 / lending_pool_fee

amount_to_borrow_wei = Web3.toWei(amount_to_borrow, "ether")


# Currently just a placeholder for quick debugging
from pycoingecko import CoinGeckoAPI

cg = CoinGeckoAPI()


def coingecko_price():
    coin = "fantom"
    return 1 / cg.get_price(ids=coin, vs_currencies="usd")[coin]["usd"]
