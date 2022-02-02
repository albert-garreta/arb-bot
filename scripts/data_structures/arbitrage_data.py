from socket import MSG_EOR
import bot_config
from scripts.data_structures.general_data import GeneralData
from scripts.data_structures.dotdict import dotdict
from scripts.prices import get_net_profit_v3, get_dex_amount_in
from scripts.utils import (
    log,
    mult_list_by_scalar,
    fix_parameters_of_function,
    reverse_scalar_fun,
    get_latest_block_number,
)
import numpy as np
from scipy.optimize import minimize_scalar
from brownie import chain


class ArbitrageData(GeneralData):
    # TODO: consider changing these class names
    def __init__(self):
        super().__init__()
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
            bounds=(0, self.max_value_of_flashloan),
            method="bounded",
        )
        return res.x

    def update_opt_borrow_amt_and_net_profit_and_amt_to_return(
        self, optimal_borrow_amount, net_profit
    ):
        self.optimal_borrow_amount = optimal_borrow_amount
        self.net_profit = net_profit
        self.amount_to_return = get_dex_amount_in(
            optimal_borrow_amount, self.get_buy_dex_data()
        )

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

    # def get_profit_ratio(self):
    #     return 100 * (self.net_profit / self.optimal_borrow_amount - 1)

    def passes_requirements(self):
        requirement = True
        # profit_ratio = self.get_profit_ratio()
        # requirement = profit_ratio > bot_config.min_profit_ratio
        requirement = requirement and self.net_profit > bot_config.min_net_profit
        requirement = requirement and self.optimal_borrow_amount > 0
        requirement = requirement or bot_config.force_actions
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
        self.update_opt_borrow_amt_and_net_profit_and_amt_to_return(
            borrow_amount, net_profit
        )

    def set_summary_message(self, addendum=""):
        # TODO: create separate class for logging
        price_buy_dex = self.get_dex_price(self.reserves_buying_dex)
        price_sell_dex = self.get_dex_price(self.reserves_selling_dex)
        msg = ""
        # Too expenive: msg += f"Block number: {get_latest_block_number()}\n"
        msg += f"Reserves buying dex: {mult_list_by_scalar(self.reserves_buying_dex,1e-18)}\n"
        msg += f"Reserves selling dex: {mult_list_by_scalar(self.reserves_selling_dex,1e-18)}\n"
        msg += f"Price buying dex: {price_buy_dex}\n"
        msg += f"Price selling dex: {price_sell_dex}\n"
        msg += f"Price ratio: {price_buy_dex/price_sell_dex}\n"
        msg += f"Buying dex index: {self.buy_dex_index}\n"
        msg += f"Net profit: {self.net_profit/1e18}\n"
        msg += f"Optimal borrow amount: {self.optimal_borrow_amount/1e18}\n"
        msg += addendum
        msg += "\n"
        self.summary_message = msg

    def print_summary(self):
        print(self.summary_message)

    def log_summary(self, path):
        log(self.summary_message, path)

    def print_and_log_summary(self, path):
        self.print_summary()
        self.log_summary(path)
