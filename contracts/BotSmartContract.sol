// SPDX-License-Identifier: Apache

pragma solidity ^0.8.0;

import "../interfaces/IUniswapV2Router02.sol";
import "../interfaces/IUniswapV2Pair.sol";
import "../interfaces/IUniswapV2Factory.sol";
import "../interfaces/IUniswapV2Callee.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract BotSmartContract is Ownable, IUniswapV2Callee {
    IERC20[2] public tokens;
    IUniswapV2Factory[2] public factories;
    IUniswapV2Router02[2] public routers;
    IUniswapV2Pair[2] public pairTkns;

    // TODO: why call it CallbackData?
    struct CallbackData {
        address[] tokenAddresses;
        address[] factoryAddresses;
        address[] routerAddresses;
        uint256 amountTkn1ToBorrow;
        uint8 buyDexIndex;
        uint8 sellDexIndex;
        bool[] orderReversions;
        uint256 buyDexFee;
    }

    event LogBalancesAndDebts(
        uint256 indexed contractBalToken0,
        uint256 indexed actualAmountTkn0ToReturn
    );

    // constructor(
    //     address[] memory _routerAddresses,
    //     address[] memory _factoryAddresses,
    //     address[] memory _tokenAddresses
    // ) {
    //     addRoutersAndFactories(_routerAddresses, _factoryAddresses);
    //     addTokens(_tokenAddresses);
    // }
    //
    // function addRoutersAndFactories(
    //     address[] memory _routerAddresses,
    //     address[] memory _factoryAddresses
    // ) public onlyOwner {
    //     for (uint256 i = 0; i < _routerAddresses.length; i++) {
    //         if (
    //             checkIfAddressAldeadyRegistered(
    //                 _routerAddresses[i],
    //                 registeredRouterAddresses
    //             )
    //         ) {
    //             addressToRouter[_routerAddresses[i]] = IUniswapV2Router02(
    //                 _routerAddresses[i]
    //             );
    //             addressToFactory[_factoryAddresses[i]] = IUniswapV2Router02(
    //                 _factoryAddresses[i]
    //             );
    //             registeredRouterAddresses.push(_routerAddresses[i]);
    //             registeredFactoryAddresses.push(_factoryAddresses[i]);
    //         }
    //     }
    // }
    //
    // function addTokens(address[] memory _tokenAddresses) public onlyOwner {
    //     for (uint256 i = 0; i < _tokenAddresses.length; i++) {
    //         if (
    //             checkIfAddressAldeadyRegistered(
    //                 _tokenAddresses[i],
    //                 registeredTokenAddresses
    //             )
    //         ) {
    //             tokens[_routerAddresses[i]] = IUniswapV2Router02(
    //                 _routerAddresses[i]
    //             );
    //             registeredTokenAddresses.push(_tokenAddresses);
    //         }
    //     }
    // }
    //
    // function checkIfAddressAldeadyRegistered(
    //     address _address,
    //     address[] memory registeredAddresses
    // ) public view returns (bool) {
    //     bool registered = false;
    //     for (uint256 i = 0; i < registeredAddresses.length; i++) {
    //         if (registeredAddresses[i] == _address) {
    //             registered = true;
    //         }
    //     }
    //     return registered;
    // }

    function requestFlashLoanAndAct(CallbackData memory _data) public {
        bytes memory params = abi.encode(_data);
        // require(false, 'hello');
        updateCurrentContracts(_data);
        _data.orderReversions[_data.buyDexIndex]
            ? actWithOrderReversed(
                _data.amountTkn1ToBorrow,
                _data.buyDexIndex,
                params
            )
            : actWithExpectedOrder(
                _data.amountTkn1ToBorrow,
                _data.buyDexIndex,
                params
            );
        // sendAllFundsToOwner(msg.sender);
    }

    function updateCurrentContracts(CallbackData memory _data) internal {
        // IERC20[] tokens = new IERC20[]();
        // IUniswapV2Factory[] factories = new IUniswapV2Factory[]();
        // IUniswapV2Router02[] routers = new IUniswapV2Router02[]();
        // pairs = new IUniswapV2Pair[]();

        for (uint8 i = 0; i < 2; i++) {
            tokens[i] = IERC20(_data.tokenAddresses[i]);
            factories[i] = IUniswapV2Factory(_data.factoryAddresses[i]);
            routers[i] = IUniswapV2Router02(_data.routerAddresses[0]);
            pairTkns[i] = IUniswapV2Pair(
                IUniswapV2Factory(_data.factoryAddresses[i]).getPair(
                    _data.tokenAddresses[0],
                    _data.tokenAddresses[1]
                )
            );
        }
    }

    function actWithExpectedOrder(
        uint256 _amountTkn1ToBorrow,
        uint256 _buyDexIndex,
        bytes memory _params
    ) internal {
        pairTkns[_buyDexIndex].swap(
            0, // amount0Out
            _amountTkn1ToBorrow, // amount1Out
            address(this), // sender
            _params
        );
    }

    function actWithOrderReversed(
        uint256 _amountTkn1ToBorrow,
        uint256 _buyDexIndex,
        bytes memory _params
    ) internal {
        pairTkns[_buyDexIndex].swap(
            _amountTkn1ToBorrow, // amount0Out
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
        normalSwap(_amount1, data);
        uint256 actualAmountTkn0ToReturn = computeActualAmountTkn0ToReturn(
            data.amountTkn1ToBorrow,
            data
        );
        emit LogBalancesAndDebts(
            tokens[0].balanceOf(address(this)),
            actualAmountTkn0ToReturn
        );
        uniswapV2CallCheckPostRequisites(actualAmountTkn0ToReturn);
        returnFundsToPair(actualAmountTkn0ToReturn, data.buyDexIndex);
    }

    function normalSwap(uint256 _amountBorrowed, CallbackData memory _data)
        public
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
    }

    function arrangeAmounts(
        CallbackData memory _data,
        uint256 _amount0,
        uint256 _amount1
    ) internal pure returns (uint256, uint256) {
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
            pairTkns[_data.buyDexIndex],
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
            address(pairTkns[_buyDexIndex]),
            expectedAmountTkn0ToReturn + 100
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
        (uint256 reserveTkn0, uint256 reserveTkn1, ) = _pair.getReserves();
        return
            _orderReversed
                ? (reserveTkn1, reserveTkn0)
                : (reserveTkn0, reserveTkn1);
    }

    function uniswapV2CallCheckPreRequisites(
        address _sender,
        CallbackData memory _data
    ) public view {
        require(_sender == address(this), "Not from this contract");
        require(
            msg.sender ==
                factories[_data.buyDexIndex].getPair(
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
        view
    {
        require(
            tokens[0].balanceOf(address(this)) > actualAmountTkn0ToReturn,
            "Not enough token0s to return"
        );
    }
}
