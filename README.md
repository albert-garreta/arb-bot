**UniswapV2-based Arbitrage bot**

This is a non-competitive arbitrage bot, similar to others out there.

*General notes*
- The bot scans for pairs on different UniswapV2-based DEXes and trades accordingly when the price of token1 with respect to token0 among two different DEXes is "sufficiently different". 
- The "sufficient difference" is the value that maximizes a certain convex function --see `prices.py' for more information--, and it depends on the dexes reserves and the fees. See . 
- The bot leverages UniswapV2's flash-swaps so that the bot does not need to hold any tokens in order to operate.
- 
  
*Technical notes and usage unformation*
- The bot uses brownie's framework. To run it it is equired to have brownie installed, then do
    <brownie run/scripts/bot.py --network [network-name]>