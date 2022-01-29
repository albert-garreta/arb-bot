from black import token
import bot_config
from scripts.prices import get_approx_price, get_best_dex_and_approx_price
from scripts.utils import get_account, num_digits, get_wallet_balances
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

    buying_dex_index, best_approx_price = get_best_dex_and_approx_price(_all_reserves, buying=True)
    required_balance_token1 = (
        bot_config.amount_for_fees_tkn1_in_tkn0
        + bot_config.amount_for_fees_tkn1_extra_in_tkn0
    ) / best_approx_price


    adjust_actor_balance(
        _actor,
        token1,
        name1,
        decimals1,
        required_balance_token1,
        _all_reserves[buying_dex_index],
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
    _dex_reserves: tuple[int, int],
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
            print(f"Caller has not enough {_name}")
            print(
                f"Sending wrapped mainnet token to actor so that actor can swap it for {_name}"
            )

            # FIXME: caution: here I am assuming that WFTM=token0. To do it in general
            # I need to make a get_approx_price function that is able to compute
            # more prices than just token0/token1 ot token1/token0
            wrapped_token_address = config["networks"][network.show_active()][
                "token_addresses"
            ]["wrapped_main_token_address"]

            assert (
                wrapped_token_address
                == config["networks"][network.show_active()]["token_addresses"][
                    bot_config.token_names[0]
                ],
                "This part of this function is implemented assuming that token0 == wrapped main token."
                "General functionality not yet implemented",
            )

            price_wrapped_maintoken_to_token1 = get_approx_price(
                _dex_reserves, buying=False
            )
            # The token being sent away has 18 decimals if it is WFTM
            # TODO: make it general (any decimals, seee FIXME and assertion above)
            _max_amount_in = int(
                (amount_missing / price_wrapped_maintoken_to_token1)
                * 10 ** (18 - _decimals)
            )
            # we add some % more to accomodate price variability
            _max_amount_in *= 1.05

            wrapped_token = interface.IERC20(wrapped_token_address)
            print("Approving spending for actor...")
            # TODO: no need to approve?
            tx = wrapped_token.approve(
                _actor.address, _max_amount_in, {"from": account}
            )
            tx.wait(1)
            print("Approved")

            print(f"Sending {_max_amount_in} wrapped main token to actor...")
            tx = wrapped_token.transfer(
                _actor.address, _max_amount_in, {"from": account}
            )
            tx.wait(1)
            print("sent")

            # TODO: It may make more sense to just swap directly with the router instead
            # of transferring first to the actor and then making the actor swap. I think it is
            # basically the same, but maybe it makes more sense from a logical perspective

            # router_address = config["networks"][network.show_active()][
            #     bot_config.dex_names[0]
            # ]
            # router = interface.UniswapV2Router(router_address)
            # router.swapTokensForExactTokens(amount_token_to_actor, _max_amount_in, [wrapped_token_address, _token.address], )

            swap_tokens_for_exact_tokens(
                wrapped_token_address,
                _token.address,
                amount_missing,
                _max_amount_in,
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

    # function swapTokensForExactTokens(
    # address _tokenInAddress,
    # address _tokenOutAddress,
    # uint256 _amountOut,
    # uint256 _minAmountOut,
    # uint256 _dexIndex
    tx = _actor.swapTokensForExactTokens(
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
