from web3 import Web3
import numpy as np
import sys, getopt
from brownie.network.gas.strategies import GasNowStrategy
from brownie import network, config
from scripts.utils import (
    ETH_NETWORKS,
    FTM_NETWORKS,
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS,
)
import os

# TODO: integrate with the config file?

passive_mode = True  # prevents making blockchain transactions
rebooter_bot = False  # bot reboots automatically in case of an error
force_actions = False

# names and decimals are filled furing preprocessing
token_names = []
decimals = []
network_info = config["networks"][network.show_active()]
dex_names = network_info["dexes"]["names"]
dex_fees = [network_info["dexes"][name]["fee"] for name in dex_names]  # [0.2, 0.3]
slippages = [
    network_info["dexes"][name]["slippage"] for name in dex_names
]  # [0.2, 0.3]
lending_pool_fee = 0.03  # Cream: 0.03. GEIST's and AAVE's: 0.09.
# NOTE: I am currently estimating slippages as the price % change
# if swapping $10k of value
approx_slippages = [
    network_info["dexes"][name]["approx_slippage"] for name in dex_names
]
# The max amount of token0 dedicated to paying fees.
# This max amount is splitted latter between token0 and token1 equally in value
amount_for_fees_tkn0 = 5
amount_for_fees_tkn1_in_tkn0 = amount_for_fees_tkn0 / 2
# Due to the way we operate, the token being sold does not incur any profits
# during the arbitrage. Hence we need to supply  extra amount of tkn1 in order to
# pay for the fees of borrowing tkn1. This is around 0.3% of the amount we borrow
# of token1. Heuristically I am approximating this as 50
amount_for_fees_tkn1_extra_in_tkn0 = 25 * 1e18
amount_for_fees = amount_for_fees_tkn0 + amount_for_fees_tkn1_in_tkn0
amount_for_fees *= 1e18
amount_for_fees_tkn0 *= 1e18
amount_for_fees_tkn1_in_tkn0 *= 1e18
# We transfer the following to actor: amount_for_fees * amt_for_fees_multiplier
# An extra amount of token0 that we keep un wftm
extra_cover = 1  # 1
extra_cover *= 1e18

weth_balance_actor_and_caller = 10 * 1e18

# Very important argument: max total value that we flashloan
# Multiply by 0.995 yo givr some wiggle room
max_value_of_flashloan = 0.995 * ((amount_for_fees) * 100 / lending_pool_fee)


min_profit_ratio = 0.01
if network.show_active() in FTM_NETWORKS:
    min_net_profit = 1e18* 1  # WFTM
elif network.show_active() in ETH_NETWORKS:
    min_net_profit = 1e18* 0.001
else:
    raise Exception

if network.show_active() in FTM_NETWORKS:
    forced_tkn0_to_buy = 1e18 * 3.5 * 100 / lending_pool_fee
    forced_tkn1_to_sell = 1e18 * 7.7 * 100 / lending_pool_fee
elif network.show_active() in ETH_NETWORKS:
    forced_tkn0_to_buy = 0.001e18
    forced_tkn1_to_sell = 3e18
else:
    raise Exception


# Number of blocks to wait between epochs. In fantom a block takes around 0.85s to
# be mined as of Jan 2022
blocks_to_wait = 0
time_between_epoch_due_checks = 0.1

directory = f"./logs/{network.show_active()}/"
if not os.path.exists(directory):
    os.makedirs(directory)
log_actions_path = directory + "_action_logs.txt"
log_searches_path = directory + "_searches_logs.txt"

# set to an integer to set a constant gas price
# NOTE: this is only used for the flashloan call of actor
# gas_strategy = GasNowStrategy("fast")
if network.show_active() in FTM_NETWORKS:
    gas_strategy = "1000 gwei"  # GasNowStrategy("fast")
elif network.show_active() in ETH_NETWORKS:
    gas_strategy = 50
# this is based on a successful run of the flashloan call
gas_limit = 1_800_000


forced_reserves = [
    (8812813628410115267563602, 19738137454139000000000000),
    (38403585201566284827432565, 85967388690746000000000000),
]

if (
    network.show_active()
    in LOCAL_BLOCKCHAIN_ENVIRONMENTS + NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS
):
    force_actions = True
    passive_mode = False
