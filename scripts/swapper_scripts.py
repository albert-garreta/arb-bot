from brownie import interface
from scripts.utils import get_account


def two_hop_arbitrage(
    _swapper,
    _token0,
    _token1,
    _amount_in,
    _min_amount_out0,
    _min_amount_out1,
    _router0_index,
    _router1_index,
):
    # This function is not actually used, since we need to use this function inside
    # the executeOperation method of the flashloan logic in the Actor contract. 
    # Howver this is the pythonic version of the function in solidity, which can be
    # used for testing more conveniently
    # TODO can I write a test for the solidity function?

    account = get_account()
    tx = _token0.approve(_swapper.address, _amount_in, {"from": account})
    tx.wait(1)
    
    tx = _swapper.swapExactTokensForTokens(
        _token0.address,
        _token1.address,
        _amount_in,
        _min_amount_out0,
        _router0_index,
    )
    tx.wait(1)
    

    amount_out_first_swap = _swapper.amountOutFromSwap()
    _token1.approve(_swapper.address, amount_out_first_swap, {"from": account})
    tx = _swapper.swapExactTokensForTokens(
        _token1.address,
        _token0.address,
        amount_out_first_swap,
        _min_amount_out1,
        _router1_index,
    )
    tx.wait(1)
