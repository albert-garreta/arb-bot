// SPDX-License-Identifier: Apache

pragma solidity ^0.8.0;

import "../interfaces/IUniswapV2Router02.sol";
import "../interfaces/IUniswapV2Pair.sol";
import "../interfaces/IUniswapV2Factory.sol";
import "../interfaces/IUniswapV2Callee.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

struct ArbData {
    address[] tokenAddresses;
    address[] factoryAddresses;
    address[] routerAddresses;
    uint256 amountTkn1ToBorrow;
    uint8 buyDexIndex;
    uint8 sellDexIndex;
    bool[] orderReversions;
    uint256 buyDexFee;
}

contract BotSmartContract is Ownable, IUniswapV2Callee {
    IERC20[2] public tokens;
    IUniswapV2Factory[2] public factories;
    IUniswapV2Router02[2] public routers;
    IUniswapV2Pair[2] public pairTkns;

    // I was getting reentrancy errors from the uniswapV2Call.
    // I put this modifier in the main function requestFlashLoanAndAct to
    // see if this helps
    uint8 private unlocked = 1;
    modifier lock() {
        require(unlocked == 1, "BotSmartContract is Locked");
        unlocked = 0;
        _;
        unlocked = 1;
    }

    receive() external payable {}

    // For debugging purposes: currently not in use
    event LogBalancesAndDebts(
        uint256 indexed contractBalToken0,
        uint256 indexed actualAmountTkn0ToReturn
    );

    function requestFlashLoanAndAct(ArbData memory _data) public lock {
        /*** Main function of the contract.
        - The bot is supposed to call this when it detects an
        arbitrage opportunity
        - It first encodes the _data structure since UniswapV2Pair
        will send it back when calling uniswapV2Call.
        - Then it updates the state variables of the contract.
        - Then it requests the flashloan to the corresponding LP.
        - The function ``continues'' with uniswapV2Call, which is
        called by the LP.
        */
        bytes memory params = abi.encode(_data);
        updateCurrentContracts(_data);
        swap(_data, params);
    }

    function updateCurrentContracts(ArbData memory _data) internal {
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

    function swap(ArbData memory _data, bytes memory params) internal {
        // The parameters of the flashloan change depending on wether the
        // token0 and token1 in the LP match our naming convention or it
        // is switched
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
    }

    function actWithExpectedOrder(
        uint256 _amountTkn1ToBorrow,
        uint256 _buyDexIndex,
        bytes memory _params
    ) internal {
        // Request flashloan
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
        // Request flashloan
        pairTkns[_buyDexIndex].swap(
            _amountTkn1ToBorrow, // amount0Out
            0, // amount1Out
            address(this), // sender
            _params
        );
    }

    /** ----------------------------------------------------------------
    The next functions are called by the LP once it has sent the requested funds.  
    */

    function pancakeCall(
        // The name of the function called by the LP  is not the same on every dex.
        // Originally the name is uniswapV2Call, so we reroute other function names
        // such as pancakeCall to uniswapV2Call
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
        /** Function called by the LP pair once it has sent the requested funds to this contract
        - First it decodes the encoded struct ArbData and it arranges the received funds to
        match our naming conventions.
        - Then it swaps tokens normally in the selling Dex.
        - Then it computes the amount of token0 owned to the LP and sends such amount to the LP. 
         */
        ArbData memory data = abi.decode(_data, (ArbData));
        (_amount0, _amount1) = arrangeAmounts(data, _amount0, _amount1);
        // Avoid these checks for gas savings
        // uniswapV2CallCheckPreRequisites(_sender, data);
        normalSwap(_amount1, data);
        uint256 actualAmountTkn0ToReturn = computeActualAmountTkn0ToReturn(
            data.amountTkn1ToBorrow,
            data
        );
        emit LogBalancesAndDebts(tokens[0].balanceOf(address(this)), actualAmountTkn0ToReturn);
        // Avoid these checks for gas savings
        // uniswapV2CallCheckPostRequisites(actualAmountTkn0ToReturn);
        returnFundsToPair(actualAmountTkn0ToReturn, data.buyDexIndex);
    }

    function normalSwap(uint256 _amountBorrowed, ArbData memory _data) public {
        // Swap the received token1's by token0's on the selling Dex
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

    function computeActualAmountTkn0ToReturn(
        uint256 _amountTkn1Borrwed,
        ArbData memory _data
    ) internal view returns (uint256) {
        (uint256 reserveTkn0, uint256 reserveTkn1) = getOrderedReserves(
            pairTkns[_data.buyDexIndex],
            _data.orderReversions[_data.buyDexIndex]
        );
        return
            getAmountIn(
                _amountTkn1Borrwed, //amountOut
                reserveTkn0, // reserve0
                reserveTkn1, // reserve1
                _data.buyDexFee
            );
    }

    // copied from UniswapV2Library
    function getAmountIn(
        uint256 amountOut,
        uint256 reserve0,
        uint256 reserve1,
        /// @notice Explain to an end user what this does
        /// @dev Explain to a developer any extra details
        /// @param Documents a parameter just like in doxygen (must be followed by parameter name),
        uint256 fee
    ) internal pure returns (uint256 amountIn) {
        require(amountOut > 0, "UniswapV2Library: INSUFFICIENT_OUTPUT_AMOUNT");
        require(
            reserve0 > 0 && reserve1 > 0,
            "UniswapV2Library: INSUFFICIENT_LIQUIDITY"
        );
        uint256 numerator = reserve0 * amountOut * 1000;
        uint256 denominator = (reserve1 - amountOut) * fee;
        amountIn = (numerator / denominator) + 1;
    }

    function returnFundsToPair(
        uint256 expectedAmountTkn0ToReturn,
        uint8 _buyDexIndex
    ) internal {
        tokens[0].transfer(
            address(pairTkns[_buyDexIndex]),
            expectedAmountTkn0ToReturn + 1
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

    function arrangeAmounts(
        ArbData memory _data,
        uint256 _amount0,
        uint256 _amount1
    ) internal pure returns (uint256, uint256) {
        // Helper to match the correct naming of token0 and token1 in the LP
        bool reversedOrder = _data.orderReversions[_data.buyDexIndex];
        return reversedOrder ? (_amount1, _amount0) : (_amount0, _amount1);
    }

    function uniswapV2CallCheckPostRequisites(uint256 actualAmountTkn0ToReturn)
        public
        view
    {
        // Currently not in use: checks that we have enough token0's to return to the
        // LP pair at the end of the UniswapV2Call function.
        require(
            tokens[0].balanceOf(address(this)) > actualAmountTkn0ToReturn,
            "Not enough token0s to return"
        );
    }
}
