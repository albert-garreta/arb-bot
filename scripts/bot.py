from brownie import chain, config, network
import time
from scripts.deploy import deploy_actor
from scripts.data import get_all_dex_to_pair_data
from scripts.search_arb_oportunity import search_arb_oportunity
from scripts.utils import deposit_eth_into_weth, get_account
import bot_config
from web3 import Web3
import sys

MAIN_NETWORKS = ["ftm-main", "mainnet"]


class Logger(object):
    def __init__(self):
        pass


def prepare_actor(_all_dex_to_pair_data, _actor):
    print("Preparing actor for a future flashloan...")
    account = get_account()
    # Preliminary steps to the flashloan request and actions which can be done beforehand

    # TODO: we don't neewd to loop here. We just want the token0 data, which is
    # invariant of the dex. The only thing that dependes on the dex is `pair`
    # and `reversed_order`
    print(_all_dex_to_pair_data["token_data"].keys())
    token0, name0, decimals0 = _all_dex_to_pair_data["token_data"][
        bot_config.token_names[0]
    ]
    amount_token0_to_actor = bot_config.amount_for_fees + bot_config.extra_cover
    amount_token0_to_actor *= 10 ** decimals0

    token0s_aldready_in_actor = token0.balanceOf(_actor.address, {"from": account})
    amount_token0_to_actor = max(amount_token0_to_actor - token0s_aldready_in_actor, 0)

    if amount_token0_to_actor > 0:
        if bot_config.token_names[0] == "weth_address":
            deposit_eth_into_weth(amount_token0_to_actor)

        # !! transferFrom and approve since we are transfering from an external account (ours)
        print(
            f"Approving {amount_token0_to_actor} of {name0} for transfering to actor..."
        )
        tx = token0.approve(
            _actor.address, amount_token0_to_actor + 10000, {"from": account}
        )
        tx.wait(1)
        print("Approved")

        # !!! Is it dangerous to make the transfer now? (grieffing attack?)

        print(f"Transferring {name0} to Actor...")
        # !!! Careful: this needs to be called by actor, not me
        tx = token0.transferFrom(
            account.address,
            _actor.address,
            amount_token0_to_actor,
            {"from": _actor.address},
        )
        tx.wait(1)
        print("Transfer done")
    else:
        # TODO: Why? did this happen?
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
            {"from": account},
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
        prepare_actor()


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

    # TODO: does not actually step when ran with `brownie run``
    if (
        config["networks"][network.show_active()] in MAIN_NETWORKS
        and not bot_config.debug_mode
    ):
        confirm = sys.stin(
            "Are you sure you want to run the bot in a mainnet in non-debug_mode? (y/n)"
        )
        if confirm == "n":
            raise Exception  # TODO: Learn what is an excpetion, error, etc

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
