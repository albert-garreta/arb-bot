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
import "./SwapperV2.sol";

/** 
    !!!
    Never keep funds permanently on your FlashLoanReceiverBase contract as they could be 
    exposed to a 'griefing' attack, where the stored funds are used by an attacker.
    !!!
 */
contract Actor is SwapperV2, FlashLoanReceiverBase, Ownable {
    // SwapperV3 public swapper;

    // This is currently used only for testing purposes to check
    // the loan ammount received during the flash loan
    uint256[] public amountsLoanReceived;
    uint256[] public preLoanBalances;

    constructor(
        address _swap_router_address,
        address _lendingPoolAddressesProviderAddress
    )
        SwapperV2(_swap_router_address)
        FlashLoanReceiverBase(
            ILendingPoolAddressesProvider(_lendingPoolAddressesProviderAddress)
        )
    {}

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
        for (uint256 i = 0; i < amounts.length; i++) {
            amountsLoanReceived.push(
                IERC20(assets[i]).balanceOf(initiator) - preLoanBalances[i]
            );
        }

        swap();
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

    function swap() internal {
        
    }

    // REMEMBER:
    // If you flash 100 AAVE, the 9bps fee is 0.09 AAVE
    // If you flash 500,000 DAI, the 9bps fee is 450 DAI
    // If you flash 10,000 LINK, the 9bps fee is 45 LINK
    // All of these fees need to be sitting ON THIS CONTRACT
    // before you execute this batch flash.
    function requestFlashLoanAndAct(
        address[] memory _tokenAddresses,
        uint256[] memory amounts
    ) public onlyOwner {
        // !!! Does the onlyOwner here prevent grieffing attacks?
        address receiverAddress = address(this);
        uint256[] memory modes = new uint256[](amounts.length);

        for (uint256 i = 0; i < amounts.length; i++) {
            // 0 = no debt, 1 = stable, 2 = variable
            modes[i] = 0;
        }

        address onBehalfOf = address(this);
        bytes memory params = "";
        uint16 referralCode = 0;

        // just for testing purposes
        for (uint256 i = 0; i < amounts.length; i++) {
            IERC20 token = IERC20(_tokenAddresses[i]);
            preLoanBalances.push(token.balanceOf(address(this)));
        }

        LENDING_POOL.flashLoan(
            receiverAddress,
            _tokenAddresses,
            amounts,
            modes,
            onBehalfOf,
            params,
            referralCode
        );

        withdrawAllFunds(_tokenAddresses);
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
}
