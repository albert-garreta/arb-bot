from brownie import network, interface, config
from scripts.utils import get_account


def get_dex_amount_out(_amount_in, dex_data):
    return _get_dex_amount_out(
        _amount_in,
        dex_data.reserve_in,
        dex_data.reserve_out,
        dex_data.fee,
        dex_data.slippage,
    )


def get_dex_amount_in(_amount_out, dex_data):
    return _get_dex_amount_in(
        _amount_out,
        dex_data.reserve_in,
        dex_data.reserve_out,
        dex_data.fee,
        dex_data.slippage,
    )


def _get_dex_amount_out(_amount_in, _reserve_in, _reserve_out, _dex_fee, _slippage=0):
    # Function from UniswapV2Library with slippage
    fee = 1 - _dex_fee / 100
    numerator = _amount_in * fee * _reserve_out
    denominator = _reserve_in + fee * _amount_in
    amount_out = numerator / denominator
    amount_out = amount_out * (1 - (_slippage / 100))
    return amount_out


def _get_dex_amount_in(_amount_out, _reserve_in, _reserve_out, _dex_fee, _slippage=0):
    # Function from UniswapV2Library with slippage
    # TODO: the fee here appears once instead of twice as above. Is this advantageous?
    fee = 1 - _dex_fee / 100
    numerator = _amount_out * _reserve_in
    denominator = _reserve_out + fee * _amount_out
    amount_out = numerator / denominator
    amount_out += 1  # this is in UniswapV2Library. Why?
    amount_out = amount_out * (1 - (_slippage / 100))
    return amount_out


def get_oracle_price(oracle=None, buying=True):
    if oracle is None:
        oracle_address = config["networks"][network.show_active()]["price_feed_address"]
        oracle = interface.AggregatorV3Interface(oracle_address)
    _, price, _, _, _ = oracle.latestRoundData({"from": get_account()})
    # TODO: implement correct general decimal formatting. Now assuming 8 decimals
    price /= 1e8
    if buying:
        return 1 / price
    else:
        return price
