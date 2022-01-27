from scripts.bot import preprocess, look_for_arbitrage, act
from scripts.prices import get_reserves
from scripts.deploy import deploy_actor
from scripts.utils import get_account, get_token_addresses
import bot_config
from brownie import interface


def test_preprocess():
    account = get_account()
    token_addresses = get_token_addresses()
    pair_dex_data, actor = preprocess()
    print(
        f"Actor balance of {bot_config.token_names[0]}: {interface.IERC20(token_addresses[0]).balanceOf(actor.address)}"
        f"Actor balance of {bot_config.token_names[1]}: {interface.IERC20(token_addresses[1]).balanceOf(actor.address)}"
    )
    


def test_act():
    pair_dex_data, actor = preprocess()
    reserves_all_dexes = get_reserves(pair_dex_data, _dex_index=0, _verbose=True)
    arb_info = look_for_arbitrage(reserves_all_dexes)
    act(arb_info, actor, _verbose=True)
