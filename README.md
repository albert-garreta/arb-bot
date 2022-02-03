# UniswapV2-based Arbitrage bot

This is a non-competitive arbitrage bot, not too different from others out there. I am currently in the process of refactoring and cleaning it up a little bit.

## General notes

- The bot scans for pairs on different UniswapV2-based DEXes and trades accordingly when the price of token1 with respect to token0 among two different DEXes is "sufficiently different".
- The "sufficient difference" is the value that maximizes a certain convex function --see `prices.py` for more information--, and it depends on the dexes reserves and the fees.
- The bot leverages UniswapV2's flash-swaps so that the bot does not need to hold any tokens in order to operate.
- It works as little as possible on the blockchain, externalizing as many computations as possible to the local machine running the bot.

## Technical notes and usage information

- The bot runs on brownie's framework. To run it do: > `brownie run/scripts/bot.py --network [network-name]`
- It is required to have brownie installed. The code at this point expects to find the account's private key and other necessary information (such as an Infura Project ID) in a `.env` file.
- At this point the bot only inspects one pair of tokens in two different dexes per run. To set these up, go to `brownie-config.yaml`, under the desired network, set the two token names to trade, add their addresses. Then set the two dex names to trade on, and add their `UniswapV2Router` and `UniswapV2Factory` addresses.
- _more documentation to come_

## Other notes

- The bot has the feature to send relevant notifications to a telegram bot
