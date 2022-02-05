from socket import MSG_EOR
import bot_config
from scripts.data_structures.static_data import dotdict, StaticPairData
from scripts.prices import get_net_profit_v3, get_dex_amount_in, get_dex_amount_out
from scripts.utils import (
    log,
    mult_list_by_scalar,
    fix_parameters_of_function,
    reverse_scalar_fun,
)
import numpy as np
from scipy.optimize import minimize_scalar
from brownie import chain
import telegram_send
from pycoingecko import CoinGeckoAPI

cg = CoinGeckoAPI()

class DataOrganizer(dotdict):
    def __init__(self):
        self.token_pair_to_pair_data = {}
        self.list_index_pairs = []
        num_tokens = len(bot_config.token_names)
        for index0 in range(num_tokens):
            for index1 in range(index0 + 1, num_tokens):
                self.set_up_state_data(index0, index1)

    def set_up_state_data(self, index0, index1):
        try:
            print(
                f"Setting up data controllers for the token pair {index0}_{index1}..."
            )
            str_pair = get_pair_to_str_form(index0, index1)
            self.token_pair_to_pair_data[str_pair] = StateData(index0, index1)
            self.list_index_pairs.append([index0, index1])
            print("Set up done\n")
        except Exception as e:
            print("Setting up failed. Ignoring pair.")
            print("The exception was:")
            print(e)
            print('\n')
#
    def get_pair_data(self, index0, index1):
        str_pair = get_pair_to_str_form(index0, index1)
        return self.token_pair_to_pair_data[str_pair]

    def maintenance(self):
        print('Updating min net profits...')
        for str_pair, state_data in self.token_pair_to_pair_data.items():
            print(str_pair)
            state_data.fill_in_min_net_profits()
            self.token_pair_to_pair_data[str_pair] =state_data
        print('Net profits updated')

def get_pair_to_str_form(index0, index1):
    return str(index0) + "_" + str(index1)


