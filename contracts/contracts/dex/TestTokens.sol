// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title TestUSDC
 * @dev Test USDC token for Cronos testnet (6 decimals like real USDC)
 */
contract TestUSDC is ERC20, Ownable {
    constructor() ERC20("Test USD Coin", "tUSDC") Ownable(msg.sender) {
        // Mint 10 million tUSDC to deployer
        _mint(msg.sender, 10_000_000 * 10**6);
    }

    function decimals() public pure override returns (uint8) {
        return 6;
    }

    /**
     * @dev Mints tokens to any address (for testnet faucet functionality)
     */
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    /**
     * @dev Faucet function - get 1000 tUSDC for testing
     */
    function faucet() external {
        _mint(msg.sender, 1000 * 10**6);
    }
}

/**
 * @title TestUSDT
 * @dev Test USDT token for Cronos testnet (6 decimals like real USDT)
 */
contract TestUSDT is ERC20, Ownable {
    constructor() ERC20("Test Tether USD", "tUSDT") Ownable(msg.sender) {
        // Mint 10 million tUSDT to deployer
        _mint(msg.sender, 10_000_000 * 10**6);
    }

    function decimals() public pure override returns (uint8) {
        return 6;
    }

    /**
     * @dev Mints tokens to any address (for testnet faucet functionality)
     */
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    /**
     * @dev Faucet function - get 1000 tUSDT for testing
     */
    function faucet() external {
        _mint(msg.sender, 1000 * 10**6);
    }
}

/**
 * @title TestVVS
 * @dev Test VVS token for Cronos testnet (18 decimals)
 */
contract TestVVS is ERC20, Ownable {
    constructor() ERC20("Test VVS Token", "tVVS") Ownable(msg.sender) {
        // Mint 1 billion tVVS to deployer
        _mint(msg.sender, 1_000_000_000 * 10**18);
    }

    /**
     * @dev Mints tokens to any address (for testnet faucet functionality)
     */
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    /**
     * @dev Faucet function - get 10000 tVVS for testing
     */
    function faucet() external {
        _mint(msg.sender, 10000 * 10**18);
    }
}
