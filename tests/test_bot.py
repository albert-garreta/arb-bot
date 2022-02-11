from brownie import interface


def test_run():
    from scripts.bot import Bot

    bot = Bot()
    bot.testing = True
    return bot.run()


def test_run_epoch():

    # The test is run for the pair WFTM-USDC on ftm-main-fork
    # In general the bot will not be able to complete
    # a flashloan operation because the LP reserves may not be ideal.
    # For this reason we are sending wftm to the bot, so even if it
    # executes an unfavorable arbitrage operation, it still has enough
    # funds to return to the LP.

    from scripts.bot import Bot
    from scripts.utils import get_account

    bot = Bot()

    bot.choose_and_set_token_pair()
    bot.variable_pair_data.update_to_best_possible()

    wrapped_main_token = interface.IWERC20(bot.variable_pair_data.token_addresses[0])
    amount_to_transfer = 0.66 * get_account().balance()
    wrapped_main_token.deposit({"from": get_account(), "value": amount_to_transfer})
    wrapped_main_token.transfer(
        bot.bot_smartcontract.address, amount_to_transfer, {"from": get_account()}
    )

    balance_bot = wrapped_main_token.balanceOf(bot.bot_smartcontract.address)
    assert (balance_bot == amount_to_transfer, f"{balance_bot}_{amount_to_transfer}")
    print(f"Bot balance: {balance_bot/1e18}")
    bot.variable_pair_data.set_summary_message()
    print(bot.variable_pair_data.summary_message)
    tx = bot.engage_in_arbitrage()
    print(tx.info())
