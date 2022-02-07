from tkinter import E
import time, warnings
from scripts.deploy import get_BotSmartContract
from scripts.utils import (
    get_account,
    get_wallet_balances,
    auto_reboot,
    get_latest_block_number,
    is_testing_mode,
    log,
)
from scripts.data_structures.data_organizer import DataOrganizer
from scripts.multi_armed_bandit import MultiArmedBandit
import bot_config
import warnings
import telegram_send


# TODO: clean this up

def main():
    Bot().run()


class Bot(object):
    def __init__(self):
        self.bot_smartcontract = get_BotSmartContract()
        self.data_organizer = DataOrganizer()
        self.state_data = None
        self.multi_armed_bandit = MultiArmedBandit(
            _num_bandits=len(self.data_organizer.list_index_pairs)
        )
        self.num_epochs = 0

    @auto_reboot
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
            self.maintenance()

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

    def run_epoch(self):
        self.choose_and_set_token_pair()
        self.state_data.update_to_best_possible()
        self.update_multi_armed_bandit()
        self.state_data.set_summary_message()
        self.state_data.print_summary()
        if self.state_data.passes_requirements():
            self.state_data.log_summary(bot_config.log_searches_path)
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
            tx.wait(1)
            # TODO: clean this tx logging up
            # print(tx.info())
            self.print_log_summary_with_balances_and_comment(tx.info())
            tx2 = self.retrieve_profits()
            tx2.wait(1)
            # TODO: improve the way things are logged around here
            self.log_post_action(tx.info())
            return tx
        except Exception as e:
            self.handle_failure(e)

    def handle_failure(self, _exception):
        self.state_data.set_summary_message(
            addendum=f"Info before the failure\n{self.flashloan_args}\n"
        )
        self.state_data.print_and_log_summary(path=bot_config.log_actions_path)
        self.state_data.update_to_best_possible()
        self.state_data.set_summary_message(
            addendum=f"Info after failure\n{self.flashloan_args}\n"
        )
        self.state_data.print_and_log_summary(path=bot_config.log_actions_path)
        self.log_failure(_exception)
        raise _exception

    def act_test(self):
        # Same as act but it halts if flashloand_and_swap fails
        # This allows to inspect the tx in brownie console
        if bot_config.passive_mode:
            return None
        self.log_pre_action()
        return self.flashloan_and_swap()

    def flashloan_and_swap(self):
        flashloan_args = self.get_flashloan_args()
        tx = self.bot_smartcontract.requestFlashLoanAndAct(
            flashloan_args,
            {
                "from": get_account(),
                # "gas_price": bot_config.gas_strategy,
                # "gas_limit": bot_config.gas_limit,
            },
        )
        tx.wait(1)
        return tx

    def get_flashloan_args(self):
        # Up to this point, we were working with wei regardless of the native decimal count of the tokens
        # TODO: clean this up
        self.flashloan_args = (
            self.state_data.token_addresses,
            [f.address for f in self.state_data.dex_factories],
            [r.address for r in self.state_data.dex_routers],
            self.state_data.optimal_borrow_amount
            / 10
            ** (
                18 - self.state_data.decimals[1]
            ),  # Important: we must pass amounts in the native decimal number of the tokens
            self.state_data.buy_dex_index,
            self.state_data.sell_dex_index,
            self.state_data.reversed_orders,
            (1000 - 10 * self.state_data.dex_fees[self.state_data.buy_dex_index]),
        )
        # TODO: clean this up
        print(get_wallet_balances(get_account(), self.state_data.tokens))
        return self.flashloan_args

    def retrieve_profits(self):
        return self.bot_smartcontract.sendAllFundsToOwner({"from": get_account()})

    def get_balances(self, address):
        return [
            tkn.balanceOf(address) / (10 ** decimal)
            for tkn, decimal in zip(self.state_data.tokens, self.state_data.decimals)
        ]

    def choose_and_set_token_pair(self):
        self.choose_pair()
        # choices are betweein 1 to num_bandits+1. Hence we have to subtract 1
        choice_index = self.multi_armed_bandit.last_choice - 1
        token0_index, token1_index = self.get_token_name_pair_from_multi_armed_choice(
            choice_index
        )
        self.state_data = self.data_organizer.get_pair_data(token0_index, token1_index)

    def choose_pair(self):
        self.multi_armed_bandit.update_choice_probs()
        self.multi_armed_bandit.choose()

    def get_token_name_pair_from_multi_armed_choice(self, _choice):
        return self.data_organizer.list_index_pairs[_choice]

    def update_multi_armed_bandit(self):
        # We subtract because the bandit tries to maximize reward, but we sant the price buy/sell ratio to be minimal
        # reward = - self.state_data.price_buy_dex / self.state_data.price_sell_dex
        reward = self.state_data.reward
        self.multi_armed_bandit.update_choice_weights(reward)

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
        self.state_data.set_summary_message(addendum=msg)
        self.state_data.print_and_log_summary(path=bot_config.log_actions_path)


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
