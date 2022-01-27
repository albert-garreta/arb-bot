from tkinter import E
from brownie import chain, config, network, interface
import time, warnings, sys, getopt
from scripts.deploy import deploy_actor
from scripts.data import get_all_dex_to_pair_data, get_all_dex_reserves
from scripts.prices import (
    get_approx_price,
    get_arbitrage_profit_info,
)
from scripts.utils import (
    deposit_main_token_into_wrapped_version,
    get_account,
    get_token_addresses,
    print_and_log,
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS,
)
from scripts.actor_utils import prepare_actor
import bot_config
from web3 import Web3
import sys
from datetime import date, datetime
import warnings
from brownie.network.gas.strategies import GasNowStrategy, ExponentialScalingStrategy


MAIN_NETWORKS = ["ftm-main", "mainnet"]


def preprocess(_verbose=True):
    if (
        network.show_active()
        in LOCAL_BLOCKCHAIN_ENVIRONMENTS + NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS
    ):
        deposit_main_token_into_wrapped_version(
            bot_config.amount_for_fees + bot_config.extra_cover
        )

    all_dex_to_pair_data = get_all_dex_to_pair_data()

    # TODO: same code used in another function in this script.
    # Refactor code into a function?
    reserves_all_dexes = get_all_dex_reserves(all_dex_to_pair_data)
    if not bot_config.debug_mode:
        actor = deploy_actor()
        actor = prepare_actor(all_dex_to_pair_data, reserves_all_dexes, actor)
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
            reserves_all_dexes = get_all_dex_reserves(all_dex_to_pair_data)

            run_epoch(all_dex_to_pair_data, reserves_all_dexes, actor)
        time.sleep(bot_config.time_between_epoch_due_checks)


def run_epoch(_all_dex_to_pair_data, _all_reserves, _actor):
    if (
        network.show_active()
        in LOCAL_BLOCKCHAIN_ENVIRONMENTS + NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS
        or bot_config.force_actions
    ):
        force_success = True
    else:
        force_success = False

    arb_info = look_for_arbitrage(_all_reserves, force_success)
    if arb_info and not bot_config.debug_mode:
        action_successful = act(_all_dex_to_pair_data, arb_info, _actor)
        if action_successful:
            _actor = prepare_actor(_all_dex_to_pair_data, _all_reserves, _actor)
        else:
            print("Flash loan failed!")
            process_failure(_all_dex_to_pair_data,_all_reserves,_actor)


