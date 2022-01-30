from socket import MSG_EOR
import bot_config
from scripts.data_structures.general_data import GeneralData
from scripts.data_structures.dotdict import dotdict
from scripts.prices.prices import find_optimal_borrow_amount_and_net_profit
from scripts.utils import log, mult_list_by_scalar


def get_arbitrage_data(_buy_dex_index, _reserves):
    sell_dex_index = (_buy_dex_index + 1) % 2
    arb_data = ArbitrageData()
    arb_data.sell_dex_index = sell_dex_index
    arb_data.reserves_buying_dex = _reserves[_buy_dex_index]
    arb_data.reserves_selling_dex = _reserves[sell_dex_index]
    arb_data.fees_buy_dex = bot_config.dex_fees[_buy_dex_index]
    arb_data.fees_sell_dex = bot_config.dex_fees[sell_dex_index]
    arb_data.slippage_buy_dex = bot_config.slippages[_buy_dex_index]
    arb_data.slippage_sell_dex = bot_config.slippages[sell_dex_index]
    return arb_data


class ArbitrageData(GeneralData):
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
        self.net_profit = None

    def update_given_buy_dex_and_reserves(self, _buy_dex_index, _reserves):
        self.buy_dex_index = _buy_dex_index
        sell_dex_index = self.get_sell_dex_index(_buy_dex_index)
        self.sell_dex_index = sell_dex_index
        self.fees_buy_dex = self.dex_fees[_buy_dex_index]
        self.fees_sell_dex = self.dex_fees[sell_dex_index]
        self.slippage_buy_dex = self.dex_slippages[_buy_dex_index]
        self.slippage_sell_dex = self.dex_slippages[sell_dex_index]
        self.reserves_buying_dex = _reserves[self.buy_dex_index]
        self.reserves_selling_dex = _reserves[self.sell_dex_index]

    def get_sell_dex_index(self, _buy_dex_index):
        return (_buy_dex_index + 1) % 2

    def get_optimal_borrow_amount_and_net_profit(self):
        # NOTE: These cannot be set as object attributes here because we need to
        # do some checks to find the best possible arbitrage set up
        optimal_amount, net_profit = find_optimal_borrow_amount_and_net_profit(self)
        return optimal_amount, net_profit

    def update_optimal_borrow_amount_and_net_profit(self, optimal_amount, net_profit):
        self.optimal_borrow_amount = optimal_amount
        self.net_profit = net_profit

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

    def passes_arbitrage_requirements(self):
        net_profit = self.net_profit
        requirement = True
        # profit_ratio = self.get_profit_ratio()
        #requirement = profit_ratio > bot_config.min_profit_ratio
        requirement = requirement and net_profit > bot_config.min_net_profit
        requirement = requirement or bot_config.force_actions
        requirement = requirement and (not bot_config.passive_mode)
        return requirement

    def get_summary_message(self):
        msg = ""
        msg += f"Reserves buying dex: {mult_list_by_scalar(self.reserves_buying_dex,1e-18)}\n"
        msg += f"Reserves selling dex: {mult_list_by_scalar(self.reserves_selling_dex,1e-18)}\n"
        msg += f"Buying dex index: {self.buy_dex_index}\n"
        msg += f"Optimal borrow amount: {self.optimal_borrow_amount/1e18}\n"
        msg += f"Net profit: {self.net_profit/1e18}\n"
        # msg += f"Profit ratio: {self.get_profit_ratio()}\n"
        self.summary_message = msg

    def print_summary(self):
        self.get_summary_message()
        print(self.summary_message)

    def log_summary(self, path):
        log(self.summary_message, path)
