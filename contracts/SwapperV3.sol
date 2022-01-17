// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;
//abicoder v2 to allow arbitrary nested arrays and structs to be encoded and
//decoded in calldata, a feature used when executing a swap.
pragma abicoder v2;

import "./uniswap/ISwapRouter.sol";
import "./uniswap/TransferHelper.sol";

contract ExampleSwapV3 {

    // Immutable modifier: State variables can be marked immutable which causes them
    // to be read-only, but assignable in the constructor.
    // The value will be stored directly in the code.
    ISwapRouter public immutable swapRouter;
    address[] public token_addresses;

    // For this example, we will set the pool fee to 0.3%.
    // Constant modifier: Disallows assignment (except initialisation),
    // does not occupy storage slot.
    uint24 public constant poolFee = 3000;

    constructor(address[] memory _token_addresses, ISwapRouter _swap_router_address) {
        token_addresses = _token_addresses;
        swapRouter = ISwapRouter(_swap_router_address);
    }

    /// @notice swapExactInputSingle swaps a fixed amount of DAI for a maximum possible amount of WETH9
    /// using the DAI/WETH9 0.3% pool by calling `exactInputSingle` in the swap router.
    /// @dev The calling address must approve this contract to spend at least `amountIn` worth of its DAI for this function to succeed.
    /// @param _amountIn The exact amount of DAI that will be swapped for WETH9.
    /// @return amountOut The amount of WETH9 received.
    function swapExactInputSingle(
        uint256 _amountIn
    ) external returns (uint256 amountOut) {
        // @mtden: eventyally I will want to have a whole list and pass the 
        // addresses or names of the tokens to swap as arguments.
        // This allows to deploy before the arbitrage oportunity
        // saving time, since once the abr appears you have to be quick
        address tokenIn = token_addresses[0];
        address tokenOut = token_addresses[1];

        // msg.sender must approve the following transfer

        // Transfer the specified amount of DAI to this contract.
        TransferHelper.safeTransferFrom(
            tokenIn,
            msg.sender,
            address(this),
            _amountIn
        );

        // Approve the router to spend DAI.
        TransferHelper.safeApprove(tokenIn, address(swapRouter), _amountIn);

        // Naively set amountOutMinimum to 0.
        // In production, use an oracle or other data source to choose
        // a safer value for amountOutMinimum.
        // We also set the sqrtPriceLimitx96 to be 0 to ensure we swap
        // our exact input amount.
        ISwapRouter.ExactInputSingleParams memory params = ISwapRouter
            .ExactInputSingleParams({
                tokenIn: tokenIn,
                tokenOut: tokenOut,
                fee: poolFee,
                recipient: msg.sender,
                deadline: block.timestamp,
                amountIn: _amountIn,
                // we are setting to zero, but this is a significant risk in production. For a real deployment, this value should be calculated using our SDK or an onchain price oracle - this helps protect against getting an unusually bad price for a trade due to a front running sandwich or another type of price manipulation
                amountOutMinimum: 0,
                //  We set this to zero - which makes this parameter inactive. In production, this value can be used to set the limit for the price the swap will push the pool to, which can help protect against price impact or for setting up logic in a variety of price-relevant mechanisms.
                sqrtPriceLimitX96: 0 
            });

        // The call to `exactInputSingle` executes the swap.
        amountOut = swapRouter.exactInputSingle(params);
    }
}
