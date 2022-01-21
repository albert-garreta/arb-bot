from brownie import network

# Number of blocks to wait between epochs. In fantom a block takes around 0.85s to
# be mined as of Jan 2022

debug_mode = False  # prevents executing the function act()

blocks_to_wait = 0
time_between_epoch_due_checks = 0.01
dex_names = ["spookyswap", "spiritswap"]
# TODO: change the way tokens are named
token_names = ["weth_address", "usdt_address"]
min_profit_to_act = 0.1

lending_pool_fee = 0.09  # This is GEIST's and AAVE's fee.

# The amount of token0 we expect to pay as fee for the flashloan
amount_for_fees = 10
# An extra amount of token0 that we will transfer just to have some extra margin
extra_cover = 2
# The amount of token0 that we will borrow with the flashloan.
# It's the amount x such that the `lending_pool_fee`` % of x is the `amount_for_fees`
amount_to_borrow = amount_for_fees * 100 / lending_pool_fee
