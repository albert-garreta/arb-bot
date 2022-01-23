// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

// import "@aave/contracts/interfaces/ILendingPoolAddressesProvider.sol";
// import "@aave/contracts/interfaces/ILendingPool.sol";
// import "@aave/contracts/flashloan/base/FlashLoanReceiverBase.sol";

import "./aave-protocol-v2/ILendingPoolAddressesProvider.sol";
import "./aave-protocol-v2/ILendingPool.sol";
import "./aave-protocol-v2//FlashLoanReceiverBase.sol";

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./uniswap-v2/IUniswapV2Router02.sol";

/** 
    !!!
    Never keep funds permanently on your FlashLoanReceiverBase contract as they could be 
    exposed to a 'griefing' attack, where the stored funds are used by an attacker.
    !!!
 */
contract Actor is FlashLoanReceiverBase, Ownable {
    // SwapperV3 public swapper;
    IUniswapV2Router02[] internal swapRouters;

    // This is currently used only for testing purposes to check
    // the loan ammount received during the flash loan
    uint256[] public amountsLoanReceived;
    uint256[] public preLoanBalances;
    // Used only for testing.
    // TODO: delete for production?
    // TODO: we know this will be a length-2 array of length-2 arrays:
    // specify for efficiency
    uint256[] public swapReturns;

    constructor(
        address[] memory _swapRouterAddresses,
        address _lendingPoolAddressesProviderAddress
    )
        FlashLoanReceiverBase(
            ILendingPoolAddressesProvider(_lendingPoolAddressesProviderAddress)
        )
    {
        for (uint256 i = 0; i < _swapRouterAddresses.length; i++) {
            swapRouters.push(IUniswapV2Router02(_swapRouterAddresses[i]));
        }
    }

    // REMEMBER:
    // If you flash 100 AAVE, the 9bps fee is 0.09 AAVE
    // If you flash 500,000 DAI, the 9bps fee is 450 DAI
    // If you flash 10,000 LINK, the 9bps fee is 45 LINK
    // All of these fees need to be sitting ON THIS CONTRACT
    // before you execute this batch flash.
    function requestFlashLoanAndAct(
        address[] memory _tokenAddresses,
        uint256[] memory amounts,
        uint8 minDexIndex
    ) public onlyOwner {
        // TODO: Does the onlyOwner here prevent grieffing attacks?
        address receiverAddress = address(this);
        uint256[] memory modes = new uint256[](amounts.length);
        // TODO: is it faster if I encode in python?
        bytes memory params = abi.encode(uint8(minDexIndex));

        for (uint256 i = 0; i < amounts.length; i++) {
            // 0 = no debt, 1 = stable, 2 = variable
            modes[i] = 0;
        }

        // just for testing purposes
        // TODO: delete or skip in production
        for (uint256 i = 0; i < amounts.length; i++) {
            IERC20 token = IERC20(_tokenAddresses[i]);
            preLoanBalances.push(token.balanceOf(address(this)));
        }

        LENDING_POOL.flashLoan(
            receiverAddress,
            _tokenAddresses,
            amounts,
            modes,
            address(this), //onBehalfOf
            params,
            0 // referralCode
        );

        withdrawAllFunds(_tokenAddresses);
    }

    // This function is called after your contract has received the flash loaned amount
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        //
        // This contract now has the funds requested.
        // Your logic goes here.
        //

        // TODO: This should be deleted or avoided for production.
        // Currently we use it for testing purposes
        for (uint256 i = 0; i < amounts.length; i++) {
            amountsLoanReceived.push(
                IERC20(assets[i]).balanceOf(initiator) - preLoanBalances[i]
            );
        }

        uint8 minDexIndex = abi.decode(params, (uint8));
        uint8 maxDexIndex = 1;
        if (minDexIndex == 1) {
            maxDexIndex = 0;
        }

        twoHopArbitrage(
            assets[0],
            assets[1],
            amounts[0],
            0, // minAmountOut0,
            0, // minAmountOut1,
            minDexIndex, // router0Index
            maxDexIndex // router1Index
        );

        // At the end of your logic above, this contract owes
        // the flashloaned amounts + premiums.
        // Therefore ensure your contract has enough to repay
        // these amounts

        // Approve the LendingPool contract allowance to *pull* the owed amount
        for (uint256 i = 0; i < assets.length; i++) {
            uint256 amountOwing = amounts[i] + premiums[i];
            IERC20(assets[i]).approve(address(LENDING_POOL), amountOwing);
        }

        return true;
    }

    function twoHopArbitrage(
        address _token0Address,
        address _token1Address,
        uint256 _amountIn,
        uint256 _minAmountOut0,
        uint256 _minAmountOut1,
        uint8 _router0Index,
        uint8 _router1Index
    ) public {
        // tx = _token0.approve(_swapper.address, _amount_in, {"from": account})
        // tx.wait(1)

        uint256[] memory amountsOut = swapExactTokensForTokens(
            _token0Address,
            _token1Address,
            _amountIn,
            _minAmountOut0,
            _router0Index
        );

        // Only for testing
        swapReturns.push(amountsOut[1]);
        // _token1.approve(_swapper.address, amount_out_first_swap, {"from": account})

        amountsOut = swapExactTokensForTokens(
            _token1Address,
            _token0Address,
            amountsOut[1],
            _minAmountOut1,
            _router1Index
        );
        // Only for testing
        swapReturns.push(amountsOut[1]);
    }

    function withdrawAllFunds(address[] memory _tokenAddresses)
        public
        onlyOwner
    {
        // TODO: send gains to user. Important for security
        for (uint256 i = 0; i < _tokenAddresses.length; i++) {
            // TODO: not loop over all list, but only those where the balance is >0
            IERC20 token = IERC20(_tokenAddresses[i]);
            token.transfer(msg.sender, token.balanceOf(address(this)));
        }
    }

    function swapExactTokensForTokens(
        address _tokenInAddress,
        address _tokenOutAddress,
        uint256 _amountIn,
        uint256 _minAmountOut,
        uint256 _routerIndex
    ) public returns (uint256[] memory) {
        // No need to do this step in the second swap of the
        // twoHorpArbitrage function

        IERC20 tokenIn = IERC20(_tokenInAddress);
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
                address(this),
                block.timestamp
            );

        return amounts;
    }
}
