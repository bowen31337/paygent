// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title ReentrancyAttacker
 * @dev Malicious contract for testing reentrancy protection
 * This contract attempts to reenter AgentWallet's executePayment function
 */
contract ReentrancyAttacker {
    address public agentWallet;
    address public token;

    constructor(address _agentWallet, address _token) {
        agentWallet = _agentWallet;
        token = _token;
    }

    /**
     * @dev Attack function that attempts reentrancy
     * This will be called by AgentWallet during executePayment
     */
    function attack(uint256 amount) external {
        // Approve the agentWallet to spend our tokens
        IERC20(token).approve(agentWallet, amount);

        // Call executePayment on AgentWallet
        // This will trigger the receive/fallback function on this contract
        // which will try to call executePayment again
        (bool success, ) = agentWallet.call(
            abi.encodeWithSignature(
                "executePayment(address,address,uint256)",
                token,
                address(this), // recipient is this contract
                amount
            )
        );
        require(success, "Attack failed");
    }

    /**
     * @dev Receive function that gets called during reentrancy attempt
     * This function tries to reenter AgentWallet
     */
    receive() external payable {
        // Try to call executePayment again (reentrancy attempt)
        // This should fail due to ReentrancyGuard
        (bool success, ) = agentWallet.call(
            abi.encodeWithSignature(
                "executePayment(address,address,uint256)",
                token,
                address(this),
                1 // Small amount
            )
        );
        // If we get here without reverting, reentrancy protection failed
        if (success) {
            revert("Reentrancy succeeded - protection failed!");
        }
    }
}
