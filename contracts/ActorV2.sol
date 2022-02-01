// SPDX-License-Identifier: Apache

pragma solidity ^0.8.0;

import "../interfaces/IUniswapV2Router02.sol";
import "../interfaces/IUniswapV2Pair.sol";
import "../interfaces/IUniswapV2Factory.sol";
import "../interfaces/IUniswapV2Callee.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract ActorV2 is Ownable, IUniswapV2Callee {
    IUniswapV2Router02[] public routers;
    IUniswapV2Factory[] public factories;
    IUniswapV2Pair[] public pairs;
    IERC20[] public tokens;

    // TODO: why call it CallbackData?
    struct CallbackData {
        address[] tokenAddresses;
        uint256 amountTkn1ToBorrow;
        uint256 expectedAmountTkn0ToReturn;
        uint8 buyDexIndex;
        uint8 sellDexIndex;
        bool[] orderReversions;
        uint256 buyDexFee;
    }

    CallbackData internal data;

    event Log(
        uint256 indexed contractBalToken0,
        uint256 indexed expectedAmountTkn0ToReturn,
        uint256 indexed actualAmountTkn0ToReturn
    );

    event Log2(uint256 amountTkn1ToBorrow);

    constructor(
        address[] memory _routerAddresses,
        address[] memory _factoryAddresses,
        address[] memory _tokenAddresses
    ) {
        for (uint8 i = 0; i < _routerAddresses.length; i++) {
            routers.push(IUniswapV2Router02(_routerAddresses[i]));
            factories.push(IUniswapV2Factory(_factoryAddresses[i]));
            tokens.push(IERC20(_tokenAddresses[i]));
            pairs.push(
                IUniswapV2Pair(
                    factories[i].getPair(_tokenAddresses[0], _tokenAddresses[1])
                )
            );
        }
    }

    //TODO: what is this for?
    receive() external payable {}

    function requestFlashLoanAndAct(CallbackData memory _data) public {
        bytes memory params = abi.encode(_data);
        // (uint112 _reserve0, uint112 _reserve1, ) = pairs[_data.buyDexIndex]
        //     .getReserves();

        if (!_data.orderReversions[_data.buyDexIndex]) {
            require(
                address(tokens[1]) == pairs[_data.buyDexIndex].token1(),
                "Incorrect token orders"
            );
            emit Log2(_data.amountTkn1ToBorrow);
            pairs[_data.buyDexIndex].swap(
                0,
                _data.amountTkn1ToBorrow,
                address(this),
                params
            );
        } else {
            require(
                address(tokens[1]) == pairs[_data.buyDexIndex].token0(),
                "Incorrect token orders"
            );
            pairs[_data.buyDexIndex].swap(
                _data.amountTkn1ToBorrow,
                0,
                address(this),
                params
            );
        }
        sendAllFundsToOwner(msg.sender);
    }

    function pancakeCall(
        // The name of the callback function is not the same on every dex.
        // TODO: Can I set up the fallback function of this contract to manage this, instead of
        // adding a redirection function as this one per every different callback function name?
        address _sender,
        uint256 _amount0,
        uint256 _amount1,
        bytes calldata _data
    ) public {
        uniswapV2Call(_sender, _amount0, _amount1, _data);
    }

    function uniswapV2Call(
        address _sender,
        uint256 _amount0,
        uint256 _amount1,
        bytes calldata _data
    ) public {
        data = abi.decode(_data, (CallbackData));

        bool reversedOrder = data.orderReversions[data.buyDexIndex];
        if (reversedOrder) {
            (_amount0, _amount1) = (_amount1, _amount0);
        }

        uniswapV2CallCheckPreRequisites(_sender, data);
        uint256 amountTkn0Out = normalSwap(_amount1, data);

        uint256[] memory balances = new uint256[](2);
        balances[0] = tokens[0].balanceOf(address(this));
        balances[1] = tokens[1].balanceOf(address(this));

        emit Log(balances[0], data.expectedAmountTkn0ToReturn, 0);
        // //TODO: check debug tools in brownie
        uint256 actualAmountTkn0ToReturn = computeActualAmountTkn0ToReturn(
            data.amountTkn1ToBorrow,
            data
        );
        emit Log(
            balances[0],
            data.expectedAmountTkn0ToReturn,
            actualAmountTkn0ToReturn
        );
        uniswapV2CallCheckPostRequisites(
            amountTkn0Out,
            actualAmountTkn0ToReturn
        );

        returnFundsToPair(actualAmountTkn0ToReturn, data.buyDexIndex);
    }

    function uniswapV2CallCheckPreRequisites(
        address _sender,
        CallbackData memory _data
    ) public {
        require(_sender == address(this), "Not from this contract");
        require(
            msg.sender ==
                IUniswapV2Factory(factories[_data.buyDexIndex]).getPair(
                    _data.tokenAddresses[0],
                    _data.tokenAddresses[1]
                )
        ); // ensure that msg.sender is a V2 pair
        require(
            tokens[0].balanceOf(address(this)) == 0,
            "The token0 balance should be 0 here"
        );

        require(
            _data.amountTkn1ToBorrow == tokens[1].balanceOf(address(this)),
            "Not enough token1 received"
        );
    }

    function uniswapV2CallCheckPostRequisites(
        uint256 amountTkn0Out,
        uint256 actualAmountTkn0ToReturn
    ) public {
        require(
            amountTkn0Out > actualAmountTkn0ToReturn + 1000000,
            "Non-positive net profit accrued"
        );
        require(
            tokens[0].balanceOf(address(this)) >
                actualAmountTkn0ToReturn + 1000000,
            "Not enough token0s to return"
        );
    }

    function returnFundsToPair(
        uint256 _actualAmountTkn0ToReturn,
        uint8 _buyDexIndex
    ) internal {
        tokens[0].transfer(
            address(pairs[_buyDexIndex]),
            _actualAmountTkn0ToReturn + 1000
        );
        // tokens[0].transfer(
        //     address(pairs[_buyDexIndex]),
        //     tokens[0].balanceOf(address(this))
        // );
        // tokens[1].transfer(
        //     address(pairs[_buyDexIndex]),
        //     tokens[1].balanceOf(address(this))
        // );
        // require(
        //     tokens[0].balanceOf(address(this)) == 0 &&
        //         tokens[1].balanceOf(address(this)) == 0,
        //     "Something went wront while transfering tokens back to the pair"
        // );

        // uint256 balance0 = IERC20(tokens[0]).balanceOf(
        //     address(pairs[_buyDexIndex])
        // );
        // uint256 balance1 = IERC20(tokens[1]).balanceOf(
        //     address(pairs[_buyDexIndex])
        // );
        //
        // uint256 amount0In = balance0 > _reserve0 - _amount0Out
        //     ? balance0 - (_reserve0 - _amount0Out)
        //     : 0;
        // uint256 amount1In = balance1 > _reserve1 - _amount1Out
        //     ? balance1 - (_reserve1 - _amount1Out)
        //     : 0;
        // emit pairSwapEvent(_amount0In, _amount1In, balancesAdjusted);
        //
        // uint256 balance0Adjusted = balance0 * (1000) - 3 * (_amount0In);
        // uint256 balance1Adjusted = balance1 * (1000) - 3 * (_amount1In);
        //
        // balancesAdjusted.push(balance0Adjusted);
        // balancesAdjusted.push(balance1Adjusted);
        // emit pairSwapEvent(_amount0In, _amount1In, balancesAdjusted);
    }

    function sendAllFundsToOwner(address _sender) internal {
        tokens[0].transfer(_sender, tokens[0].balanceOf(_sender));
    }

    function normalSwap(uint256 _amountBorrowed, CallbackData memory _data)
        public
        returns (uint256)
    {
        tokens[1].approve(
            address(routers[_data.sellDexIndex]),
            _amountBorrowed + 100000
        );

        address[] memory path = new address[](2);
        path[0] = _data.tokenAddresses[1];
        path[1] = _data.tokenAddresses[0];

        uint256[] memory amounts = routers[_data.sellDexIndex]
            .swapExactTokensForTokens(
                _amountBorrowed,
                uint256(0),
                path,
                address(this),
                block.timestamp
            );

        require(
            tokens[1].balanceOf(address(this)) == 0,
            "We should have no token1s here"
        );

        return amounts[0];
    }

    function computeActualAmountTkn0ToReturn(
        uint256 _amountTkn1Borrwed,
        CallbackData memory _data
    ) internal view returns (uint256) {
        // Due to price variability, the expected amount of Tkn0 to return may be different than the one computed
        // before interacting with the smartcontract. Hence we recalculate it here
        (uint256 reserveTkn0, uint256 reserveTkn1) = getOrderedReserves(
            pairs[_data.buyDexIndex],
            data.orderReversions[_data.buyDexIndex]
        );

        // careful on the order of reserves here: reserveIn is the reserve of token1 because we are selling
        return
            getAmountIn(
                _amountTkn1Borrwed,
                reserveTkn0,
                reserveTkn1,
                _data.buyDexFee
            );
    }

    function getOrderedReserves(IUniswapV2Pair _pair, bool _orderReversed)
        internal
        view
        returns (uint256, uint256)
    {
        // The method getReserves() from UniswapPairs need not return the desired order of reserves
        // TODO: is the order, however, constant? If not, then I cannot use the attribute order_reversions
        // from CallbackData
        (
            uint256 reserveTkn0,
            uint256 reserveTkn1,
            uint32 blockTimestampLast
        ) = _pair.getReserves();
        if (_orderReversed) {
            return (reserveTkn1, reserveTkn0);
        } else {
            return (reserveTkn0, reserveTkn1);
        }
    }

    // copied from UniswapV2Library
    function getAmountIn(
        uint256 amountOut,
        uint256 reserveIn,
        uint256 reserveOut,
        uint256 fee
    ) internal pure returns (uint256 amountIn) {
        require(amountOut > 0, "UniswapV2Library: INSUFFICIENT_OUTPUT_AMOUNT");
        require(
            reserveIn > 0 && reserveOut > 0,
            "UniswapV2Library: INSUFFICIENT_LIQUIDITY"
        );
        uint256 numerator = reserveIn * amountOut * 1000;
        uint256 denominator = (reserveOut - amountOut) * fee;
        amountIn = (numerator / denominator) + 1;
    }
}
