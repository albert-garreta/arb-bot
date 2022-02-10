# UniswapV2-based Arbitrage bot

This is a non-competitive arbitrage bot, not too different from others out there. It works with UniswapV2-type dexes on EVM-compatible chains.

(This is a blockchain-related repository)

## General notes

- The bot scans for different pairs (token0, token1) on different UniswapV2-based DEXes and trades accordingly when the price of token1 with respect to token0 among two different DEXes is "sufficiently different".
- The "sufficient difference" is the value that maximizes a certain convex function --see `prices.py` for more information--, and it depends on the dexes' reserves and their fees.
- The bot leverages UniswapV2's flash-swaps so that the bot does not need to hold any tokens in order to operate.
- It works as little as possible on the blockchain, externalizing as many computations as possible to the local machine running the bot.

## Technical notes and usage information

- The bot has been partially tested only. It is not meant to be used for competitive arbitrage.
- The bot runs on brownie's framework. To run it do: > `brownie run/scripts/bot.py --network [network-name]`
- It is required to have brownie installed. The code at this point expects to find the account's private key and other necessary information (such as, depending on the network to be used, an Infura Project ID) in a `.env` file.
- To set the different tokens the bot is going to inspect, go to `brownie-config.yaml` under the desired network. Add the token names to trade, their addresses, and their coingecko API id (note: the api ids must much the order in which the token names are listed). Then set the two dex names to trade on, and add their `UniswapV2Router` and `UniswapV2Factory` addresses.
- The above configuration is ready-to-go for the networks `ftm-main`, `avax-main`, and `polygon-main`.
- _more documentation to come_

## Other notes

- The bot has the feature to send relevant notifications to a telegram bot. For this, one needs to configure `telegram-send` correctly. Telegram notifications can be deactivated in `bot_config.py` setting `telegram_notifications=False`.
- The bot constantly inspects different pairs of tokens gathered from a given list of tokens. The number of pairs grows almost exponentially with the number of tokens. To try to solve this problem the bot implements an heuristic to increase the number of inspections dedicated to the most promising pairs among all
possible pairs. This heuristic is given by the `Exp30` algorithm for Adversarial Multi Armed Bandits, see <https://en.wikipedia.org/wiki/Multi-armed_bandit>.
_NOTE:_ the benefits of using this heuristic are dubious. I am quite sure that simply choosing pairs randomly would produce a similar performance. However the idea of optimizing the pair inspection mechanism was interesting to me. 

To deactivate the multi_armed_bandit heuristic set `bandit_exploration_probability=1` in `bot_config.py`

## Open issues

- [UniswapV2: LOCKED (reentrancy error) coming out of nowhere at seemingly random occassions](https://github.com/albert-garreta/arb-bot/issues/1)
