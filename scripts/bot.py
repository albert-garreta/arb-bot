from brownie import chain, config, network
import time
from scripts.deploy import deploy_actor
from scripts.data import get_all_dex_to_pair_data
from scripts.search_arb_oportunity import search_arb_oportunity
from scripts.utils import get_account
import bot_config
from web3 import Web3
import sys
from datetime import date, datetime
import pandas as pd

MAIN_NETWORKS = ["ftm-main", "mainnet"]


class Logger(object):
    def __init__(self, _pair_name, _dex_name):
        self.pair = _pair_name
        self.dex = _dex_name
        self.min_spread = 0.3
        self.spread_history = pd.DataFrame(columns=["date", "spread"])

    def log(self, _spread):
        pass


def prepare_actor(_all_dex_to_pair_data, _actor):
    """Preliminary steps to the flashloan request and actions which can be done beforehand"""

    print("Preparing actor for a future flashloan...")
    account = get_account()

    print(_all_dex_to_pair_data["token_data"].keys())
    token0, name0, decimals0 = _all_dex_to_pair_data["token_data"][
        bot_config.token_names[0]
    ]
    amount_token0_to_actor = bot_config.amount_for_fees + bot_config.extra_cover
    amount_token0_to_actor *= 10 ** decimals0

    token0s_aldready_in_actor = token0.balanceOf(_actor.address, {"from": account})
    amount_token0_to_actor = max(amount_token0_to_actor - token0s_aldready_in_actor, 0)

    if amount_token0_to_actor > 0:
        # !! transferFrom and approve since we are transfering from an external account (ours)
        print(
            f"Approving {amount_token0_to_actor} of "
            f"{name0} for transfering to actor..."
        )
        tx = token0.approve(
            _actor.address, amount_token0_to_actor + 10000, {"from": account}
        )
        tx.wait(1)
        print("Approved")

        # TODO: Is it dangerous to make the transfer now? (grieffing attack?)
        print(f"Transferring {name0} to Actor...")
        # TODO: Check if this can be done just with a transfer
        tx = token0.transferFrom(
            account.address,
            _actor.address,
            amount_token0_to_actor,
            {"from": _actor.address},
        )
        tx.wait(1)
        print("Transfer done")
    else:
        # TODO: Why did this happen?
        print("ATTENTION: actor holds too much tokens0s. How did this happen?")
    print("Preparation completed")
    return _actor


def act(_all_dex_to_pair_data, _actor, _verbose=True):

    token0, names0, decimals0 = _all_dex_to_pair_data["token_data"][
        bot_config.token_names[0]
    ]
    account = get_account()
    print("Requesting flash loan and swapping...")
    try:
        tx = _actor.requestFlashLoanAndAct(
            [token0.address],
            [Web3.toWei(bot_config.amount_to_borrow, "ether")],
            {
                "from": account,
            },
        )
        tx.wait(1)
        print("Success!")
        return True
    except Exception as e:
        print("Operation failed")
        print(f"The exception is {e}")
        return False


def run_epoch(_all_dex_to_pair_data, _actor):
    oportunty = check_if_arbitrage_oportunity(_all_dex_to_pair_data)
    if oportunty and not bot_config.debug_mode:
        success = act(_all_dex_to_pair_data, _actor)
        if success:
            _actor = prepare_actor(_all_dex_to_pair_data, _actor)


def check_if_arbitrage_oportunity(_all_dex_to_pair_data):
    profit = search_arb_oportunity(_all_dex_to_pair_data, _verbose=True)
    if profit > 0.01 + sum(bot_config.dex_fees) + bot_config.lending_pool_fee:
        print("ACT\n")
        slippage_tolerance = (
            profit - 0.01 + sum(bot_config.dex_fees) + bot_config.lending_pool_fee
        )
        with open("./reports/actions.txt", "a") as f:
            f.write(f"{datetime.now()}- Acting for non-taxed profit {profit}\n")
        return True
    else:
        return False


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


def rebooter(function):
    def wrapped_fun(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except:
            return wrapped_fun(*args, **kwargs)

    return wrapped_fun


@rebooter
def run_bot():
    """
    The bot runs an epoch every time bot_config["time_between_epoch_due_checks"] are mined.
    This is checked by epoch_due()
    """

    block_number = get_latest_block_number()
    last_recorded_time = time.time()
    all_dex_to_pair_data = get_all_dex_to_pair_data()
    if not bot_config.debug_mode:
        actor = deploy_actor()
        actor = prepare_actor(all_dex_to_pair_data, actor)
    else:
        actor = None

    while True:
        if epoch_due(block_number):
            print(
                f"Starting epoch after waiting for {time.time() - last_recorded_time}s"
            )
            last_recorded_time = time.time()
            run_epoch(all_dex_to_pair_data, actor)
        time.sleep(bot_config.time_between_epoch_due_checks)


def main():
    run_bot()
