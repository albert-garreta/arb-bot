from tkinter import E
from brownie import chain, config, network, interface
import time, warnings, sys, getopt
from scripts.deploy import deploy_actor
from scripts.data import get_all_dex_to_pair_data, get_all_dex_reserves
from scripts.prices.prices import (
    get_approx_price,
    get_dex_amount_out,
    get_arbitrage_data,
)
from scripts.utils import (
    get_account,
    get_token_names_and_addresses,
    print_and_log,
    rebooter,
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    MAIN_NETWORKS,
)
from scripts.actor_utils import prepare_actor
import bot_config
from web3 import Web3
import sys
from datetime import date, datetime
import warnings
from brownie.network.gas.strategies import GasNowStrategy, ExponentialScalingStrategy


def main():
    all_dex_to_pair_data, actor = preprocess()
    run_bot(all_dex_to_pair_data, actor)


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
            elapsed_time = time.time() - last_recorded_time
            last_recorded_time = time.time()
            print(f"Starting epoch after waiting `for {elapsed_time}s")
            run_epoch(all_dex_to_pair_data, actor)
        time.sleep(bot_config.time_between_epoch_due_checks)


def run_epoch(_all_dex_to_pair_data, _actor, _verbose=True):
    # NOTE: I think this is the most expensive call in an epoch without action.
    _all_reserves = get_all_dex_reserves(_all_dex_to_pair_data)
    arb_data = get_arbitrage_data(_all_reserves)
    passes_arb_requirements = pass_arbitrage_requirements(arb_data)
    if _verbose:
        arb_data.print_summary()
    if passes_arb_requirements:
        act(arb_data, _actor)


def pass_arbitrage_requirements(_arbitrage_data):
    net_profit = _arbitrage_data.net_profit
    profit_ratio = _arbitrage_data.get_profit_ratio()
    requirement = profit_ratio > bot_config.min_profit_ratio
    requirement = requirement and net_profit > bot_config.min_net_profit
    requirement = requirement or bot_config.force_actions
    requirement = requirement and (not bot_config.passive_mode)
    return requirement


def flashloan_and_swap(_arb_data, _actor):
    tx = _actor.requestFlashLoanAndAct(
        token_addresses,
        _arb_data.optimal_borrow_amt,
        _arb_data.buy_dex_index,
        _arb_data.sell_dex_index,
        {
            "from": get_account(),
            # "gas_price": bot_config.gas_strategy,
            # "gas_limit": bot_config.gas_limit,
        },
    )
    tx.wait(1)


def act(_arb_data, _actor, _verbose):
    print_and_log_action_info("pre_action", _verbose)
    try:
        flashloan_and_swap(_arb_data, _actor)
        print_and_log_action_info("post_action", _verbose)
    except Exception as e:
        process_failure(e)


def process_failure(_exception):
    msg = "Operation failed\n"
    msg += f"The exception is {_exception}\n\n"
    print_and_log(msg, bot_config.log_actions_path)


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


def preprocess(_verbose=True):
    actor = deploy_actor()
    all_dex_to_pair_data = get_all_dex_to_pair_data()

    # TODO: same code used in another function in this script.
    # Refactor code into a function?
    reserves_all_dexes = get_all_dex_reserves(all_dex_to_pair_data)
    if not bot_config.passive_mode:
        actor = prepare_actor(all_dex_to_pair_data, reserves_all_dexes, actor)
    else:
        actor = None
    return all_dex_to_pair_data, actor


def print_and_log_action_info(stage, _verbose):
    if _verbose:
        pass

    token0 = _arb_data.token0
    token1 = _arb_data.token1
    decimals0 = _arb_data.decimals0
    decimals1 = _arb_data.decimals1
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
    print(tkn0_to_buy, tkn1_to_sell)

    # TODO: when creating a data structure, make it so that decimals are returned in a list,
    # same with tokens, names, etc
    decimals = [decimals0, decimals1]
    amts = [tkn0_to_buy, tkn1_to_sell]
    tokens = [token0, token1]
    token_names, token_addresses = get_token_names_and_addresses()

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

    amts_to_borrow = [amt / (10 ** decimal) for amt, decimal in zip(amts, decimals)]
    fees_to_be_paid = [
        0.01 * bot_config.lending_pool_fee * amt / (10 ** decimal)
        for amt, decimal in zip(amts, decimals)
    ]
    total_to_be_returned = [
        fees_to_be_paid[i] + amts_to_borrow[i] for i in range(len(tokens))
    ]

    capacity_to_return = [
        actor_pre_loan_balance[0]
        + (
            get_dex_amount_out(
                _all_reserves[selling_dex_index][1],
                _all_reserves[selling_dex_index][0],
                amts_to_borrow[1] * 10 ** 18,
                bot_config.dex_fees[selling_dex_index],
            )
            / (10 ** 18)
        ),
        actor_pre_loan_balance[1]
        + (
            get_dex_amount_out(
                _all_reserves[buying_dex_index][0],
                _all_reserves[buying_dex_index][1],
                amts_to_borrow[0] * 10 ** 18,
                bot_config.dex_fees[buying_dex_index],
            )
            / (10 ** 18)
        ),
    ]
    return_deltas = [
        capacity_to_return[i] - total_to_be_returned[i] for i in range(len(tokens))
    ]
    msg = ""
    msg += "Requesting flash loan and swapping...\n"
    msg += f"Expected net value gain (in token0): {final_amount_out*(10**(18-decimals[0]))}\n"
    msg += f"Requesting to borrow the following ammounts: \n"
    msg += f"{amts_to_borrow}\n"
    msg += f"Fees to be paid: \n"
    msg += f"{fees_to_be_paid}\n"
    msg += f"Total to be returned: {total_to_be_returned}\n"
    msg += f"Capacity to return: {capacity_to_return}\n"
    msg += f"Return deltas: {return_deltas}\n"
    msg += f"Buying dex index: {buying_dex_index}\n"
    msg += f"Selling dex index: {selling_dex_index}\n"
    msg += f"Actor pre-loan balances: {actor_pre_loan_balance}\n"
    msg += f"Caller pre-loan balances: " f"{caller_pre_loan_balance}\n\n"
    if any([delta < 0 for delta in return_deltas]):
        error_msg = "Some token needs to be returned by an \
                     amount larger than what can be returned\n\n"
        msg += error_msg
        print_and_log(msg, bot_config.log_actions_path)
        # raise ValueError(msg)

    print_and_log(msg, bot_config.log_actions_path)

    msg = ""
    price_tkn0_to_tkn1 = get_approx_price(_all_reserves, buying=False)
    try:

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

        return True
    except:
        pass
