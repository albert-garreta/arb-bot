from tkinter import E
import time, warnings
from scripts.deploy import get_BotSmartContract
from scripts.utils import (
    get_account,
    auto_reboot,
    get_latest_block_number,
    log,
    get_address_list_from_contract_list,
    convert_from_wei,
    full_log,
)
from scripts.data_structures.data_organizer import DataOrganizer
from scripts.multi_armed_bandit import MultiArmedBandit
import bot_config
import warnings


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
        # self.update_multi_armed_bandit() deactivate MAB
        self.variable_pair_data.set_summary_message()
        print(self.variable_pair_data.summary_message)
        if self.variable_pair_data.passes_requirements():
            return self.engage_in_arbitrage()

    """----------------------------------------------------------------
    Arbitrage operation methods
    ----------------------------------------------------------------"""

    def engage_in_arbitrage(self):
        # If in passive_mode, skips the function returning None
        # Otherwise it logs information down and then attempts
        # to perform an arbitrage operation.
        # Returns the brownie transaction object if successful,
        # otherwise it logs down information about the failure and
        # raises an Exception
        if bot_config.passive_mode:
            return None
        self.log_pre_action()
        try:
            tx = self.flashloan_and_swap()
            self.handle_successful_arb()
        except Exception as e:
            self.handle_failed_arb(e)

    def flashloan_and_swap(self):
        self.get_flashloan_args()
        tx = self.bot_smartcontract.requestFlashLoanAndAct(
            self.flashloan_args,
            {
                "from": get_account(),
              # "gas_price": "10 gwei",
            },
        )
        tx.wait(1)
        return tx

    def get_flashloan_args(self):
        """
        Here we construct an instance of the struct `ArbData` from
        `BotSmartContract``, which is the argument taken by the
        function `requestFlashLoanAndAct``. The struct consists in:

        tokenAddresses; factoryAddresses; routerAddresses;
        amountTkn1ToBorrow; buyDexIndex; sellDexIndex;
        orderReversions; buyDexFee;

        NOTE: Up to this point, we were working with wei regardless of the
        native decimal count of the tokens. We convert all necessary
        amounts into their native decimal count, since these arguments
        will be handled by UniswapV2's contracts.
        """
        data = self.variable_pair_data  # for readibility
        self.flashloan_args = (
            data.token_addresses,
            get_address_list_from_contract_list(data.dex_factories),
            get_address_list_from_contract_list(data.dex_routers),
            convert_from_wei(data.optimal_borrow_amount, data.decimals[1]),
            data.buy_dex_index,
            data.sell_dex_index,
            data.reversed_orders,
            (1000 - 10 * data.dex_fees[data.buy_dex_index]),  # buyDexFee
        )
        return self.flashloan_args

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
        # Deactivated MAB
        # self.multi_armed_bandit.update_choice_probs()
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

    def log_pre_action(self):
        msg = f"\n\n\nNEW ACTION: Requesting flashloan and swapping...\n"
        full_log(msg, bot_config.log_actions_path)

    def handle_successful_arb(self, msg=""):
        msg = f"Success! Flashloan and swaps completed\n" + msg
        full_log(msg, bot_config.log_actions_path)

    def log_failure(self, _exception):
        msg = f"Operation failed\nThe exception is\n{_exception}\n"
        full_log(msg, bot_config.log_actions_path)

    def handle_failed_arb(self, _exception):
        # TODO: clean this function up

        # We first log the summary message with the data collected before the
        # failure.
        self.variable_pair_data.set_summary_message(
            addendum=f"Info before the failure\n{self.flashloan_args}\n"
        )
        full_log(self.variable_pair_data.summary_message, bot_config.log_actions_path)

        # Next we update the varables_pair_data. After this call the object will
        # contain all the data after the failure
        self.variable_pair_data.update_to_best_possible()
        # Now we log a new summary message with the new data
        self.variable_pair_data.set_summary_message(
            addendum=f"Info after failure\n{self.flashloan_args}\n"
        )
        full_log(self.variable_pair_data.summary_message, bot_config.log_actions_path)
        self.log_failure(_exception)
        raise _exception


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
