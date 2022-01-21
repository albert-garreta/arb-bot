from brownie import chain
import time
from scripts.search_arb_oportunity import (
    search_arb_oportunity,
    get_all_dex_to_pair_data,
)
import bot_config


class Logger(object):
    def __init__(self):
        pass


def run_epoch(_all_dex_to_pair_data):
    act = check_if_arbitrage_oportunity(_all_dex_to_pair_data)
    if act:
        pass


def check_if_arbitrage_oportunity(_all_dex_to_pair_data):
    profit = search_arb_oportunity(_all_dex_to_pair_data, _verbose=True)
    if profit > bot_config.min_profit_to_act:
        print("ACT\n")
        return True
    else:
        return False


def run_bot():
    """
    The bot runs an epoch every time bot_config["time_between_epoch_due_checks"] are mined.
    This is checked by epoch_due()
    """
    block_number = get_latest_block_number()
    last_recorded_time = time.time()
    all_dex_to_pair_data = get_all_dex_to_pair_data(
        bot_config.token_names, bot_config.dex_names
    )
    while True:
        if epoch_due(block_number):
            print(
                f"Starting epoch after waiting for {time.time() - last_recorded_time}s"
            )
            last_recorded_time = time.time()
            run_epoch(all_dex_to_pair_data)
        time.sleep(bot_config.time_between_epoch_due_checks)


def epoch_due(block_number):
    """
    Returns a boolean indicating whether block_number is the number of the most recent block mined
    Returns: bool
    """
    return get_latest_block_number() - block_number >= bot_config.blocks_to_wait


def get_latest_block_number():
    # Retrieve the latest block mined: chain[-1]
    # https://eth-brownie.readthedocs.io/en/stable/core-chain.html#accessing-block-information
    # Get its number
    latest_block_number = chain[-1]["number"]
    return latest_block_number


def main():
    run_bot()
