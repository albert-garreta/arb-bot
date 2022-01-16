from brownie import chain
import time
import yaml


with open("./bot-config.yaml", "r") as f:
    bot_config = yaml.load(f, yaml.FullLoader)


def run_epoch():
    act = check_if_arbitrage_oportunity()
    if act:
        pass


def check_if_arbitrage_oportunity():
    pass


def run_bot():
    block_number = get_latest_block_number()
    epoch_start_time = time.time()

    while True:
        if epoch_due(block_number):
            print(f"Starting block after waiting for {time.time() - epoch_start_time}s")
            run_epoch()
            epoch_start_time = time.time()
        time.sleep(bot_config["time_between_epoch_due_checks"])


def epoch_due(block_number):
    """
    Returns a boolean indicating whether block_number is the number of the most recent block mined
    Returns: bool
    """
    return block_number == get_latest_block_number() - bot_config["blocks_to_wait"]


def get_latest_block_number():
    # Retrieve the latest block mined
    # https://eth-brownie.readthedocs.io/en/stable/core-chain.html#accessing-block-information
    latest_block = chain[-1]
    # Get its number
    latest_block_number = chain[-1]["number"]
    return latest_block_number


def main():
    run_bot()
