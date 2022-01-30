from black import token
import bot_config
from scripts.prices.prices import get_approx_price
from scripts.utils import (
    get_account,
    ensure_amount_of_wrapped_maintoken,

)
from bot_config import LOCAL_BLOCKCHAIN_ENVIRONMENTS,NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS
from scripts.data_structures.general_data import get_dex_router_and_factory
from brownie import interface, config, network
import warnings
import numpy as np


def prepare_actor(_all_dex_to_pair_data, _all_reserves, _actor):
    # FIXME: this currently is innefficient (because in some cases it is possible that we
    # make two transfers of WFTM to actor, when we could do it with just one transfer)
    # and messy (in how the amounts to transfer are computed, in having the hardcoded 0
    # as index of dex being used twice).

    """Preliminary steps to the flashloan request and actions which can be done beforehand"""
    print("Preparing actor for a future flashloan...")

    if (
        network.show_active()
        in LOCAL_BLOCKCHAIN_ENVIRONMENTS + NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS
    ):
        ensure_amount_of_wrapped_maintoken(
            bot_config.weth_balance_actor_and_caller,
            _actor,
        )

    token0, name0, decimals0 = _all_dex_to_pair_data["token_data"][
        bot_config.token_names[0]
    ]
    token1, name1, decimals1 = _all_dex_to_pair_data["token_data"][
        bot_config.token_names[1]
    ]

    required_balance_token0 = bot_config.amount_for_fees_tkn0 + 1000000
    adjust_actor_balance(
        _actor, token0, name0, decimals0, required_balance_token0, _all_reserves
    )
    required_balance_token1 = bot_config.amount_for_fees_tkn1_in_tkn0

    adjust_actor_balance(
        _actor, token1, name1, decimals1, required_balance_token1, _all_reserves
    )

    # TODO: Do I need to return the actor here?
    print("Preparation completed")
    return _actor


def adjust_actor_balance(
    _actor,
    _token,
    _name: str,
    _decimals: int,
    _required_balance: int,  # in wei
    _all_reserves,
) -> None:
    account = get_account()
    # We need to adjust the decimals here
    _required_balance = int(_required_balance / 10 ** (18 - _decimals))
    print(f"Required balance of {_name} for actor: {_required_balance}")
    tokens_aldready_in_actor = _token.balanceOf(_actor.address, {"from": account})
    print(f"Tokens {_name} already in actor: {tokens_aldready_in_actor}")
    amount_missing = max(_required_balance - tokens_aldready_in_actor, 0)
    print(f"Amount missing: {amount_missing}")

    if amount_missing <= 0:
        print("Actor has already enough balance")
    else:
        token_balance_caller = _token.balanceOf(account.address)
        print(f"Caller {_name} balance {token_balance_caller}")
        if token_balance_caller >= amount_missing:
            print(f"Caller has enough {_name}. Sending it to actor...")
            # TODO: do I need to approve here?
            tx = _token.approve(
                _actor.address, amount_missing + 1000, {"from": account}
            )
            tx.wait(1)
            # ATTENTION to the "from":_actor.address
            tx = _token.transfer(
                _actor.address,
                amount_missing,
                {"from": account},
            )
            tx.wait(1)
            print("Transfered")
        else:
            # TODO:
            # So far we only allow to do this if we are testing
            # And we assume that token0 is the wrapped main token
            if (
                network.show_active()
                not in LOCAL_BLOCKCHAIN_ENVIRONMENTS
                + NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS
            ):
                raise Exception(f"Caller has not enough {_name}")
            assert (
                _name == bot_config.token_names[1]
            ), f"Token {_name} to be swapped should be {bot_config.token_names[1]}"

            weth = interface.IWeth(
                config["networks"][network.show_active()]["token_addresses"][
                    "wrapped_main_token_address"
                ]
            )
            price_tkn0_to_tkn1 = get_approx_price(_all_reserves, _buying=False)
            max_amount_in = amount_missing / price_tkn0_to_tkn1 + 1e18
            swap_tokens_for_exact_tokens(
                weth.address,
                _token.address,
                amount_missing,
                max_amount_in,
                _name,
                account,
                _actor,
            )


def swap_tokens_for_exact_tokens(
    _token_in_address,
    _token_out_address,
    _amount_out,
    _max_amount_in,
    _name,
    _account,
    _actor,
):
    print(
        f"Swapping at most {_max_amount_in} wrapped mainnet token "
        f"for {_amount_out} {_name} (tokens for exact tokens)"
    )

    router, factory = get_dex_router_and_factory(bot_config.dex_names[0])

    tx = interface.IERC20(_token_in_address).approve(
        router.address, _max_amount_in, {"from": get_account()}
    )
    tx.wait(1)

    # function swapTokensForExactTokens(
    # address _tokenInAddress,
    # address _tokenOutAddress,
    # uint256 _amountOut,
    # uint256 _minAmountOut,
    # uint256 _dexIndex
    tx = router.swapTokensForExactTokens(
        _token_in_address,
        _token_out_address,
        _amount_out,
        _max_amount_in,
        0,
        {"from": _account},
    )
    tx.wait(1)
    print("Swap done")
    print(
        f"Actor {_name} balance: {interface.IERC20(_token_out_address).balanceOf(_actor.address)}"
    )


def swap_exact_tokens_for_tokens(
    _token_in_address,
    _token_out_address,
    _amount_in,
    _min_amount_out,
    _name,
    _account,
    _actor,
):
    print(f"Swapping wrapped mainnet token for {_name} (exact tokens for tokens)")

    # function swapTokensForExactTokens(
    # address _tokenInAddress,
    # address _tokenOutAddress,
    # uint256 _amountOut,
    # uint256 _minAmountOut,
    # uint256 _dexIndex
    tx = _actor.swapTokensForExactTokens(
        _token_in_address,
        _token_out_address,
        _amount_in,
        _min_amount_out,
        0,
        {"from": _account},
    )
    tx.wait(1)
    print("Swap done")
    print(
        f"Actor {_name} balance: {interface.IERC20(_token_out_address).balanceOf(_actor.address)}"
    )
