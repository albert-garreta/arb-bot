// SPDX-License-Identifier: Apache

pragma solidity ^0.8.0;

import "../interfaces/IUniswapV2Router02.sol";
import "../interfaces/IUniswapV2Pair.sol";
import "../interfaces/IUniswapV2Callee.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract ActorV2 is Ownable, IUniswapV2Callee {
    IUniswapV2Router02[] internal routers;
    IUniswapV2Pair public pair;

    constructor(address[] memory _routerAddresses, address _pairAddress) {
        for (uint8 i = 0; i < _routerAddresses.length; i++) {
            routers.push(IUniswapV2Router02(_routerAddresses[i]));
        }
        pair = IUniswapV2Pair(_pairAddresses);
    }

    function requestFlashLoanAndAct(
        address[] memory _tokenAddresses,
        uint256[] memory amounts,
        uint8 buyingDexIndex,
        uint8 sellingDexIndex
    ) public onlyOwner {
        address receiverAddress = address(this);
        bytes memory params = abi.encode(uint8(sellingDexIndex));

        // just for testing purposes
        // TODO: delete or skip in production
        for (uint256 i = 0; i < amounts.length; i++) {
            IERC20 token = IERC20(_tokenAddresses[i]);
            preLoanBalances.push(token.balanceOf(address(this)));
        }

        pair.swap(amounts[0], amounts[1], address(this), params);
    }

    function uniswapV2Call(
        address sender,
        uint256 amount0,
        uint256 amount1,
        bytes calldata data
    ) {
        address[] memory path = new address[](2);
        uint256 amountToken;
        uint256 amountETH;

        address token0 = IUniswapV2Pair(msg.sender).token0(); // fetch the address of token0
        address token1 = IUniswapV2Pair(msg.sender).token1(); // fetch the address of token1
        require(
            msg.sender == IUniswapV2Factory(factoryV2).getPair(token0, token1)
        ); // ensure that msg.sender is a V2 pair
        // rest of the function goes here!


        (uint8 sellDexIndex, uint256 priceTkn0Tkn1) = abi.decode(
            params,
            (uint8, uint256)
        );

        uint256[] memory amountsOut = swapExactTokensForTokens(
            address(token1),
            address(token0),
            amount1,
            0, // min amount out
            sellDexIndex
        );

        returnFunds();
    }


    function swapExactTokensForTokens(
        address _tokenInAddress,
        address _tokenOutAddress,
        uint256 _amountIn,
        uint256 _minAmountOut,
        uint256 _dexIndex
    ) public returns (uint256[] memory) {
        IERC20 tokenIn = IERC20(_tokenInAddress);
        tokenIn.approve(address(swapRouters[_dexIndex]), _amountIn);

        address[] memory path = new address[](2);
        path[0] = _tokenInAddress;
        path[1] = _tokenOutAddress;

        uint256[] memory amounts = swapRouters[_dexIndex]
            .swapExactTokensForTokens(
                _amountIn,
                _minAmountOut,
                path,
                address(this),
                block.timestamp
            );
        return amounts;
    }

    function returnFunds() internal {
        require(amount0 == 0 || amount1 == 0); // this strategy is unidirectional
        path[0] = amount0 == 0 ? token0 : token1;
        path[1] = amount0 == 0 ? token1 : token0;
        amountToken = token0 == address(WETH) ? amount1 : amount0;
        amountETH = token0 == address(WETH) ? amount0 : amount1;

        require(path[0] == address(WETH) || path[1] == address(WETH)); // this strategy only works with a V2 WETH pair
        IERC20 token = IERC20(path[0] == address(WETH) ? path[1] : path[0]);
        IUniswapV1Exchange exchangeV1 = IUniswapV1Exchange(
            factoryV1.getExchange(address(token))
        ); // get V1 exchange

        if (amountToken > 0) {
            uint256 minETH = abi.decode(data, (uint256)); // slippage parameter for V1, passed in by caller
            token.approve(address(exchangeV1), amountToken);
            uint256 amountReceived = exchangeV1.tokenToEthSwapInput(
                amountToken,
                minETH,
                uint256(-1)
            );
            uint256 amountRequired = UniswapV2Library.getAmountsIn(
                factory,
                amountToken,
                path
            )[0];
            assert(amountReceived > amountRequired); // fail if we didn't get enough ETH back to repay our flash loan
            WETH.deposit{value: amountRequired}();
            assert(WETH.transfer(msg.sender, amountRequired)); // return WETH to V2 pair
            (bool success, ) = sender.call{
                value: amountReceived - amountRequired
            }(new bytes(0)); // keep the rest! (ETH)
            assert(success);
        } else {
            uint256 minTokens = abi.decode(data, (uint256)); // slippage parameter for V1, passed in by caller
            WETH.withdraw(amountETH);
            uint256 amountReceived = exchangeV1.ethToTokenSwapInput{
                value: amountETH
            }(minTokens, uint256(-1));
            uint256 amountRequired = UniswapV2Library.getAmountsIn(
                factory,
                amountETH,
                path
            )[0];
            assert(amountReceived > amountRequired); // fail if we didn't get enough tokens back to repay our flash loan
            assert(token.transfer(msg.sender, amountRequired)); // return tokens to V2 pair
            assert(token.transfer(sender, amountReceived - amountRequired)); // keep the rest! (tokens)
        }
    }
}
