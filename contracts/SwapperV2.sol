// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./uniswap-v2/IUniswapV2Router02.sol";
import "../interfaces/ISwapper.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract SwapperV2 is ISwapper {
    IUniswapV2Router02 public immutable swapRouter;

    constructor(address _swapRouterAddress) {
        swapRouter = IUniswapV2Router02(_swapRouterAddress);
    }

    function swapExactTokensForTokens(
        address _tokenInAddress,
        address _tokenOutAddress,
        uint256 _amountIn,
        uint256 _minAmountOut
    ) public returns (uint256) {
        IERC20(_tokenInAddress).transferFrom(
            address(msg.sender),
            address(this),
            _amountIn
        );

        IERC20(_tokenInAddress).approve(address(swapRouter), _amountIn);

        address[] memory path = new address[](2);
        path[0] = _tokenInAddress;
        path[1] = _tokenOutAddress;

        uint256[] memory amounts = swapRouter.swapExactTokensForTokens(
            _amountIn,
            _minAmountOut, // min amount out
            path,
            address(msg.sender),
            block.timestamp
        );

        return amounts[1];
    }
}
