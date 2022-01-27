from scripts.bot import preprocess, look_for_arbitrage, act
from scripts.data import get_all_dex_reserves
from scripts.deploy import deploy_actor
from scripts.utils import get_account, get_token_addresses
import bot_config
from brownie import interface


def test_preprocess():
    token_addresses = get_token_addresses(bot_config.token_names)
    pair_dex_data, actor = preprocess()
    print(
        f"Actor balance of {bot_config.token_names[0]}: {interface.IERC20(token_addresses[0]).balanceOf(actor.address)}"
        f"Actor balance of {bot_config.token_names[1]}: {interface.IERC20(token_addresses[1]).balanceOf(actor.address)}"
    )


def test_act():
    pair_dex_data, actor = preprocess()
    all_reserves = get_all_dex_reserves(pair_dex_data)
    arb_info = look_for_arbitrage(all_reserves, _force_success=True)
    act(pair_dex_data, arb_info, actor, _verbose=True)
