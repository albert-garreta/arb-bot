def test_bot():
    from scripts.bot import Bot
    import bot_config
    from brownie import interface

    Bot().run()


def test_run_epoch():

    from scripts.bot import Bot
    bot = Bot()
    bot.arb_data.update_to_best_possible()
    bot.arb_data.set_summary_message()
    bot.arb_data.print_summary()
    # bot.arb_data.buy_dex_index=0
    tx = bot.act()