def look_for_arbitrage(_reserves_all_dexes, _force_success=False):
    # The force_sucess argument is used for testing purposes
    (
        final_profit_ratio,
        optimal_amount_in,
        final_amount_out,
        buying_dex_index,
        selling_dex_index,
    ) = get_arbitrage_profit_info(
        _reserves_all_dexes,
        bot_config.dex_fees,
        bot_config.approx_slippages,
        bot_config.lending_pool_fee,
        _verbose=True,
    )
    if (
        final_profit_ratio > bot_config.min_final_profit_ratio
        and final_amount_out / 1e18 > bot_config.min_final_amount_out
    ) or _force_success:
        final_amount_out = round(final_amount_out / 1e18, 3)
        final_profit_ratio = round(final_profit_ratio, 3)
        print("ACT\n")

        msg = f"{datetime.now()} - ACT\n"
        msg += f"Reserves buying dex: {_reserves_all_dexes[buying_dex_index]}\n"
        msg += f"Reserves selling dex: {_reserves_all_dexes[selling_dex_index]}\n"
        msg += f"Profit ratio {final_profit_ratio}.\n"
        msg += f"Optimal amount in {optimal_amount_in/1e18}\n"
        msg += f"Gains (in token0) {final_amount_out}\n\n"

        print_and_log(msg, bot_config.log_searches_path)
        tkn0_to_buy = 0.5 * optimal_amount_in
        price_tkn1_to_tkn0 = get_approx_price(
            _reserves_all_dexes[buying_dex_index], buying=True
        )
        tkn1_to_sell = 0.5 * optimal_amount_in / price_tkn1_to_tkn0

        if _force_success:
            tkn0_to_buy = bot_config.forced_tkn0_to_buy
            tkn1_to_sell = bot_config.forced_tkn1_to_sell

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
    token0, name0, decimals0 = _all_dex_to_pair_data["token_data"][
        bot_config.token_names[0]
    ]
    token1, name1, decimals1 = _all_dex_to_pair_data["token_data"][
        bot_config.token_names[1]
    ]

    (
        final_profit_ratio,
        tkn0_to_buy,
        tkn1_to_sell,
        final_amount_out,
        buying_dex_index,
        selling_dex_index,
    ) = arb_info

    # fix decimals, right now all token denominations are in wei
    tkn0_to_buy /= 10 ** (18 - decimals0)
    tkn1_to_sell /= 10 ** (18 - decimals1)

    # TODO: when creating a data structure, make it so that decimals are returned in a list,
    # same with tokens, names, etc
    decimals = [decimals0, decimals1]
    amts = [tkn0_to_buy, tkn1_to_sell]
    tokens = [token0, token1]
    token_addresses = get_token_addresses(bot_config.token_names)

    account = get_account()

    # TODO: make this into a function
    actor_pre_loan_balance = [
        tkn.balanceOf(_actor.address) / (10 ** decimal)
        for tkn, decimal in zip(tokens, decimals)
    ]
    caller_pre_loan_balance = [
        tkn.balanceOf(account) / (10 ** decimal)
        for tkn, decimal in zip(tokens, decimals)
    ]

    msg = ""
    msg += "Requesting flash loan and swapping...\n"
    msg += f"Expected net value gain (in token0): {final_amount_out/(10**decimals0)}\n"
    msg += f"Requesting to borrow the following ammounts: \n"
    msg += f"{[amt/(10**decimal) for amt, decimal in zip(amts, decimals)]}\n"
    msg += f"Fees to be paid: \n"
    msg += f"{[0.01*bot_config.lending_pool_fee*amt/(10**decimal) for amt, decimal in zip(amts, decimals)]}\n"
    msg += f"Buying dex index: {buying_dex_index}\n"
    msg += f"Selling dex index: {selling_dex_index}\n"
    msg += f"Actor pre-loan balances: {actor_pre_loan_balance}\n"
    msg += f"Caller pre-loan balances: " f"{caller_pre_loan_balance}\n\n"

    print_and_log(msg, bot_config.log_actions_path)
    msg = ""
    try:
        # if True:
        tx = _actor.requestFlashLoanAndAct(
            token_addresses,
            [tkn0_to_buy, tkn1_to_sell],
            buying_dex_index,
            selling_dex_index,
            {
                "from": account,
                "gas_price": bot_config.gas_strategy,
                "gas_limit": bot_config.gas_limit,
            },
        )
        tx.wait(1)
        actor_post_loan_balance = [
            tkn.balanceOf(_actor.address) / (10 ** decimal)
            for tkn, decimal in zip(tokens, decimals)
        ]
        caller_post_loan_balance = [
            tkn.balanceOf(account) / (10 ** decimal)
            for tkn, decimal in zip(tokens, decimals)
        ]
        amounts_flashloaned = [
            _actor.amountsLoanReceived(idx) / 10 ** decimals[idx]
            for idx in range(len(tokens))
        ]
        final_net_profits = [
            (
                caller_post_loan_balance[idx]
                - caller_pre_loan_balance[idx]
                - actor_pre_loan_balance[idx]
            )
            / 10 ** decimals[idx]
            for idx in range(len(tokens))
        ]

        msg += "Success!"
        msg += f"Actor post-loan balances: {actor_post_loan_balance}\n"
        msg += f"Caller post-loan balances: " f"{caller_post_loan_balance}\n"
        msg += (
            f"Amount of loans received during the flash loan: "
            f"{amounts_flashloaned}\n"
        )
        msg += f"Final net profits: {final_net_profits}\n\n"
        # assert pre_loan_balance == initial_deposit
        print_and_log(msg, bot_config.log_actions_path)

        assert False
        return True
    except Exception as e:
        msg += "Operation failed\n"
        msg += f"The exception is {e}\n\n"
        print_and_log(msg, bot_config.log_actions_path)
        
        return False


def process_failure(_all_dex_to_pair_data, _all_reserves, _actor):
    # TODO: What else do we need to do here?
    prepare_actor(_all_dex_to_pair_data, _all_reserves, _actor)


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
