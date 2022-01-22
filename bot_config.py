from brownie import network

# Number of blocks to wait between epochs. In fantom a block takes around 0.85s to
# be mined as of Jan 2022

debug_mode = True  # prevents executing the function act()

blocks_to_wait = 0
time_between_epoch_due_checks = 0.01
dex_names = ["spookyswap", "spiritswap"]
# dex_fees = [0.2, 0.3]
dex_fees = [0.2, 0.04]  # spooky and curve
# dex_names = ["spiritswap", "spookyswap"]
# TODO: change the way tokens are named
token_names = ["weth_address", "usdt_address"]
lending_pool_fee = 0.03  # Cream: 0.03. GEIST's and AAVE's: 0.09.

# The amount of token0 we expect to pay as fee for the flashloan
amount_for_fees = 10
# An extra amount of token0 that we will transfer just to have some extra margin
extra_cover = 2
# The amount of token0 that we will borrow with the flashloan.
# It's the amount x such that the `lending_pool_fee`` % of x is the `amount_for_fees`
amount_to_borrow = amount_for_fees * 100 / lending_pool_fee
