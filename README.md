# UniswapV2-based Arbitrage bot

This is a non-competitive arbitrage bot, not too different from others out there. It works with UniswapV2-type dexes on EVM-compatible chains.

(This is a blockchain-related repository)

## General notes

- The bot scans for different pairs (`token0`, `token1`) on different UniswapV2-based dexes (decentralized exchanges) and trades accordingly when the price of `token1` with respect to `token0` among two different dexes is "sufficiently different". More precisely, when the price of `token1` is significantly cheaper on `dex0` than on `dex1`, the bot uses UniswapV2's flashloan to borrow a acertain amount `x` of `token1` from `dex0` (technically, it borrows it from the `token0/token1` LP in `dex0`). Then sells the loaned `token1`'s on `dex1`, and returns the loan value to `dex0`.
- The "certain amount `x`" is the value that maximizes a certain convex function --see `prices.py` for more information--, and it depends on the dexes' reserves and their fees. If the prices between `dex0` and `dex1` are not sufficiently different, this value is negative and arbitrage cannot be profitable.
- NOTE: Someone may wonder why, if there is a price difference sufficient to compensate for the fees, not borrow as much `token1` as possible? The reason for this is essentially that, in UniswapV2 dexes, the amount of `token0` one gets by exchanging `token1` for `token0` is given by the following formula:
    $$amount\_token1* (1-fees) \frac{ reserves\_token0 } { reserves\_token1 + amount\_token1*(1-fees) } $$
    This tends to 1 as `amount_token` tends to infinity. These type of formulas come from the so-called $x*y\geq k$ equation.
- The bot leverages UniswapV2's flash-swaps so that the bot does not need to hold any tokens in order to operate (except for paying for transaction fees).
- It works as little as possible on the blockchain, externalizing as many computations as possible to the local machine running the bot.

- This bot is similar to many open-sourced bots. It will not be competitive and one should not expect to obtain gains from running it. I wrote it as an exercise on smartcontract development.


## Technical notes and usage information

- The bot has been partially tested only. 
- The bot runs on brownie's framework. To run it do: > `brownie run/scripts/bot.py --network [network-name]`
- It is required to have brownie installed. The code at this point expects to find the account's private key and other necessary information (such as, depending on the network to be used, an Infura Project ID) in a `.env` file.
- To set the different tokens the bot is going to inspect, go to `brownie-config.yaml` under the desired network. Add the token names to trade, their addresses, and their coingecko API id (note: the api ids must match the order in which the token names are listed). Then set the two dex names to trade on, and add their `UniswapV2Router` and `UniswapV2Factory` addresses.
- The above configuration is ready-to-go for the networks `ftm-main`, `avax-main`, and `polygon-main`.

## Other notes

- The bot has the feature to send relevant notifications to a telegram bot. For this, one needs to configure `telegram-send` correctly. Telegram notifications can be deactivated in `bot_config.py` setting `telegram_notifications=False`.
- The bot constantly inspects different pairs of tokens gathered from a given list of tokens. The number of pairs grows almost exponentially with the number of tokens. To try to solve this problem the bot implements an heuristic to increase the number of inspections dedicated to the most promising pairs among all
possible pairs. This heuristic is given by the `Exp30` algorithm for Adversarial Multi Armed Bandits, see <https://en.wikipedia.org/wiki/Multi-armed_bandit>.
_NOTE:_ in hindsight, the benefits of using this heuristic are dubious. I am quite sure that simply choosing pairs randomly produces  similar performance. 

To deactivate the multi_armed_bandit heuristic set `bandit_exploration_probability=1` in `bot_config.py`

## Open issues

[UniswapV2: LOCKED (reentrancy error) coming out of nowhere at seemingly random occassions](https://github.com/albert-garreta/arb-bot/issues/1) 
UPDATE: It seems this occurs after a previous transaction errored out.
