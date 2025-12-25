// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title PaymentRouter
 * @dev Router contract for handling batch payments and fee distribution
 */
contract PaymentRouter is ReentrancyGuard {
    using SafeERC20 for IERC20;

    // State variables
    address public owner;
    address public feeCollector;
    uint256 public feePercentage; // Fee in basis points (100 = 1%)

    // Allowed agents who can execute payments
    mapping(address => bool) public allowedAgents;

    // Events
    event PaymentExecuted(
        address indexed agent,
        address indexed recipient,
        address indexed token,
        uint256 amount,
        uint256 feeAmount,
        uint256 netAmount
    );
    event BatchPaymentExecuted(
        address indexed agent,
        address indexed token,
        uint256 totalAmount,
        uint256 totalFee,
        uint256 totalNet,
        uint256 paymentCount
    );
    event FeeUpdated(uint256 newFeePercentage);
    event AgentPermissionUpdated(address indexed agent, bool allowed);
    event FeeCollectorUpdated(address indexed newCollector);

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    modifier onlyAllowedAgent() {
        require(allowedAgents[msg.sender], "Agent not allowed");
        _;
    }

    /**
     * @dev Constructor
     * @param _feeCollector Address that receives fees
     * @param _feePercentage Fee in basis points (100 = 1%, max 10% = 1000)
     */
    constructor(address _feeCollector, uint256 _feePercentage) {
        owner = msg.sender;
        feeCollector = _feeCollector;
        require(_feePercentage <= 1000, "Fee cannot exceed 10%");
        feePercentage = _feePercentage;

        // Owner is automatically allowed
        allowedAgents[msg.sender] = true;
    }

    // ==================== External Functions ====================

    /**
     * @dev Updates the fee percentage
     * @param _feePercentage New fee percentage in basis points
     */
    function setFeePercentage(uint256 _feePercentage) external onlyOwner {
        require(_feePercentage <= 1000, "Fee cannot exceed 10%");
        feePercentage = _feePercentage;
        emit FeeUpdated(_feePercentage);
    }

    /**
     * @dev Updates the fee collector address
     * @param _feeCollector New fee collector address
     */
    function setFeeCollector(address _feeCollector) external onlyOwner {
        require(_feeCollector != address(0), "Invalid fee collector address");
        feeCollector = _feeCollector;
        emit FeeCollectorUpdated(_feeCollector);
    }

    /**
     * @dev Adds or removes an agent's permission
     * @param _agent Address of the agent
     * @param _allowed Whether the agent is allowed
     */
    function setAgentPermission(address _agent, bool _allowed) external onlyOwner {
        allowedAgents[_agent] = _allowed;
        emit AgentPermissionUpdated(_agent, _allowed);
    }

    /**
     * @dev Executes a single payment
     * @param _token Address of the ERC20 token
     * @param _recipient Address to receive payment
     * @param _amount Amount to transfer
     * @return success Whether payment was successful
     */
    function executePayment(
        address _token,
        address _recipient,
        uint256 _amount
    ) external onlyAllowedAgent nonReentrant returns (bool) {
        require(_recipient != address(0), "Invalid recipient");
        require(_amount > 0, "Amount must be greater than 0");
        require(_token != address(0), "Invalid token address");

        // Calculate fee
        uint256 feeAmount = (_amount * feePercentage) / 10000;
        uint256 netAmount = _amount - feeAmount;

        // Transfer tokens from agent to recipient and fee collector using SafeERC20
        // Agent must approve this contract first
        IERC20(_token).safeTransferFrom(msg.sender, _recipient, netAmount);

        if (feeAmount > 0) {
            IERC20(_token).safeTransferFrom(msg.sender, feeCollector, feeAmount);
        }

        emit PaymentExecuted(
            msg.sender,
            _recipient,
            _token,
            _amount,
            feeAmount,
            netAmount
        );

        return true;
    }

    /**
     * @dev Executes batch payments to multiple recipients
     * @param _token Address of the ERC20 token
     * @param _recipients Array of recipient addresses
     * @param _amounts Array of amounts corresponding to recipients
     * @return success Whether all payments were successful
     */
    function batchPay(
        address _token,
        address[] calldata _recipients,
        uint256[] calldata _amounts
    ) external onlyAllowedAgent nonReentrant returns (bool) {
        require(_recipients.length == _amounts.length, "Arrays must have same length");
        require(_recipients.length > 0, "Empty arrays not allowed");
        require(_token != address(0), "Invalid token address");

        uint256 totalFee = 0;
        uint256 totalAmount = 0;
        uint256 totalNet = 0;

        // First pass: validate and calculate totals
        for (uint256 i = 0; i < _recipients.length; i++) {
            require(_recipients[i] != address(0), "Invalid recipient");
            require(_amounts[i] > 0, "Amount must be greater than 0");

            uint256 feeAmount = (_amounts[i] * feePercentage) / 10000;
            totalFee += feeAmount;
            totalAmount += _amounts[i];
            totalNet += _amounts[i] - feeAmount;
        }

        // Transfer total fee to collector using SafeERC20
        if (totalFee > 0) {
            IERC20(_token).safeTransferFrom(msg.sender, feeCollector, totalFee);
        }

        // Transfer net amounts to recipients using SafeERC20
        // Using a loop with individual transfers for simplicity and safety
        for (uint256 i = 0; i < _recipients.length; i++) {
            uint256 netAmount = _amounts[i] - ((_amounts[i] * feePercentage) / 10000);
            IERC20(_token).safeTransferFrom(msg.sender, _recipients[i], netAmount);
        }

        emit BatchPaymentExecuted(
            msg.sender,
            _token,
            totalAmount,
            totalFee,
            totalNet,
            _recipients.length
        );

        return true;
    }

    // ==================== View Functions ====================

    /**
     * @dev Gets payment details for a given amount
     * @param _amount Amount to calculate fees for
     * @return feeAmount The fee amount
     * @return netAmount The net amount after fee
     */
    function getPaymentDetails(uint256 _amount) external view returns (
        uint256 feeAmount,
        uint256 netAmount
    ) {
        feeAmount = (_amount * feePercentage) / 10000;
        netAmount = _amount - feeAmount;
    }

    /**
     * @dev Checks if an agent is allowed
     * @param _agent Address to check
     * @return True if agent is allowed
     */
    function isAgentAllowed(address _agent) external view returns (bool) {
        return allowedAgents[_agent];
    }

    /**
     * @dev Gets fee collector address
     * @return Fee collector address
     */
    function getFeeCollector() external view returns (address) {
        return feeCollector;
    }

    /**
     * @dev Gets fee percentage
     * @return Fee percentage in basis points
     */
    function getFeePercentage() external view returns (uint256) {
        return feePercentage;
    }
}
