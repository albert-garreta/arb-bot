from socket import MSG_EOR
import bot_config
from scripts.data_structures.static_pair_data import dotdict, StaticPairData
from scripts.prices import get_net_profit_v3
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


class VariablePairData(StaticPairData):
    """
    # TODO: format docstrings correctly

    This inherits from StaticPairData (see its docstring first) and records all needed information that changes over time, such as
    the reserves in each LP, or the maximum possible net profit we can obtain from an arbitrage operation.

    Important considerations:
        - The two tokens and dexes are stored in a fixed order throughout the
        repository. Hence `token0` will always be the first token in `bot_config.token_names` and,
        similarly for token1 and the dexes.
        - Additionally, `token1` will *always* be the token being borrowed, while `token0` will *always* be the token
        being returned.
        - This means that dex0, dex1 can have different arbitrage roles depending on the state we are in: sometimes
        dex0 will be the buying dex, and dex1 the selling dex, while sometimes these reles will be reversed.
        This is stored in `self.buy_dex_index`.

    Attributes worth describing:
        - optimal_borrow_amount: the amount optimal amount of token1 to borrow in the current state.
        - net_profit: the net proft in token0 we would acquire if we were to perform an arbitrage operation in the current state
        - _profit_function: a scalar function whose input is an amount x of token1 to borrow, and whose output is the
        profit we would acquire if we were to perform an arbitrage operation with x token1 borrowed.

    """

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
        # Given an index of a dex, which is to act as the buying dex, update all attributes
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

    def get_sell_dex_index(self, _buy_dex_index):
        return (_buy_dex_index + 1) % 2

    def passes_requirements(self):
        # Returns a bool indicating whether or not the state of the pairs examined is
        # good enough to perform an arbitrage operation.
        requirement = True
        requirement = requirement and self.net_profit / 1e18 > self.min_net_profit
        requirement = requirement and self.optimal_borrow_amount > 0
        requirement = requirement or bot_config.force_actions
        return requirement

    """----------------------------------------------------------------
    Methods to compute `optimal_borrow_amount` and `net_profit`
    ----------------------------------------------------------------"""

    def set_profit_function(self):
        # Transforms `get_net_profit_v3`, the net profit function, into a scalar function
        # by fixing all but one of its parameters to be the attributes of this class
        # The resulting scalar function tells, given an amount x of token1 (in wei),
        # the net profit in tokn0 we would obtain if we were to borrow x token1 to do
        # an arbitrage operation.
        # This will allow to optimize the function f later in order to find the optimal
        # borrow amount.
        f = fix_parameters_of_function(
            _fun=get_net_profit_v3,
            _args_1_tuple=(self,),
        )
        self._profit_function = f

    def profit_function(self, _borrow_amount):
        return self._profit_function(_borrow_amount)

    def get_optimal_borrow_amount(self):
        # Returns the optimal amount of token1 (in wei) to borrow
        # according to the function `get_net_profit_v3`` and the attributes
        # of this class.

        # 1sr we reverse the function since we are going to use a minimization method
        # but we want to maximize f
        fun_to_minimize = reverse_scalar_fun(self._profit_function)
        # 2nd we use scipy's scalar function minimization method
        res = minimize_scalar(
            fun_to_minimize,
            bounds=bot_config.loan_bounds,
            method="bounded",
        )
        return res.x

    def update_optimal_amounts_net_profit_and_more(
        self, optimal_borrow_amount, net_profit
    ):
        self.optimal_borrow_amount = optimal_borrow_amount
        self.net_profit = net_profit

    """----------------------------------------------------------------
    Methods to decide which dex should be the buy dex and which should be the sell dex
    ----------------------------------------------------------------"""

    def update_to_best_possible(self):
        # For each possible choice of buy/sell dexes, it computes with which one we
        # would obtain more net profit if we were to perform arbitrage. Then it
        # updates the class' attributes in accordance to the choice that obtains
        # more profits.

        # 1st it updates the reserves of the two dexes
        self.update_all_dexes_reserves()
        # 2nd it obtains the best metrics, where best_metrics is a dictionary
        # containing `buy_dex_index`, `borrow_amount`, `net_profit``, with
        # the two latter values being the optimal borrow and profit we would
        # do if we were to use the dex given by `buy_dex_index` as the buy dex
        best_metrics = self.get_best_metrics()
        # 3rd it updates the attributes of the class accordingly
        self.update_to_best_arb_data_from_best_metrics(best_metrics)

    def get_best_metrics(self):
        best_metrics = {
            "borrow_amount": -np.inf,
            "net_profit": -np.inf,
            "buy_dex_index": 0,
        }
        for temporary_buy_dex_index in range(self.num_dexes):
            self.update_given_buy_dex(temporary_buy_dex_index)
            best_metrics = self.update_best_metrics(
                temporary_buy_dex_index, best_metrics
            )
        return best_metrics

    def update_best_metrics(self, _temporary_buy_dex_index, _best_metrics):
        borrow_amt = self.get_optimal_borrow_amount()
        net_profit = self.profit_function(borrow_amt)
        if net_profit > _best_metrics["net_profit"]:
            _best_metrics["net_profit"] = net_profit
            _best_metrics["borrow_amount"] = borrow_amt
            _best_metrics["buy_dex_index"] = _temporary_buy_dex_index
        return _best_metrics

    def update_to_best_arb_data_from_best_metrics(self, _best_metrics):
        # NOTE: this is lightly inefficient because we already ran this method.
        # However note we are not recomputing the optimal borrow amount so the
        # inneficiency is most likely negligible.
        buy_dex_index = _best_metrics["buy_dex_index"]
        net_profit = _best_metrics["net_profit"]
        borrow_amount = _best_metrics["borrow_amount"]
        self.update_given_buy_dex(buy_dex_index)
        self.update_optimal_amounts_net_profit_and_more(borrow_amount, net_profit)

    """----------------------------------------------------------------
    Logging methods
    ----------------------------------------------------------------"""

    # TODO: clean this part up

    def set_summary_message(self, addendum=""):
        msg = f"{self.token_names}\n"
        # Maybe too expenive: msg += f"Block number: {get_latest_block_number()}\n"
        msg += f"Reserves buying dex: {mult_list_by_scalar(self.reserves_buying_dex,1e-18)}\n"
        msg += f"Reserves selling dex: {mult_list_by_scalar(self.reserves_selling_dex,1e-18)}\n"
        msg += f"Price buying dex: {self.price_buy_dex}\n"
        msg += f"Price selling dex: {self.price_sell_dex}\n"
        msg += f"Price ratio: {self.price_ratio}\n"
        msg += f"Buying dex index: {self.buy_dex_index}\n"
        msg += f"Net profit: {round(self.net_profit/1e18,6)} (Min: {round(self.min_net_profit,6)})\n"
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

    """----------------------------------------------------------------
    Price utilities
    ----------------------------------------------------------------"""

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

    def get_dex_price(self, _reserves):
        # This retruns the price of
        return _reserves[0] / _reserves[1]
