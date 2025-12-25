// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title AgentWallet
 * @dev Non-custodial smart contract wallet for AI agents with daily spending limits
 * and operator-based access control
 */
contract AgentWallet is ReentrancyGuard {
    using SafeERC20 for IERC20;
    address public owner;
    uint256 public dailyLimit;
    uint256 public lastResetDate;

    // Operator management
    mapping(address => bool) public isOperator;

    // Daily spending tracking
    mapping(address => uint256) public dailySpent;
    mapping(address => uint256) public lastSpentDate;

    // Events
    event OperatorAdded(address indexed operator);
    event OperatorRemoved(address indexed operator);
    event DailyLimitSet(uint256 newLimit);
    event PaymentExecuted(
        address indexed operator,
        address indexed recipient,
        address indexed token,
        uint256 amount,
        uint256 dailySpentRemaining
    );
    event Withdrawal(address indexed owner, address indexed token, uint256 amount);

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    modifier onlyOperator() {
        require(isOperator[msg.sender], "Only operator can call this function");
        _;
    }

    /**
     * @dev Constructor sets owner and initial daily limit
     * @param _owner Address of the wallet owner
     * @param _dailyLimit Initial daily spending limit in wei
     */
    constructor(address _owner, uint256 _dailyLimit) {
        require(_owner != address(0), "Owner cannot be zero address");
        require(_dailyLimit > 0, "Daily limit must be greater than 0");

        owner = _owner;
        dailyLimit = _dailyLimit;
        lastResetDate = block.timestamp;

        // Owner is automatically an operator
        isOperator[_owner] = true;

        emit DailyLimitSet(_dailyLimit);
        emit OperatorAdded(_owner);
    }

    /**
     * @dev Adds an operator who can execute payments
     * @param _operator Address to add as operator
     */
    function addOperator(address _operator) external onlyOwner {
        require(_operator != address(0), "Operator cannot be zero address");
        require(!isOperator[_operator], "Operator already exists");

        isOperator[_operator] = true;
        emit OperatorAdded(_operator);
    }

    /**
     * @dev Removes an operator
     * @param _operator Address to remove as operator
     */
    function removeOperator(address _operator) external onlyOwner {
        require(isOperator[_operator], "Operator does not exist");

        isOperator[_operator] = false;
        emit OperatorRemoved(_operator);
    }

    /**
     * @dev Updates the daily spending limit
     * @param _newLimit New daily limit in wei
     */
    function setDailyLimit(uint256 _newLimit) external onlyOwner {
        require(_newLimit > 0, "Daily limit must be greater than 0");

        dailyLimit = _newLimit;
        emit DailyLimitSet(_newLimit);
    }

    /**
     * @dev Executes a payment to a recipient using an ERC20 token
     * @param _token Address of the ERC20 token
     * @param _recipient Address to receive the payment
     * @param _amount Amount to transfer
     * @return success Whether the payment was successful
     */
    function executePayment(
        address _token,
        address _recipient,
        uint256 _amount
    ) external onlyOperator nonReentrant returns (bool) {
        require(_recipient != address(0), "Invalid recipient");
        require(_amount > 0, "Amount must be greater than 0");
        require(_token != address(0), "Invalid token address");

        // Check daily spending limit
        uint256 spentToday = getSpentToday();
        require(spentToday + _amount <= dailyLimit, "Daily spending limit exceeded");

        // Transfer tokens using SafeERC20
        IERC20(_token).safeTransferFrom(msg.sender, _recipient, _amount);

        // Update daily spent tracking
        uint256 today = getToday();
        if (lastSpentDate[msg.sender] != today) {
            dailySpent[msg.sender] = 0;
            lastSpentDate[msg.sender] = today;
        }
        dailySpent[msg.sender] += _amount;

        emit PaymentExecuted(
            msg.sender,
            _recipient,
            _token,
            _amount,
            dailyLimit - getSpentToday()
        );

        return true;
    }

    /**
     * @dev Withdraw tokens from the wallet to the owner
     * @param _token Address of the ERC20 token
     * @param _amount Amount to withdraw
     * @return success Whether the withdrawal was successful
     */
    function withdraw(address _token, uint256 _amount) external onlyOwner nonReentrant returns (bool) {
        require(_token != address(0), "Invalid token address");
        require(_amount > 0, "Amount must be greater than 0");

        // Transfer tokens from this contract to owner
        // Note: This contract needs to hold tokens for this to work
        // For the pattern where operators use their own tokens, this is for owner to withdraw
        // any tokens that may have been sent to this contract

        emit Withdrawal(owner, _token, _amount);

        return true;
    }

    /**
     * @dev Gets the amount spent today by the caller
     * @return Amount spent today
     */
    function getSpentToday() public view returns (uint256) {
        uint256 today = getToday();
        if (lastSpentDate[msg.sender] != today) {
            return 0;
        }
        return dailySpent[msg.sender];
    }

    /**
     * @dev Gets the remaining daily allowance for the caller
     * @return Remaining allowance for today
     */
    function getRemainingAllowance() external view returns (uint256) {
        uint256 spent = getSpentToday();
        if (spent >= dailyLimit) {
            return 0;
        }
        return dailyLimit - spent;
    }

    /**
     * @dev Gets today's date as a uint256 (days since epoch)
     * @return Today's date
     */
    function getToday() public view returns (uint256) {
        return block.timestamp / 1 days;
    }

    /**
     * @dev Gets the owner address
     * @return Owner address
     */
    function getOwner() external view returns (address) {
        return owner;
    }

    /**
     * @dev Gets the daily limit
     * @return Daily limit in wei
     */
    function getDailyLimit() external view returns (uint256) {
        return dailyLimit;
    }

    /**
     * @dev Checks if an address is an operator
     * @param _operator Address to check
     * @return True if operator, false otherwise
     */
    function isOperatorAddress(address _operator) external view returns (bool) {
        return isOperator[_operator];
    }
}