class StateData(StaticPairData):
    # TODO: consider changing these class names
    def __init__(self, index0, index1):
        super().__init__(index0, index1)
        self.num_dexes = 2
        self.buy_dex_index = None
        self.sell_dex_index = None
        self.reserves_buying_dex = None
        self.reserves_selling_dex = None
        self.fees_buy_dex = None
        self.fees_sell_dex = None
        self.slippage_buy_dex = None
        self.slippage_sell_dex = None
        self.optimal_borrow_amount = None
        self.amount_to_return = None
        self.net_profit = None
        self._profit_function = None

    def update_given_buy_dex(self, _buy_dex_index):
        self.buy_dex_index = _buy_dex_index
        sell_dex_index = self.get_sell_dex_index(_buy_dex_index)
        self.sell_dex_index = sell_dex_index
        self.fees_buy_dex = self.dex_fees[_buy_dex_index]
        self.fees_sell_dex = self.dex_fees[sell_dex_index]
        self.slippage_buy_dex = self.dex_slippages[_buy_dex_index]
        self.slippage_sell_dex = self.dex_slippages[sell_dex_index]
        self.reserves_buying_dex = self.reserves[_buy_dex_index]
        self.reserves_selling_dex = self.reserves[sell_dex_index]
        self.set_profit_function()

    def set_profit_function(self):
        f = fix_parameters_of_function(
            _fun=get_net_profit_v3,
            _args_1_tuple=(self,),
        )
        self._profit_function = f

    def profit_function(self, _borrow_amount):
        return self._profit_function(_borrow_amount)

    def get_sell_dex_index(self, _buy_dex_index):
        return (_buy_dex_index + 1) % 2

    def get_optimal_borrow_amount(self):

        res = minimize_scalar(
            reverse_scalar_fun(self._profit_function),
            bounds=bot_config.loan_bounds,
            method="bounded",
        )
        return res.x

    def update_optimal_amounts_net_profit_and_more(
        self, optimal_borrow_amount, net_profit
    ):
        # TODO: clean this up
        self.optimal_borrow_amount = optimal_borrow_amount
        self.net_profit = net_profit
        # If the optimal_borrow_amount is negative, we want to record a net_profit of 0.
        # Otherwise the multiplier is just 1 and we get the unaltered net_profit
        self.net_profit_relu = net_profit * (1 + np.sign(optimal_borrow_amount)) / 2
        self.amount_to_return = get_dex_amount_in(
            optimal_borrow_amount, self.get_buy_dex_data()
        )
        self.price_buy_dex = self.get_dex_price(self.reserves_buying_dex)
        self.price_sell_dex = self.get_dex_price(self.reserves_selling_dex)
        self.price_ratio = self.price_buy_dex / self.price_sell_dex
        self.reward = self.net_profit /(1e18*self.min_net_profit )

    def get_dex_data(self, _buying):
        if _buying:
            return self.get_buy_dex_data()
        else:
            return self.get_sell_dex_data()

    def get_buy_dex_data(self):
        buy_dex_data = dotdict()
        buy_dex_data.reserves_in = self.reserves_buying_dex[0]
        buy_dex_data.reserves_out = self.reserves_buying_dex[1]
        buy_dex_data.fee = self.fees_buy_dex
        buy_dex_data.slippage = self.slippage_buy_dex
        return buy_dex_data

    def get_sell_dex_data(self):
        sell_dex_data = dotdict()
        sell_dex_data.reserves_in = self.reserves_selling_dex[1]
        sell_dex_data.reserves_out = self.reserves_selling_dex[0]
        sell_dex_data.fee = self.fees_sell_dex
        sell_dex_data.slippage = self.slippage_sell_dex
        return sell_dex_data

    def passes_requirements(self):
        requirement = True

        # TODO: Is it 1e18 or 10**decimals[0]?
        requirement = (
            requirement
            and self.net_profit / 1e18 > self.min_net_profit
        )
        requirement = requirement and self.optimal_borrow_amount > 0
        requirement = requirement or bot_config.force_actions
        # print(self.net_profit / (10 ** self.decimals[0]),self.decimals[0], self.min_net_profit, self.optimal_borrow_amount)
        # requirement = requirement and (not bot_config.passive_mode)
        return requirement

    def get_dex_price(self, _reserves):
        return _reserves[0] / _reserves[1]

    def update_to_best_possible(self):
        """
        Check the two combinatios of buying/selling dexes and see with which one
        we get better net profits"""
        # NOTE: I think this is the most expensive call in an epoch without action.
        self.update_all_dexes_reserves()
        best_metrics = self.get_best_metrics()
        self.update_to_best_arb_data_from_best_metrics(best_metrics)

    def get_best_metrics(self):
        best_metrics = {
            "borrow_amount": -np.inf,
            "net_profit": -np.inf,
            "buy_dex_index": 0,
        }
        for buy_dex_index in range(self.num_dexes):
            self.update_given_buy_dex(buy_dex_index)
            best_metrics = self.update_best_metrics(buy_dex_index, best_metrics)
        return best_metrics

    def update_best_metrics(self, _buy_dex_index, _best_metrics):
        borrow_amt = self.get_optimal_borrow_amount()
        net_profit = self.profit_function(borrow_amt)
        if net_profit > _best_metrics["net_profit"]:
            _best_metrics["net_profit"] = net_profit
            _best_metrics["borrow_amount"] = borrow_amt
            _best_metrics["buy_dex_index"] = _buy_dex_index
        return _best_metrics

    def update_to_best_arb_data_from_best_metrics(self, _best_metrics):
        # TODO: this is inefficient because we already ran this method.
        # At least we are not reoptimizing the net_profit function
        buy_dex_index = _best_metrics["buy_dex_index"]
        net_profit = _best_metrics["net_profit"]
        borrow_amount = _best_metrics["borrow_amount"]
        self.update_given_buy_dex(buy_dex_index)
        self.update_optimal_amounts_net_profit_and_more(borrow_amount, net_profit)

    def set_summary_message(self, addendum=""):
        # TODO: create separate class for logging
        msg = f"{self.token_names}\n"
        # Too expenive: msg += f"Block number: {get_latest_block_number()}\n"
        msg += f"Reserves buying dex: {mult_list_by_scalar(self.reserves_buying_dex,1e-18)}\n"
        msg += f"Reserves selling dex: {mult_list_by_scalar(self.reserves_selling_dex,1e-18)}\n"
        msg += f"Price buying dex: {self.price_buy_dex}\n"
        msg += f"Price selling dex: {self.price_sell_dex}\n"
        msg += f"Price ratio: {self.price_ratio}\n"
        msg += f"Buying dex index: {self.buy_dex_index}\n"
        msg += f"Net profit: {self.net_profit_relu/1e18} ({round(self.net_profit/1e18,6)}) (Min: {round(self.min_net_profit,6)})\n"
        msg += f"Optimal borrow amount: {self.optimal_borrow_amount/1e18}\n"
        msg += addendum
        msg += "\n"
        self.summary_message = msg

    def print_summary(self):
        print(self.summary_message)

    def log_summary(self, path):
        msg = self.summary_message
        if bot_config.telegram_notifications:
            telegram_send.send(messages=[msg])
        log(msg, path)

    def print_and_log_summary(self, path):
        self.print_summary()
        self.log_summary(path)
