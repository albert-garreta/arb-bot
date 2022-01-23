from brownie import network

debug_mode = True  # prevents executing the function act()

# Number of blocks to wait between epochs. In fantom a block takes around 0.85s to
# be mined as of Jan 2022
blocks_to_wait = 0
time_between_epoch_due_checks = 0.001
dex_names = ["spookyswap", "spiritswap"]
dex_fees = [0.2, 0.3] 
# TODO: change the way tokens are named
token_names = ["token0", "token1"]
lending_pool_fee = 0.09  # Cream: 0.03. GEIST's and AAVE's: 0.09.

# The amount of token0 we expect to pay as fee for the flashloan
amount_for_fees = 10
# An extra amount of token0 that we will transfer just to have some extra margin
extra_cover = 0.1
# The amount of token0 that we will borrow with the flashloan.
# It's the amount x such that the `lending_pool_fee`` % of x is the `amount_for_fees`
amount_to_borrow = amount_for_fees * 100 / lending_pool_fee
