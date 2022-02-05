pragma solidity ^0.8.0;
import "./IERC20.sol";

interface IWERC20 is IERC20 {
    function deposit() external returns (bool);
}
