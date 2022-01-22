// SPDX-License-Identifier: Apache 2.0

pragma solidity ^0.8.0;

interface ISwapper {
    function swapExactTokensForTokens(
        address _tokenInAddress,
        address _tokenOutAddress,
        uint256 _amountIn,
        uint256 _minAmountOut,
        uint256 _routerIndex,
        address _beneficiaryAddress
    ) external returns (uint256[] memory);
}
