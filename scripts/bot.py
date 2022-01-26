from tkinter import E
from brownie import chain, config, network
import time, warnings, sys, getopt
from scripts.deploy import deploy_actor
from scripts.data import get_all_dex_to_pair_data
from scripts.prices import (
    get_approx_price,
    get_arbitrage_profit_info,
    get_reserves,
    get_net_profit,
)
from scripts.utils import (
    deposit_main_token_into_wrapped_version,
    get_account,
    get_token_addresses,
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS,
)
from scripts.actor_utils import prepare_actor
import bot_config
from web3 import Web3
import sys
from datetime import date, datetime
import warnings


MAIN_NETWORKS = ["ftm-main", "mainnet"]


def preprocess():
    if (
        network.show_active()
        in LOCAL_BLOCKCHAIN_ENVIRONMENTS + NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS
    ):
        deposit_main_token_into_wrapped_version(
            bot_config.amount_for_fees + bot_config.extra_cover
        )

    all_dex_to_pair_data = get_all_dex_to_pair_data()
    all_dex_to_pair_data = get_all_dex_to_pair_data()
    if not bot_config.debug_mode:
        actor = deploy_actor()
        actor = prepare_actor(all_dex_to_pair_data, actor)
    else:
        actor = None
    return all_dex_to_pair_data, actor


def rebooter(function):
    def wrapped_fun(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            if bot_config.rebooter_bot:
                return wrapped_fun(*args, **kwargs)
            else:
                raise e

    return wrapped_fun


@rebooter
def run_bot(all_dex_to_pair_data, actor):
    """
    The bot runs an epoch every time bot_config["time_between_epoch_due_checks"] are mined.
    This is checked by epoch_due()
    """

    block_number = get_latest_block_number()
    last_recorded_time = time.time()

    while True:
        if epoch_due(block_number):
            print(
                f"Starting epoch after waiting for {time.time() - last_recorded_time}s"
            )
            last_recorded_time = time.time()

            # NOTE: this is the most expensive call in a run without action.
            reserves_all_dexes = [
                get_reserves(all_dex_to_pair_data, dex_index)
                for dex_index in range(len(bot_config.dex_names))
            ]
            run_epoch(reserves_all_dexes, reserves_all_dexes, actor)
        time.sleep(bot_config.time_between_epoch_due_checks)


def run_epoch(_all_dex_to_pair_data, _all_reserves, _actor):

    arb_info = look_for_arbitrage(_all_reserves)
    if arb_info and not bot_config.debug_mode:
        action_successful = act(_all_dex_to_pair_data, arb_info, _actor)
        if action_successful:
            _actor = prepare_actor(_all_dex_to_pair_data, _actor)
        else:
            print("Flash loan failed!")
            process_failure()


def look_for_arbitrage(reserves_all_dexes):
    (
        final_profit_ratio,
        optimal_amount_in,
        final_amount_out,
        buying_dex_index,
        selling_dex_index,
    ) = get_arbitrage_profit_info(
        reserves_all_dexes,
        bot_config.dex_fees,
        bot_config.approx_slippages,
        bot_config.lending_pool_fee,
        _verbose=True,
    )
    if (
        final_profit_ratio > bot_config.min_final_profit_ratio
        and final_amount_out / 1e18 > bot_config.min_final_amount_out
    ):
        final_amount_out = round(final_amount_out / 1e18, 3)
        final_profit_ratio = round(final_profit_ratio, 3)
        print("ACT\n")
        with open("./reports/actions.txt", "a") as f:
            f.write(
                f"{datetime.now()} - ACT\n"
                f"Reserves buying dex: {reserves_all_dexes[buying_dex_index]}\n"
                f"Reserves selling dex: {reserves_all_dexes[selling_dex_index]}\n"
                f"Profit ratio {final_profit_ratio}.\n"
                f"Optimal amount in {optimal_amount_in/1e18}\n"
                f"Gains (in token0) {final_amount_out}\n\n"
            )
        tkn0_to_buy = 0.5 * optimal_amount_in
        price_tkn1_to_tkn0 = get_approx_price(
            reserves_all_dexes[buying_dex_index], buying=True
        )
        tkn1_to_sell = 0.5 * optimal_amount_in / price_tkn1_to_tkn0
        return (  # TODO: create structure for this data
            final_profit_ratio,
            tkn0_to_buy,
            tkn1_to_sell,
            final_amount_out,
            buying_dex_index,
            selling_dex_index,
        )

    else:
        return None


def act(_all_dex_to_pair_data, arb_info, _actor, _verbose=True):
    (
        final_profit_ratio,
        amount_tkn0_to_buy,
        amount_tkn1_to_sell,
        buying_dex_index,
        selling_dex_index,
    ) = arb_info
    account = get_account()
    print("Requesting flash loan and swapping...")

    try:
        tx = _actor.requestFlashLoanAndAct(
            get_token_addresses(bot_config.token_names),
            [amount_tkn0_to_buy, amount_tkn1_to_sell],
            buying_dex_index,
            selling_dex_index,
            {"from": account},
        )
        tx.wait(1)
        print("Success!")
        return True
    except Exception as e:
        print("Operation failed")
        print(f"The exception is {e}")
        return False


def process_failure(_all_dex_to_pair_data, _actor):
    # TODO: What else do we need to do here?
    prepare_actor(_all_dex_to_pair_data, _actor)


def epoch_due(block_number):
    """
    Returns a boolean indicating whether block_number is the number of the most recent block mined
    Returns: bool
    """
    try:
        """FIXME: Currently sometimes I get the following error when retrievient blocks:
        File "./scripts/bot.py", line 156, in get_latest_block_number
            latest_block_number = chain[-1]["number"]
          File "brownie/network/state.py", line 240, in __getitem__
            block = web3.eth.get_block(block_number)
          File "web3/eth.py", line 589, in get_block
            return self._get_block(block_identifier, full_transactions)
          File "web3/module.py", line 57, in caller
            result = w3.manager.request_blocking(method_str,
          File "web3/manager.py", line 198, in request_blocking
            return self.formatted_response(response,
          File "web3/manager.py", line 177, in formatted_response
            apply_null_result_formatters(null_result_formatters, response, params)
          File "web3/manager.py", line 82, in apply_null_result_formatters
            formatted_resp = pipe(params, null_result_formatters)
          File "cytoolz/functoolz.pyx", line 667, in cytoolz.functoolz.pipe
          File "cytoolz/functoolz.pyx", line 642, in cytoolz.functoolz.c_pipe
          File "web3/_utils/method_formatters.py", line 630, in raise_block_not_found
            raise BlockNotFound(message)
        BlockNotFound: Block with id: '0x1baba25' not found."""
        latest_block_num = get_latest_block_number()
        return latest_block_num - block_number >= bot_config.blocks_to_wait
    except:
        warnings.warn("Retrieving block number failed. Proceeding anyway")
        return True


def get_latest_block_number():
    # Retrieve the latest block mined: chain[-1]
    # https://eth-brownie.readthedocs.io/en/stable/core-chain.html#accessing-block-information
    # Get its number
    try:
        latest_block_number = chain[-1]["number"]
        return latest_block_number
    except Exception as e:
        return e


def main():

    all_dex_to_pair_data, actor = preprocess()
    run_bot(all_dex_to_pair_data, actor)
