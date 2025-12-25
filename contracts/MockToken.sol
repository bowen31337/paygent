// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title MockToken
 * @dev Simple ERC20 token for testing purposes
 */
contract MockToken is ERC20 {
    /**
     * @dev Constructor initializes token with name "MockToken" and symbol "MTK"
     * Mints 1,000,000 tokens to the deployer
     */
    constructor() ERC20("MockToken", "MTK") {
        _mint(msg.sender, 1000000 * 10**18);
    }

    /**
     * @dev Mints tokens to a specified address
     * @param to Address to receive minted tokens
     * @param amount Amount of tokens to mint
     */
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}
