// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./uniswap-v2/IUniswapV2Router02.sol";
import "../interfaces/ISwapper.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract SwapperV2 is ISwapper {
    IUniswapV2Router02[] internal swapRouters;

    constructor(address[] memory _swapRouterAddresses) {
        for (uint256 i = 0; i < _swapRouterAddresses.length; i++) {
            swapRouters.push(IUniswapV2Router02(_swapRouterAddresses[i]));
        }
    }

    function twoHopArbitrage(
        address _tokenInAddress,
        address _tokenOutAddress,
        uint256 _amountIn,
        uint256 _minAmountOut0,
        uint256 _minAmountOut1,
        uint256 _router0Index,
        uint256 _router1Index
    ) internal returns (uint256) {
        // Swap tokenIn for tokenOut in router0, then swap tokenOut for tokenIn in router1
        uint256 amountOutFirstSwap = swapExactTokensForTokens(
            _tokenInAddress,
            _tokenOutAddress,
            _amountIn,
            _minAmountOut0,
            _router0Index,
            true
        );

        uint256 amountOutFinal = swapExactTokensForTokens(
            _tokenOutAddress,
            _tokenInAddress,
            amountOutFirstSwap,
            _minAmountOut1,
            _router1Index,
            false
        );

        return amountOutFinal;
    }

    function swapExactTokensForTokens(
        address _tokenInAddress,
        address _tokenOutAddress,
        uint256 _amountIn,
        uint256 _minAmountOut,
        uint256 _routerIndex,
        bool _doTransferFrom
    ) internal returns (uint256) {
        // No need to do this step in the second swap of the
        // twoHorpArbitrage function
        if (_doTransferFrom) {
            IERC20(_tokenInAddress).transferFrom(
                address(msg.sender),
                address(this),
                _amountIn
            );
        }

        IERC20(_tokenInAddress).approve(
            address(swapRouters[_routerIndex]),
            _amountIn
        );

        address[] memory path = new address[](2);
        path[0] = _tokenInAddress;
        path[1] = _tokenOutAddress;

        uint256[] memory amounts = swapRouters[_routerIndex]
            .swapExactTokensForTokens(
                _amountIn,
                _minAmountOut, // min amount out
                path,
                address(msg.sender),
                block.timestamp
            );

        return amounts[1];
    }
}
