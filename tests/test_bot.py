def test_run():
    from scripts.bot import Bot
    import bot_config
    from brownie import interface

    bot = Bot()
    bot.testing = True
    return bot.run()


def test_run_epoch():

    from scripts.bot import Bot

    bot = Bot()
    bot.choose_and_set_token_pair()
    bot.state_data.update_to_best_possible()
    bot.update_multi_armed_bandit()
    bot.state_data.set_summary_message()
    bot.state_data.print_summary()
    return bot.act_test()
