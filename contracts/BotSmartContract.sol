// SPDX-License-Identifier: Apache

pragma solidity ^0.8.0;

import "../interfaces/IUniswapV2Router02.sol";
import "../interfaces/IUniswapV2Pair.sol";
import "../interfaces/IUniswapV2Factory.sol";
import "../interfaces/IUniswapV2Callee.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract BotSmartContract is Ownable, IUniswapV2Callee {
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

    event LogBalancesAndDebts(
        uint256 indexed contractBalToken0,
        uint256 indexed expectedAmountTkn0ToReturn,
        uint256 indexed actualAmountTkn0ToReturn
    );

    constructor(
        address[] memory _routerAddresses,
        address[] memory _factoryAddresses,
        address[] memory _tokenAddresses
    ) {
        modifyStateVariables(
            _routerAddresses,
            _factoryAddresses,
            _tokenAddresses
        );
    }

    function modifyStateVariables(
        address[] memory _routerAddresses,
        address[] memory _factoryAddresses,
        address[] memory _tokenAddresses
    ) public onlyOwner {
        routers = new IUniswapV2Router02[](0);
        factories = new IUniswapV2Factory[](0);
        pairs = new IUniswapV2Pair[](0);
        tokens = new IERC20[](0);

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

    //TODO: Is this necessary?
    receive() external payable {}

    function requestFlashLoanAndAct(CallbackData memory _data) public {
        bytes memory params = abi.encode(_data);
        _data.orderReversions[_data.buyDexIndex]
            ? actWithOrderReversed(_data, params)
            : actWithExpectedOrder(_data, params);
        // sendAllFundsToOwner(msg.sender);
    }

    function actWithExpectedOrder(
        CallbackData memory _data,
        bytes memory _params
    ) internal {
        pairs[_data.buyDexIndex].swap(
            0, // amount0Out
            _data.amountTkn1ToBorrow, // amount1Out
            address(this), // sender
            _params
        );
    }

    function actWithOrderReversed(
        CallbackData memory _data,
        bytes memory _params
    ) internal {
        pairs[_data.buyDexIndex].swap(
            _data.amountTkn1ToBorrow, // amount0Out
            0, // amount1Out
            address(this), // sender
            _params
        );
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
        CallbackData memory data = abi.decode(_data, (CallbackData));

        (_amount0, _amount1) = arrangeAmounts(data, _amount0, _amount1);
        uniswapV2CallCheckPreRequisites(_sender, data);
        uint256 amountTkn0Out = normalSwap(_amount1, data);
        uint256 actualAmountTkn0ToReturn = computeActualAmountTkn0ToReturn(
            data.amountTkn1ToBorrow,
            data
        );
        emit LogBalancesAndDebts(
            tokens[0].balanceOf(address(this)),
            data.expectedAmountTkn0ToReturn,
            actualAmountTkn0ToReturn
        );
        uniswapV2CallCheckPostRequisites(actualAmountTkn0ToReturn);
        returnFundsToPair(actualAmountTkn0ToReturn, data.buyDexIndex);
    }

    function normalSwap(uint256 _amountBorrowed, CallbackData memory _data)
        public
        returns (uint256)
    {
        tokens[1].approve(
            address(routers[_data.sellDexIndex]),
            _amountBorrowed
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
        return amounts[0];
    }

    function arrangeAmounts(
        CallbackData memory _data,
        uint256 _amount0,
        uint256 _amount1
    ) internal returns (uint256, uint256) {
        bool reversedOrder = _data.orderReversions[_data.buyDexIndex];
        return reversedOrder ? (_amount1, _amount0) : (_amount0, _amount1);
    }

    function computeActualAmountTkn0ToReturn(
        uint256 _amountTkn1Borrwed,
        CallbackData memory _data
    ) internal view returns (uint256) {
        // Due to price variability, the expected amount of Tkn0 to return may be different than the one computed
        // before interacting with the smartcontract. Hence we recalculate it here
        (uint256 reserveTkn0, uint256 reserveTkn1) = getOrderedReserves(
            pairs[_data.buyDexIndex],
            _data.orderReversions[_data.buyDexIndex]
        );
        return
            getAmountIn(
                _amountTkn1Borrwed, //amountOut
                reserveTkn0, // reserveIn
                reserveTkn1, // reserveOut
                _data.buyDexFee
            );
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

    function returnFundsToPair(
        uint256 expectedAmountTkn0ToReturn,
        uint8 _buyDexIndex
    ) internal {
        tokens[0].transfer(
            address(pairs[_buyDexIndex]),
            expectedAmountTkn0ToReturn
        );
    }

    function sendAllFundsToOwner() public onlyOwner {
        tokens[0].transfer(msg.sender, tokens[0].balanceOf(address(this)));
    }

    function getOrderedReserves(IUniswapV2Pair _pair, bool _orderReversed)
        internal
        view
        returns (uint256, uint256)
    {
        // The method getReserves() from UniswapPairs need not return the desired order of reserves
        (
            uint256 reserveTkn0,
            uint256 reserveTkn1,
            uint32 blockTimestampLast
        ) = _pair.getReserves();
        return
            _orderReversed
                ? (reserveTkn1, reserveTkn0)
                : (reserveTkn0, reserveTkn1);
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

    function uniswapV2CallCheckPostRequisites(uint256 actualAmountTkn0ToReturn)
        public
    {
        require(
            tokens[0].balanceOf(address(this)) > actualAmountTkn0ToReturn,
            "Not enough token0s to return"
        );
    }
}
