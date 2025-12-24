// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title PaymentRouter
 * @dev Batch payment router for executing multiple payments efficiently
 * Supports both native token (CRO) and ERC20 token payments
 */
contract PaymentRouter is ReentrancyGuard {
    // Events
    event BatchPaymentExecuted(
        address indexed payer,
        uint256 totalAmount,
        uint256 paymentCount,
        uint256 timestamp
    );
    event SinglePaymentExecuted(
        address indexed from,
        address indexed to,
        address indexed token,
        uint256 amount
    );

    // USDC token address (Cronos testnet)
    address public constant USDC = 0x2C7804F9272E6d9F39931C658f42186F455c1B49;

    /**
     * @dev Payment struct for batch operations
     */
    struct Payment {
        address recipient;
        uint256 amount;
    }

    /**
     * @dev Execute multiple CRO payments in a single transaction
     * @param _payments Array of payment structs
     * @return success Boolean array indicating success of each payment
     */
    function executeBatchCRO(Payment[] calldata _payments) external nonReentrant payable returns (bool[] memory success) {
        require(_payments.length > 0, "No payments to execute");

        uint256 totalAmount = 0;
        for (uint i = 0; i < _payments.length; i++) {
            totalAmount += _payments[i].amount;
        }

        require(msg.value >= totalAmount, "Insufficient CRO sent");

        success = new bool[](_payments.length);
        uint256 remaining = msg.value;

        for (uint i = 0; i < _payments.length; i++) {
            address recipient = _payments[i].recipient;
            uint256 amount = _payments[i].amount;

            require(recipient != address(0), "Invalid recipient");
            require(amount > 0, "Amount must be positive");
            require(remaining >= amount, "Insufficient remaining value");

            (bool sent, ) = recipient.call{value: amount}("");
            success[i] = sent;

            if (sent) {
                remaining -= amount;
                emit SinglePaymentExecuted(address(this), recipient, address(0), amount);
            }
        }

        emit BatchPaymentExecuted(msg.sender, totalAmount, _payments.length, block.timestamp);

        // Refund any unused CRO
        if (remaining > 0) {
            (bool sent, ) = msg.sender.call{value: remaining}("");
            require(sent, "Refund failed");
        }

        return success;
    }

    /**
     * @dev Execute multiple USDC payments in a single transaction
     * @param _payments Array of payment structs
     * @return success Boolean array indicating success of each payment
     */
    function executeBatchUSDC(Payment[] calldata _payments) external nonReentrant returns (bool[] memory success) {
        require(_payments.length > 0, "No payments to execute");

        uint256 totalAmount = 0;
        for (uint i = 0; i < _payments.length; i++) {
            totalAmount += _payments[i].amount;
        }

        // Transfer total USDC from caller to this contract
        IERC20(USDC).transferFrom(msg.sender, address(this), totalAmount);

        success = new bool[](_payments.length);

        for (uint i = 0; i < _payments.length; i++) {
            address recipient = _payments[i].recipient;
            uint256 amount = _payments[i].amount;

            require(recipient != address(0), "Invalid recipient");
            require(amount > 0, "Amount must be positive");

            bool sent = IERC20(USDC).transfer(recipient, amount);
            success[i] = sent;

            if (sent) {
                emit SinglePaymentExecuted(address(this), recipient, USDC, amount);
            }
        }

        emit BatchPaymentExecuted(msg.sender, totalAmount, _payments.length, block.timestamp);
        return success;
    }

    /**
     * @dev Execute a single CRO payment with additional metadata
     * @param _recipient Payment recipient
     * @param _amount Amount to send
     * @param _metadata Optional metadata hash (not used in contract, for off-chain tracking)
     * @return success Whether payment was successful
     */
    function payCRO(
        address _recipient,
        uint256 _amount,
        bytes32 _metadata
    ) external payable nonReentrant returns (bool success) {
        require(_recipient != address(0), "Invalid recipient");
        require(msg.value >= _amount, "Insufficient CRO sent");
        require(_amount > 0, "Amount must be positive");

        (bool sent, ) = _recipient.call{value: _amount}("");
        require(sent, "Transfer failed");

        emit SinglePaymentExecuted(msg.sender, _recipient, address(0), _amount);
        return true;
    }

    /**
     * @dev Execute a single USDC payment with additional metadata
     * @param _recipient Payment recipient
     * @param _amount Amount to send
     * @param _metadata Optional metadata hash (not used in contract, for off-chain tracking)
     * @return success Whether payment was successful
     */
    function payUSDC(
        address _recipient,
        uint256 _amount,
        bytes32 _metadata
    ) external nonReentrant returns (bool success) {
        require(_recipient != address(0), "Invalid recipient");
        require(_amount > 0, "Amount must be positive");

        // Transfer USDC from caller to recipient
        IERC20(USDC).transferFrom(msg.sender, _recipient, _amount);

        emit SinglePaymentExecuted(msg.sender, _recipient, USDC, _amount);
        return true;
    }

    /**
     * @dev Get USDC balance of this contract
     */
    function getUSDCBalance() external view returns (uint256) {
        return IERC20(USDC).balanceOf(address(this));
    }

    /**
     * @dev Get native CRO balance of this contract
     */
    function getCROBalance() external view returns (uint256) {
        return address(this).balance;
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
