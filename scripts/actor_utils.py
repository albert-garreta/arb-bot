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
    amount_token0_to_actor = bot_config.amount_for_fees + bot_config.extra_cover
    amount_token0_to_actor *= 10 ** decimals0

    token0s_aldready_in_actor = token0.balanceOf(_actor.address, {"from": account})
    amount_token0_to_actor = max(amount_token0_to_actor - token0s_aldready_in_actor, 0)

    if amount_token0_to_actor > 0:
        # !! transferFrom and approve since we are transfering from an external account (ours)
        print(
            f"Approving {amount_token0_to_actor} of "
            f"{name0} for transfering to actor..."
        )
        tx = token0.approve(
            _actor.address, amount_token0_to_actor + 10000, {"from": account}
        )
        tx.wait(1)
        print("Approved")

        # TODO: Is it dangerous to make the transfer now? (grieffing attack?)
        print(f"Transferring {name0} to Actor...")
        # TODO: Check if this can be done just with a transfer
        # POSSIBLE ANSWER: I think so, but must add PAYABLE to Actor. <- Check
        tx = token0.transferFrom(
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
    print("Preparation completed")
    return _actor
