def get_net_profit_v3(_amount_tkn1_to_borrow, _state_data):
    # Given an amount of token1 to borrow and state_data with assigned buying and selling dexes,
    # this function computes the net profit that the arbitrage of epartion would accrue
    buy_dex_data = _state_data.get_dex_data(_buying=True)
    sell_dex_data = _state_data.get_dex_data(_buying=False)
    amt_out_tkn0_selling_dex1 = get_dex_amount_out(
        _amount_tkn1_to_borrow,
        sell_dex_data,
    )
    amt_tkn0_to_return_dex0 = get_dex_amount_in(
        _amount_tkn1_to_borrow,
        buy_dex_data,
    )
    net_profit = amt_out_tkn0_selling_dex1 - amt_tkn0_to_return_dex0
    return net_profit


def get_dex_amount_out(_amount_in, state_data):
    # Unpacks state_data
    return _get_dex_amount_out(
        _amount_in,
        state_data.reserves_in,
        state_data.reserves_out,
        state_data.fee,
        state_data.slippage,
    )


def get_dex_amount_in(_amount_out, state_data):
    # Unpacks state_data
    return _get_dex_amount_in(
        _amount_out,
        state_data.reserves_in,
        state_data.reserves_out,
        state_data.fee,
        state_data.slippage,
    )


def _get_dex_amount_out(_amount_in, _reserve_in, _reserve_out, _dex_fee, _slippage=0):
    # Function from UniswapV2Library with added slippage
    fee = 1 - _dex_fee / 100
    numerator = _amount_in * fee * _reserve_out
    denominator = _reserve_in + fee * _amount_in
    amount_out = numerator / denominator
    amount_out = amount_out * (1 - (_slippage / 100))
    return amount_out


def _get_dex_amount_in(_amount_out, _reserve_in, _reserve_out, _dex_fee, _slippage=0):
    # Function from UniswapV2Library with added slippage
    fee = 1 - _dex_fee / 100
    numerator = _amount_out * _reserve_in
    # This has been modified to avoid negative returned values
    denominator = max(0.01, (_reserve_out - _amount_out)) * fee
    _amount_in = numerator / denominator
    _amount_in += 1
    _amount_in = _amount_in / (1 - (_slippage / 100))
    return _amount_in
