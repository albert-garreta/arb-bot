from tkinter import E
from brownie import chain
import time, warnings, sys
from scripts.deploy import get_actor
from scripts.utils import (
    get_account,
    get_wallet_balances,
    rebooter,
    get_latest_block_number,
    is_testing_mode,
)
from scripts.data_structures.state_data import StateData
import bot_config
import sys
import warnings
import sys


def main():
    Bot().run()


class Bot(object):
    def __init__(self):
        self.actor_smartcontract = get_actor()
        self.arb_data = StateData()
        self.testing = False

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
            if is_testing_mode():
                return self.act_test()
            else:
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

    def act_test(self):
        # Same as act but it halts if flashloand_and_swap fails
        # This allows to inspect the tx in brownie console
        if bot_config.passive_mode:
            return None
        self.log_pre_action()
        return self.flashloan_and_swap()

    def flashloan_and_swap(self):
        flashloan_args = self.get_flashloan_args()
        tx = self.actor_smartcontract.requestFlashLoanAndAct(
            flashloan_args,
            {
                "from": get_account(),
                "gas_price": bot_config.gas_strategy,
                # "gas_limit": bot_config.gas_limit,
            },
        )
        tx.wait(1)
        return tx

    def get_flashloan_args(self):
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
        # TODO: clean this up
        print(flashloan_args)
        print(self.actor_smartcontract.pairs(0))
        print(self.actor_smartcontract.pairs(1))
        print(get_wallet_balances(get_account(), self.arb_data.tokens))

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


def epoch_due(block_number):
    """
    Returns a boolean indicating whether block_number is the number of the most recent block mined
    Returns: bool
    """
    try:
        latest_block_num = get_latest_block_number()
        return latest_block_num - block_number >= bot_config.blocks_to_wait
    except:
        warnings.warn("Retrieving block number failed. Proceeding anyway")
        return True
