from tkinter import E
import time, warnings
from scripts.deploy import get_BotSmartContract
from scripts.utils import (
    get_account,
    auto_reboot,
    get_latest_block_number,
    log,
)
from scripts.data_structures.data_organizer import DataOrganizer
from scripts.multi_armed_bandit import MultiArmedBandit
import bot_config
import warnings
import telegram_send


def main():
    Bot().run()


class Bot(object):
    """This is the main class of the repository. Everything gets moving by executing its `run` method."""

    # TODO: Explain what an arbitrage operation exactly consists of using this repository's notation
    # (already partially implicitly explained in the data structures classes) and here in run_epoch

    def __init__(self):
        # Stores a deployed BotSmartContract
        self.bot_smartcontract = get_BotSmartContract()
        self.data_organizer = DataOrganizer()
        # This will be filled in when a LP has been chosen
        self.variable_pair_data = None
        num_bandits = len(self.data_organizer.list_index_pairs)
        self.multi_armed_bandit = MultiArmedBandit(num_bandits)
        self.num_epochs = 0

    # The auto_reboot wrapper will reboot this function in case it is
    # thrown by an error. This behavior can be disabled in `bot_config.py`
    @auto_reboot
    def run(self):
        # Periodically run epochs.
        block_number = get_latest_block_number()
        last_recorded_time = time.time()
        while True:
            if epoch_due(block_number):
                elapsed_time = time.time() - last_recorded_time
                last_recorded_time = time.time()
                print(f"Starting epoch after waiting for {elapsed_time}s")
                self.run_epoch()
            time.sleep(bot_config.time_between_epoch_due_checks)
            self.maintenance()

    def run_epoch(self):
        # - 1st we choose a token pair (token0, token1)
        # - 2nd (in `update_to_best_possible`) we choose which among 
        #       dex0 and dex1 should be the
        #       dex were we borrow token1, and which where we sell it;
        #       the former dex is referred to as the `buy_dex`, and the 
        #       latter as the sell_dex`.
        #       Several additional data is recorded at this stage
        # - 3rd Console printing
        # - 4th If the current setting passes the minimum requirements,
        #       the bot logs it and engages in an arbitrage operation
        self.choose_and_set_token_pair()
        self.variable_pair_data.update_to_best_possible()
        self.update_multi_armed_bandit()
        self.variable_pair_data.set_summary_message()
        self.variable_pair_data.print_summary()
        if self.variable_pair_data.passes_requirements():
            self.variable_pair_data.log_summary(bot_config.log_searches_path)
            return self.engage_in_arbitrage()

    """----------------------------------------------------------------
    Arbitrage operation methods
    ----------------------------------------------------------------"""

    # TODO: clean this part up

    def engage_in_arbitrage(self):
        if bot_config.passive_mode:
            return None
        self.log_pre_action()
        try:
            tx = self.flashloan_and_swap()
            tx.wait(1)
            # TODO: clean this tx logging and improve the way things are logged around here
            # print(tx.info())
            self.print_log_summary_with_balances_and_comment(tx.info())
            tx2 = self.retrieve_profits()
            tx2.wait(1)
            self.log_post_action(tx.info())
            return tx
        except Exception as e:
            self.handle_failure(e)

    def flashloan_and_swap(self):
        flashloan_args = self.get_flashloan_args()
        tx = self.bot_smartcontract.requestFlashLoanAndAct(
            flashloan_args,
            {
                "from": get_account(),
                "gas_price": bot_config.gas_strategy,
            },
        )
        tx.wait(1)
        return tx

    def get_flashloan_args(self):
        # Up to this point, we were working with wei regardless of the native decimal count of the tokens
        # TODO: clean this up
        self.flashloan_args = (
            self.variable_pair_data.token_addresses,
            [f.address for f in self.variable_pair_data.dex_factories],
            [r.address for r in self.variable_pair_data.dex_routers],
            self.variable_pair_data.optimal_borrow_amount
            / 10
            ** (
                18 - self.variable_pair_data.decimals[1]
            ),  # Important: we must pass amounts in the native decimal number of the tokens
            self.variable_pair_data.buy_dex_index,
            self.variable_pair_data.sell_dex_index,
            self.variable_pair_data.reversed_orders,
            (
                1000
                - 10
                * self.variable_pair_data.dex_fees[
                    self.variable_pair_data.buy_dex_index
                ]
            ),
        )
        return self.flashloan_args

    def retrieve_profits(self):
        return self.bot_smartcontract.sendAllFundsToOwner({"from": get_account()})

    """----------------------------------------------------------------
    Token Pair choice methods
    ----------------------------------------------------------------"""

    def choose_and_set_token_pair(self):
        # NOTE: with the current configuration, this is effectively just a ranfom choice.
        # See `bandit_exploration_probability` in `bot_config.py`

        self.choose_pair()
        # choices are betweein 1 to num_bandits+1. Hence we have to subtract 1
        choice_index = self.multi_armed_bandit.last_choice - 1
        token0_index, token1_index = self.get_token_name_pair_from_multi_armed_choice(
            choice_index
        )
        self.variable_pair_data = self.data_organizer.get_pair_data(
            token0_index, token1_index
        )

    def choose_pair(self):
        self.multi_armed_bandit.update_choice_probs()
        self.multi_armed_bandit.choose()

    def get_token_name_pair_from_multi_armed_choice(self, _choice):
        return self.data_organizer.list_index_pairs[_choice]

    def update_multi_armed_bandit(self):
        self.multi_armed_bandit.update_choice_weights(self.variable_pair_data)

    """----------------------------------------------------------------
    Maintenance methods
    ----------------------------------------------------------------"""

    def maintenance(self):
        self.num_epochs += 1
        if self.maintenance_due():
            print("Entering bot maintenance mode...")
            self.data_organizer.maintenance()
            self.multi_armed_bandit.maintenance()
            print("Maintenance done")
        else:
            pass

    def maintenance_due(self):
        return (self.num_epochs + 1) % bot_config.bot_maintenance_epoch_frequency == 0

    """----------------------------------------------------------------
    Logging methods
    ----------------------------------------------------------------"""
    
    # TODO: clean this part up
    
    def handle_failure(self, _exception):
        self.variable_pair_data.set_summary_message(
            addendum=f"Info before the failure\n{self.flashloan_args}\n"
        )
        self.variable_pair_data.print_and_log_summary(path=bot_config.log_actions_path)
        self.variable_pair_data.update_to_best_possible()
        self.variable_pair_data.set_summary_message(
            addendum=f"Info after failure\n{self.flashloan_args}\n"
        )
        self.variable_pair_data.print_and_log_summary(path=bot_config.log_actions_path)
        self.log_failure(_exception)
        raise _exception

    def log_pre_action(self):
        comment = f"\n\n\nNEW ACTION: Requesting flashloan and swapping...\n"
        print(comment)
        log(comment, bot_config.log_actions_path)

    def log_post_action(self, msg=""):
        msg = f"Success! Flashloan and swaps completed\n" + msg
        self.print_log_summary_with_balances_and_comment(msg)

    def log_failure(self, _exception, msg=""):
        msg = "Operation failed\n"
        msg += f"The exception is\n{_exception}\n" + msg
        telegram_send.send(messages=[msg])
        log(msg, bot_config.log_actions_path)

    def print_log_summary_with_balances_and_comment(self, comment=""):
        # TODO: create separate class for logging
        actor_pre_loan_balance = self.get_balances(self.bot_smartcontract.address)
        caller_pre_loan_balance = self.get_balances(get_account())
        msg = f"Actor balances: {actor_pre_loan_balance}\n"
        msg += f"Caller balances: {caller_pre_loan_balance}\n"
        msg += comment
        self.variable_pair_data.set_summary_message(addendum=msg)
        self.variable_pair_data.print_and_log_summary(path=bot_config.log_actions_path)


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
