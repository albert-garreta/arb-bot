// SPDX-License-Identifier: Apache 2.0

interface ISwapper {
    function swapExactTokensForTokens(
        address _tokenInAddress,
        address _tokenOutAddress,
        uint256 _amountIn,
        uint256 _minAmountOut
    ) external returns (uint256);
}
