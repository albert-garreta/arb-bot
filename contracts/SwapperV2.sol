// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./uniswap-v2/IUniswapV2Router02.sol";
import "../interfaces/ISwapper.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

//TODO: Deprecated: remove and put the swapper test in test_actor

contract SwapperV2 is ISwapper {
    IUniswapV2Router02[] internal swapRouters;

    constructor(address[] memory _swapRouterAddresses) {
        for (uint256 i = 0; i < _swapRouterAddresses.length; i++) {
            swapRouters.push(IUniswapV2Router02(_swapRouterAddresses[i]));
        }
    }

    function swapExactTokensForTokens(
        address _tokenInAddress,
        address _tokenOutAddress,
        uint256 _amountIn,
        uint256 _minAmountOut,
        uint256 _routerIndex,
        address _beneficiaryAddress
    ) public returns (uint256[] memory) {
        // No need to do this step in the second swap of the
        // twoHorpArbitrage function

        IERC20 tokenIn = IERC20(_tokenInAddress);
        tokenIn.transferFrom(_beneficiaryAddress, address(this), _amountIn);
        tokenIn.approve(address(swapRouters[_routerIndex]), _amountIn);

        // require(
        //     tokenIn.allowance(
        //         address(this),
        //         address(swapRouters[_routerIndex])
        //     ) == _amountIn
        // );
        // require(tokenIn.balanceOf(_whoToTransferFrom) == _amountIn);

        address[] memory path = new address[](2);
        path[0] = _tokenInAddress;
        path[1] = _tokenOutAddress;

        uint256[] memory amounts = swapRouters[_routerIndex]
            .swapExactTokensForTokens(
                _amountIn,
                _minAmountOut, // min amount out
                path,
                _beneficiaryAddress,
                block.timestamp
            );

        return amounts;
    }
}
