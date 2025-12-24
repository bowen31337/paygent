// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title PaymentRouter
 * @dev Router contract for handling x402 payments and fee distribution
 */
contract PaymentRouter {
    address public agentWallet;
    address public feeCollector;
    uint256 public feePercentage; // Fee in basis points (100 = 1%)

    address public owner;
    mapping(address => bool) public allowedAgents;

    event PaymentExecuted(
        address indexed agent,
        address indexed recipient,
        uint256 amount,
        uint256 feeAmount,
        uint256 netAmount
    );
    event FeeUpdated(uint256 newFeePercentage);
    event AgentPermissionUpdated(address indexed agent, bool allowed);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    modifier onlyAllowedAgent() {
        require(allowedAgents[msg.sender], "Agent not allowed");
        _;
    }

    constructor(
        address _agentWallet,
        address _feeCollector,
        uint256 _feePercentage
    ) {
        owner = msg.sender;
        agentWallet = _agentWallet;
        feeCollector = _feeCollector;
        feePercentage = _feePercentage;
    }

    function setFeePercentage(uint256 _feePercentage) external onlyOwner {
        require(_feePercentage <= 1000, "Fee cannot exceed 10%"); // Max 10%
        feePercentage = _feePercentage;
        emit FeeUpdated(_feePercentage);
    }

    function setAgentPermission(address agent, bool allowed) external onlyOwner {
        allowedAgents[agent] = allowed;
        emit AgentPermissionUpdated(agent, allowed);
    }

    function executePayment(
        address recipient,
        uint256 amount
    ) external onlyAllowedAgent returns (bool) {
        require(recipient != address(0), "Invalid recipient");
        require(amount > 0, "Amount must be greater than 0");

        // Calculate fee
        uint256 feeAmount = (amount * feePercentage) / 10000;
        uint256 netAmount = amount - feeAmount;

        // Transfer fee to collector
        if (feeAmount > 0) {
            // This would need actual token transfer logic
            // For now, just emit event
        }

        // Transfer net amount to recipient
        // This would need actual token transfer logic

        emit PaymentExecuted(msg.sender, recipient, amount, feeAmount, netAmount);
        return true;
    }

    function batchExecutePayments(
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external onlyAllowedAgent returns (bool) {
        require(recipients.length == amounts.length, "Arrays must have same length");
        require(recipients.length > 0, "Empty arrays not allowed");

        uint256 totalFee = 0;
        uint256 totalAmount = 0;

        for (uint256 i = 0; i < recipients.length; i++) {
            require(recipients[i] != address(0), "Invalid recipient");
            require(amounts[i] > 0, "Amount must be greater than 0");

            uint256 feeAmount = (amounts[i] * feePercentage) / 10000;
            totalFee += feeAmount;
            totalAmount += amounts[i];
        }

        // Process batch payment
        // This would need actual token transfer logic

        return true;
    }

    function getPaymentDetails(uint256 amount) external view returns (
        uint256 feeAmount,
        uint256 netAmount
    ) {
        feeAmount = (amount * feePercentage) / 10000;
        netAmount = amount - feeAmount;
    }
}