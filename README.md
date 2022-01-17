
The bot runs an epoch every time n_blocks are mined.
Each epoch consists in the following:

We work with a list of dexes, list_dexes, and with a list of prices, list_tokens, denominated in a stablecoin.
1. The bot checks if the prices of some token in list_tokens is different between two different dexes in list_dexes.
2. The bot determines if this difference in price is sufficient.
3. If it is, it executes a flashloan and swaps for profit.