from web3 import Web3
from brownie.network.gas.strategies import ExponentialScalingStrategy
from brownie import network, config
import os

NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS = ["development", "ganache"]
LOCAL_BLOCKCHAIN_ENVIRONMENTS = NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS + [
    "mainnet-fork",
    "ftm-main-fork",
    "plygon-main-fork",
]
ETH_NETWORKS = ["mainnet", "mainnet-fork", "kovan"]
FTM_NETWORKS = ["ftm-main", "ftm-main-fork", "ftm-test"]
MATIC_NETWORKS = ["polygon-main", "polygon-main-fork"]
AVAX_NETWORKS = ["avax-main", "avax-main-fork"]
MAIN_NETWORKS = ["ftm-main", "mainnet", "polygon-main"]

passive_mode = False  # prevents making any blockchain transactions
auto_reboot = False  # the bot reboots automatically in case of an error
force_actions = False  # the bot engages in arbitrage regardless of the market conditions. Used for testing
telegram_notifications = True  # the bot sends revelations notifications to a telegram bot. Uses `telegram_send``

log_directory = f"./logs/{network.show_active()}/"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)
log_actions_path = log_directory + f"action_logs.txt"

# How likely the multi armed bandit is to choose a random pair, from 0 to 1
# Choosing 1 effectively disables the bandit functionality
bandit_exploration_probability = 1

# Max amount in token1 we are allowed to borrow
max_value_of_flashloan = 1e6 * 1e18

# Bounds for the amount of token1 loaned
loan_bounds = (0, max_value_of_flashloan)

# Min expected net profits in USD in order to execute an arbitrage operation
min_net_profits_in_usd = 1

# How often the bot gets into maintenance. Currently this involves only
# updating the CoinGecko prices of the tokens being tracked, and saving
# the multi armed bandit weights
bot_maintenance_epoch_frequency = 10 * 60 * 2  # every 10 minutes approx

# This is a handcrafted reserve scenario for token0=WFTM token1=USDC used during testing
forced_reserves = [
    [39658714960429940000000000, 75878131847931000000000000],
    [12025438053268697000000000, 23157867742710000000000000],
]

# Here we set different gas strategies depending on the network
if network.show_active() in FTM_NETWORKS:
    gas_strategy = ExponentialScalingStrategy(
        "700 gwei", "1300 gwei", time_duration=0.4
    )
elif network.show_active() in ETH_NETWORKS:
    gas_strategy = 50
elif network.show_active() in MATIC_NETWORKS:
    gas_strategy = "150 gwei"
elif network.show_active() in AVAX_NETWORKS:
    gas_strategy = "40 gwei"
else:
    raise Exception

# Overwrite `force_actions` and `passive_mode` when testing
if (
    network.show_active()
    in LOCAL_BLOCKCHAIN_ENVIRONMENTS + NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS
):
    force_actions = True
    passive_mode = False

# Do not change these. Instead, modify the browni-config.yaml file
token_names = config["networks"][network.show_active()]["token_names"]
network_info = config["networks"][network.show_active()]
dexes_info = network_info["dexes"]
dex_names = dexes_info["names"]
dex_fees = [dexes_info[name]["fee"] for name in dex_names]
slippages = [dexes_info[name]["approx_slippage"] for name in dex_names]
approx_slippages = [dexes_info[name]["approx_slippage"] for name in dex_names]
decimals = []  # this is filled up during preprocessing

# Deprecated
blocks_to_wait = 0
time_between_epoch_due_checks = 0
