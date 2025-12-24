// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title AgentWallet
 * @dev Non-custodial smart contract wallet for AI agents with daily spending limits
 * and operator management for automated payment execution.
 */
contract AgentWallet is Ownable, ReentrancyGuard {
    // Events
    event OperatorAdded(address indexed operator);
    event OperatorRemoved(address indexed operator);
    event DailyLimitUpdated(uint256 indexed newLimit);
    event PaymentExecuted(
        address indexed recipient,
        address indexed token,
        uint256 amount,
        uint256 timestamp
    );
    event Withdrawal(address indexed recipient, uint256 amount);

    // Operator management
    mapping(address => bool) public operators;
    uint256 public operatorCount;

    // Daily spending limit
    uint256 public dailyLimitUSD;
    uint256 public lastResetDay;
    uint256 public spentToday;

    // USDC token address (Cronos testnet: 0x2C7804F9272E6d9F39931C658f42186F455c1B49)
    address public constant USDC = 0x2C7804F9272E6d9F39931C658f42186F455c1B49;

    // Modifier to restrict access to owner or operators
    modifier onlyAuthorized() {
        require(
            msg.sender == owner() || operators[msg.sender],
            "Not authorized"
        );
        _;
    }

    // Modifier to check daily limit
    modifier checkDailyLimit(uint256 usdAmount) {
        _updateDailySpending();
        require(
            spentToday + usdAmount <= dailyLimitUSD,
            "Daily limit exceeded"
        );
        _;
        spentToday += usdAmount;
    }

    constructor(uint256 _dailyLimitUSD) {
        require(_dailyLimitUSD > 0, "Daily limit must be positive");
        dailyLimitUSD = _dailyLimitUSD;
        lastResetDay = block.timestamp / 1 days;
    }

    /**
     * @dev Add an operator address
     * Only owner can call
     */
    function addOperator(address _operator) external onlyOwner {
        require(_operator != address(0), "Invalid operator address");
        require(!operators[_operator], "Operator already exists");

        operators[_operator] = true;
        operatorCount++;

        emit OperatorAdded(_operator);
    }

    /**
     * @dev Remove an operator address
     * Only owner can call
     */
    function removeOperator(address _operator) external onlyOwner {
        require(operators[_operator], "Operator does not exist");

        operators[_operator] = false;
        operatorCount--;

        emit OperatorRemoved(_operator);
    }

    /**
     * @dev Update daily spending limit
     * Only owner can call
     */
    function updateDailyLimit(uint256 _newLimit) external onlyOwner {
        require(_newLimit > 0, "Daily limit must be positive");
        dailyLimitUSD = _newLimit;
        emit DailyLimitUpdated(_newLimit);
    }

    /**
     * @dev Execute a payment in USDC
     * Can be called by owner or operators
     * Requires daily limit check
     */
    function executePayment(
        address _recipient,
        uint256 _amountUSDC,
        uint256 _usdValue
    ) external onlyAuthorized nonReentrant checkDailyLimit(_usdValue) returns (bool) {
        require(_recipient != address(0), "Invalid recipient");
        require(_amountUSDC > 0, "Amount must be positive");

        // Transfer USDC to recipient
        IERC20(USDC).transfer(_recipient, _amountUSDC);

        emit PaymentExecuted(_recipient, USDC, _amountUSDC, block.timestamp);
        return true;
    }

    /**
     * @dev Withdraw native tokens (CRO) from the wallet
     * Only owner can call
     */
    function withdraw(address _recipient, uint256 _amount) external onlyOwner nonReentrant {
        require(_recipient != address(0), "Invalid recipient");
        require(address(this).balance >= _amount, "Insufficient balance");

        (bool success, ) = _recipient.call{value: _amount}("");
        require(success, "Transfer failed");

        emit Withdrawal(_recipient, _amount);
    }

    /**
     * @dev Withdraw ERC20 tokens from the wallet
     * Only owner can call
     */
    function withdrawToken(
        address _token,
        address _recipient,
        uint256 _amount
    ) external onlyOwner nonReentrant {
        require(_recipient != address(0), "Invalid recipient");
        require(_token != address(0), "Invalid token");

        IERC20(_token).transfer(_recipient, _amount);

        emit Withdrawal(_recipient, _amount);
    }

    /**
     * @dev Get current daily spending status
     */
    function getDailySpendingStatus() external view returns (
        uint256 limit,
        uint256 spent,
        uint256 remaining
    ) {
        _updateDailySpending();
        return (dailyLimitUSD, spentToday, dailyLimitUSD - spentToday);
    }

    /**
     * @dev Check if an address is an operator
     */
    function isOperator(address _address) external view returns (bool) {
        return operators[_address];
    }

    /**
     * @dev Update daily spending counter if a new day has started
     */
    function _updateDailySpending() internal {
        uint256 currentDay = block.timestamp / 1 days;
        if (currentDay > lastResetDay) {
            spentToday = 0;
            lastResetDay = currentDay;
        }
    }

    /**
     * @dev Allow contract to receive CRO
     */
    receive() external payable {}

    /**
     * @dev Fallback function
     */
    fallback() external payable {}
}
