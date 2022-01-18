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
import "./SwapperV3.sol";

/** 
    !!!
    Never keep funds permanently on your FlashLoanReceiverBase contract as they could be 
    exposed to a 'griefing' attack, where the stored funds are used by an attacker.
    !!!
 */
contract Actor is SwapperV3, FlashLoanReceiverBase {
    // SwapperV3 public swapper;

    constructor(
        address[] memory _token_addresses,
        address _swap_router_address,
        address _lendingPoolAddressesProviderAddress
    )
        SwapperV3(_swap_router_address)
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

        // At the end of your logic above, this contract owes
        // the flashloaned amounts + premiums.
        // Therefore ensure your contract has enough to repay
        // these amounts.

        // Approve the LendingPool contract allowance to *pull* the owed amount
        for (uint256 i = 0; i < assets.length; i++) {
            uint256 amountOwing = amounts[i] + premiums[i];
            IERC20(assets[i]).approve(address(LENDING_POOL), amountOwing);
        }

        return true;
    }

    function executeFlashLoanAndAct(
        address[] memory _tokenAddresses,
        uint256[] memory amounts
    ) public {
        address receiverAddress = address(this);

        // 0 = no debt, 1 = stable, 2 = variable
        uint256[] memory modes = new uint256[](amounts.length);
        for (uint256 i = 0; i < amounts.length; i++) {
            modes[i] = 0;
        }

        address onBehalfOf = address(this);
        bytes memory params = "";
        uint16 referralCode = 0;

        LENDING_POOL.flashLoan(
            receiverAddress,
            _tokenAddresses,
            amounts,
            modes,
            onBehalfOf,
            params,
            referralCode
        );
    }
}
