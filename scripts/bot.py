from tkinter import E
from brownie import chain
import time, warnings, sys, getopt
from scripts.deploy import get_actor_V2
from scripts.prices import (
    get_approx_price,
    get_dex_amount_out,
)
from scripts.utils import (
    get_account,
    get_token_names_and_addresses,
    get_wallet_balances,
    log,
    rebooter,
    mult_list_by_scalar,
)
from bot_config import (
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    MAIN_NETWORKS,
)
from scripts.data_structures.arbitrage_data import ArbitrageData
from scripts.actor_utils import prepare_actor
import bot_config
from web3 import Web3
import sys
from datetime import date, datetime
import warnings
from brownie.network.gas.strategies import GasNowStrategy, ExponentialScalingStrategy


def main():
    Bot().run()


class Bot(object):
    def __init__(self):
        self.actor_smartcontract = get_actor_V2()
        self.arb_data = ArbitrageData()
        # if not bot_config.passive_mode:
        #    self.prepare_actor_smartcontract()

    @rebooter
    def run(self):
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
                print(f"Starting epoch after waiting for {elapsed_time}s")
                self.run_epoch()
            time.sleep(bot_config.time_between_epoch_due_checks)

    def run_epoch(self):
        self.arb_data.update_to_best_possible()
        self.arb_data.set_summary_message()
        self.arb_data.print_summary()
        if self.arb_data.passes_requirements():
            self.arb_data.log_summary(bot_config.log_searches_path)
            return self.act()

    def act(self):
        if bot_config.passive_mode:
            return None
        self.log_pre_action()
        try:
            tx = self.flashloan_and_swap()
            self.log_post_action()
            return tx
        except Exception as e:
            self.log_failure(e)

    def flashloan_and_swap(self):
        flashloan_args = (
            self.arb_data.token_addresses,
            # TODO: clean this up
            self.arb_data.optimal_borrow_amount
            / 10
            ** (
                18 - self.arb_data.decimals[1]
            ),  # Important: we must pass amounts in the native decimal number of the tokens
            self.arb_data.amount_to_return / 10 ** (18 - self.arb_data.decimals[0]),
            self.arb_data.buy_dex_index,
            self.arb_data.sell_dex_index,
            self.arb_data.reversed_orders,
            (1000 - 10 * self.arb_data.dex_fees[self.arb_data.buy_dex_index]),
        )
        print(flashloan_args)
        print(self.actor_smartcontract.pairs(0))
        print(self.actor_smartcontract.pairs(1))
        print(get_wallet_balances(get_account(), self.arb_data.tokens))

        # if self.arb_data.reversed_orders[self.arb_data.buy_dex_index]:
        #     switch_order(self.arb_data.tokens)
        #     switch_order(self.arb_data.decimals)
        #     switch_order(self.arb_data.reserves[self.arb_data.buy_dex_index])
        #     switch_order(self.arb_data.token_addresses)

        tx = self.actor_smartcontract.requestFlashLoanAndAct(
            flashloan_args,
            {
                "from": get_account(),
                # "gas_price": bot_config.gas_strategy,
                # "gas_limit": bot_config.gas_limit,
            },
        )
        tx.wait(1)
        return tx

    def get_balances(self, address):
        return [
            tkn.balanceOf(address) / (10 ** decimal)
            for tkn, decimal in zip(self.arb_data.tokens, self.arb_data.decimals)
        ]

    def log_pre_action(self):
        comment = f"Requesting flashloan and swapping...\n"
        self.print_log_summary_with_balances_and_comment(comment)

    def log_post_action(self):
        comment = f"Success! Flashloan and swaps completed\n"
        self.print_log_summary_with_balances_and_comment(comment)

    def log_failure(self, _exception):
        msg = "Operation failed\n"
        msg += f"The exception is {_exception}\n\n"
        self.print_log_summary_with_balances_and_comment(msg)

    def print_log_summary_with_balances_and_comment(self, comment=""):
        # TODO: create separate class for logging
        actor_pre_loan_balance = self.get_balances(self.actor_smartcontract.address)
        caller_pre_loan_balance = self.get_balances(get_account())
        msg = f"Actor balances: {actor_pre_loan_balance}\n"
        msg += f"Caller balances: {caller_pre_loan_balance}\n"
        msg += comment
        self.arb_data.set_summary_message(addendum=msg)
        self.arb_data.print_and_log_summary(path=bot_config.log_actions_path)

    """
    def log_post_action(self):

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
    """


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
