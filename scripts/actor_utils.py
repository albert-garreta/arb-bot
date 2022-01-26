import bot_config
from scripts.utils import get_account


def prepare_actor(_all_dex_to_pair_data, _actor):
    """Preliminary steps to the flashloan request and actions which can be done beforehand"""
    print("Preparing actor for a future flashloan...")
    account = get_account()

    print(_all_dex_to_pair_data["token_data"].keys())
    token0, name0, decimals0 = _all_dex_to_pair_data["token_data"][
        bot_config.token_names[0]
    ]
    token1, name1, decimals1 = _all_dex_to_pair_data["token_data"][
        bot_config.token_names[0]
    ]
    required_balance =  bot_config.amount_for_fees_token0 + bot_config.extra_cover
    adjust_actor_balance(_actor, token0, name0, decimals0, required_balance)
    required_balance =  bot_config.amount_for_fees_token1 + bot_config.extra_cover
    adjust_actor_balance(_actor, token1, name1, decimals1, required_balance)

    # TODO: Do I need to return the actor here?
    print("Preparation completed")
    return _actor


def adjust_actor_balance(_actor, _token, _name, _decimals, _required_balance):
    account = get_account()
    
    _required_balance *= 10 ** _decimals

    token0s_aldready_in_actor = _token.balanceOf(_actor.address, {"from": account})
    amount_token0_to_actor = max(_required_balance - token0s_aldready_in_actor, 0)

    if amount_token0_to_actor > 0:
        # !! transferFrom and approve since we are transfering from an external account (ours)
        print(
            f"Approving {amount_token0_to_actor} of "
            f"{_name} for transfering to actor..."
        )
        tx = _token.approve(
            _actor.address, amount_token0_to_actor + 10000, {"from": account}
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
            amount_token0_to_actor,
            {"from": _actor.address},
        )
        tx.wait(1)
        print("Transfer done")
    else:
        # TODO: Why did this happen?
        print("ATTENTION: actor holds too much tokens0s. How did this happen?")

