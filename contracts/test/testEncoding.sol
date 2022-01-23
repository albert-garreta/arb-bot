pragma solidity ^0.8.0;

contract testEncoding {
    bytes params;
    uint8 public decodedParam;

    constructor() {
        params = abi.encode(uint8(1));
    }

    function decode() public {
        decodedParam = abi.decode(params, (uint8));
    }
}
