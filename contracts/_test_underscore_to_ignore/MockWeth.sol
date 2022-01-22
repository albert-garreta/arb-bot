// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockWeth is ERC20 {
    constructor() ERC20("Mock Weth token", "WETH") {}
    // constructor(uint256 _initialSupply) ERC20("Mock Weth token", "WETH") {
    //     _mint(msg.sender, _initialSupply);
    // }
}
