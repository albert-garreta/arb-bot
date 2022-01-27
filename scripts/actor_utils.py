from black import token
import bot_config
from scripts.prices import get_approx_price
from scripts.utils import get_account, num_digits, get_wallet_balances
from brownie import interface, config, network


def prepare_actor(_all_dex_to_pair_data, _all_reserves, _actor):
    """Preliminary steps to the flashloan request and actions which can be done beforehand"""
    print("Preparing actor for a future flashloan...")

    print(_all_dex_to_pair_data["token_data"].keys())
    token0, name0, decimals0 = _all_dex_to_pair_data["token_data"][
        bot_config.token_names[0]
    ]
    token1, name1, decimals1 = _all_dex_to_pair_data["token_data"][
        bot_config.token_names[1]
    ]

    # TODO: Here we are choosing a dex arbitrarily. Probably it does not matter much?
    reserves0 = _all_reserves[0]

    required_balance_token0 = (bot_config.amount_for_fees + bot_config.extra_cover) / 2
    adjust_actor_balance(
        _actor, token0, name0, decimals0, required_balance_token0, reserves0
    )
    required_balance_token1 = required_balance_token0 / get_approx_price(
        reserves0, buying=True
    )
    adjust_actor_balance(
        _actor, token1, name1, decimals1, required_balance_token1, reserves0
    )

    # TODO: Do I need to return the actor here?
    print("Preparation completed")
    return _actor


def adjust_actor_balance(
    _actor,
    _token,
    _name: str,
    _decimals: int,
    _required_balance: int,
    _dex_reserves: tuple[int, int],
) -> None:
    account = get_account()
    # We need to adjust the decimals here
    _required_balance = int(_required_balance * 10 ** (_decimals - 18))
    print(f"Required balance of {_name} for actor: {_required_balance}")
    tokens_aldready_in_actor = _token.balanceOf(_actor.address, {"from": account})
    print(f"Tokens {_name} already in actor: {tokens_aldready_in_actor}")
    amount_token_to_actor = max(_required_balance - tokens_aldready_in_actor, 0)
    print(f"Tokens to transfer to actor: {amount_token_to_actor}")
    token_balance_caller = _token.balanceOf(account.address)
    print(f"Caller {_name} balance {token_balance_caller}")
    if token_balance_caller < amount_token_to_actor:
        print(f"Caller {_name} balance is insufficient.")

        # FIXME: caution: here I am assuming that WFTM=token0. To do it in general
        # I need to make a get_approx_price function that is able to compute
        # more prices than just token0/token1 ot token1/token0
        wrapped_token_address = config["networks"][network.show_active()][
            "wrapped_main_token_address"
        ]
        price_wrap_to_token1 = get_approx_price(_dex_reserves, buying=False)
        # The token being sent away has 18 decimals if it is WFTM
        # TODO: make it genera (any decimals, seee FIXME above)
        _max_amount_in = int(
            (amount_token_to_actor / price_wrap_to_token1) * 10 ** (18 - _decimals)
        )
        # we add 10% more to accomodate price variability
        _max_amount_in *= 1.1

        print("Approving spending...")
        tx = interface.IERC20(wrapped_token_address).approve(
            _actor.address, _max_amount_in, {"from": account}
        )
        tx.wait(1)
        print("Approved")

        swap_tokens_for_exact_tokens(
            wrapped_token_address,
            _token.address,
            amount_token_to_actor,
            _max_amount_in,
            _name,
            account,
            _actor,
        )

    if amount_token_to_actor > 0:
        # !! transferFrom and approve since we are transfering from an external account (ours)
        print(
            f"Approving {amount_token_to_actor} of "
            f"{_name} for transfering to actor..."
        )
        tx = _token.approve(
            _actor.address, amount_token_to_actor + 10000, {"from": account}
        )
        tx.wait(1)
        print("Approved")

        # TODO: Is it dangerous to make the transfer now? (grieffing attack?)
        print(f"Transferring {_name} to Actor...")
        # TODO: Check if this can be done just with a transfer
        # POSSIBLE ANSWER: I think so, but must add PAYABLE to Actor. <- Check
        tx = _token.transferFrom(
            account.address,
            _actor.address,
            amount_token_to_actor,
            {"from": _actor.address},
        )
        tx.wait(1)
        print("Transfer done")
    else:
        # TODO: Why did this happen?
        print("ATTENTION: actor holds too much tokens0s. How did this happen?")


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
        f"Current caller {_name} balance: {interface.IERC20.balaceOf(_account.address)}"
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
        f"Current caller {_name} balance: {interface.IERC20.balaceOf(_account.address)}"
    )
