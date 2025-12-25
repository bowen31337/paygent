// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IMoonlanderRouter
 * @dev Interface for Moonlander perpetual trading router
 */
interface IMoonlanderRouter {
    function openPosition(
        address baseToken,
        address quoteToken,
        bool isLong,
        uint256 amount,
        uint256 leverage,
        uint256 slippageTolerance,
        uint256 deadline
    ) external returns (bytes32 positionId);

    function closePosition(
        bytes32 positionId,
        uint256 slippageTolerance,
        uint256 deadline
    ) external returns (uint256 profit, uint256 fee);

    function setStopLoss(
        bytes32 positionId,
        uint256 stopLossPrice
    ) external;

    function setTakeProfit(
        bytes32 positionId,
        uint256 takeProfitPrice
    ) external;

    function getFundingRate(address baseToken, address quoteToken) external view returns (int256 rate);
}

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title MoonlanderAdapter
 * @dev Adapter contract for Moonlander perpetual trading operations
 */
contract MoonlanderAdapter {
    // State variables
    address public tradingRouter;
    address public feeManager;
    uint256 public defaultLeverage;
    address public owner;

    // Structs
    struct Position {
        bytes32 positionId;
        address baseToken;
        address quoteToken;
        bool isLong;
        uint256 amount;
        uint256 leverage;
        uint256 entryPrice;
        uint256 liquidationPrice;
        uint256 stopLossPrice;
        uint256 takeProfitPrice;
        uint256 openedAt;
        uint256 closedAt;
        bool active;
        address trader;
    }

    struct Trade {
        bytes32 positionId;
        address trader;
        uint256 amount;
        uint256 leverage;
        bool isLong;
        uint256 entryPrice;
        uint256 fee;
        uint256 timestamp;
    }

    // Mappings
    mapping(bytes32 => Position) public positions;
    mapping(address => bytes32[]) public traderPositions;
    mapping(bytes32 => Trade) public trades;

    // Constants
    uint256 public constant MAX_LEVERAGE = 50; // 50x max leverage
    uint256 public constant MIN_LEVERAGE = 2;  // 2x min leverage

    // Events
    event PositionOpened(
        bytes32 indexed positionId,
        address indexed trader,
        address baseToken,
        address quoteToken,
        bool isLong,
        uint256 amount,
        uint256 leverage,
        uint256 entryPrice
    );
    event PositionClosed(
        bytes32 indexed positionId,
        address indexed trader,
        uint256 profit,
        uint256 fee,
        uint256 exitPrice
    );
    event StopLossSet(bytes32 indexed positionId, uint256 stopLossPrice);
    event TakeProfitSet(bytes32 indexed positionId, uint256 takeProfitPrice);
    event FundingRateUpdated(address indexed baseToken, address indexed quoteToken, int256 rate);

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    /**
     * @dev Constructor
     * @param _tradingRouter Moonlander router address
     * @param _feeManager Fee manager address
     * @param _defaultLeverage Default leverage for positions
     */
    constructor(
        address _tradingRouter,
        address _feeManager,
        uint256 _defaultLeverage
    ) {
        owner = msg.sender;
        tradingRouter = _tradingRouter;
        feeManager = _feeManager;
        defaultLeverage = _defaultLeverage;
    }

    // ==================== External Functions ====================

    /**
     * @dev Opens a new perpetual position
     * @param baseToken Base token address
     * @param quoteToken Quote token address
     * @param isLong True for long position, false for short
     * @param amount Position size
     * @param leverage Leverage multiplier (0 for default)
     * @param slippageTolerance Slippage tolerance in basis points
     * @param deadline Timestamp deadline
     * @return positionId Unique position identifier
     */
    function openPosition(
        address baseToken,
        address quoteToken,
        bool isLong,
        uint256 amount,
        uint256 leverage,
        uint256 slippageTolerance,
        uint256 deadline
    ) external returns (bytes32) {
        require(baseToken != address(0) && quoteToken != address(0), "Invalid tokens");
        require(amount > 0, "Amount must be greater than 0");
        require(deadline > block.timestamp, "Deadline must be in the future");

        // Validate leverage
        uint256 useLeverage = leverage > 0 ? leverage : defaultLeverage;
        require(useLeverage >= MIN_LEVERAGE && useLeverage <= MAX_LEVERAGE, "Invalid leverage");

        // Approve trading router to spend tokens
        IERC20(quoteToken).approve(tradingRouter, amount);

        bytes32 positionId = IMoonlanderRouter(tradingRouter).openPosition(
            baseToken,
            quoteToken,
            isLong,
            amount,
            useLeverage,
            slippageTolerance,
            deadline
        );

        // Get current price for entry price calculation
        uint256 entryPrice = getCurrentPrice(baseToken, quoteToken);
        uint256 liquidationPrice = calculateLiquidationPrice(entryPrice, isLong, useLeverage);

        positions[positionId] = Position({
            positionId: positionId,
            baseToken: baseToken,
            quoteToken: quoteToken,
            isLong: isLong,
            amount: amount,
            leverage: useLeverage,
            entryPrice: entryPrice,
            liquidationPrice: liquidationPrice,
            stopLossPrice: 0,
            takeProfitPrice: 0,
            openedAt: block.timestamp,
            closedAt: 0,
            active: true,
            trader: msg.sender
        });

        traderPositions[msg.sender].push(positionId);

        trades[positionId] = Trade({
            positionId: positionId,
            trader: msg.sender,
            amount: amount,
            leverage: useLeverage,
            isLong: isLong,
            entryPrice: entryPrice,
            fee: calculateFee(amount, useLeverage),
            timestamp: block.timestamp
        });

        emit PositionOpened(positionId, msg.sender, baseToken, quoteToken, isLong, amount, useLeverage, entryPrice);
        return positionId;
    }

    /**
     * @dev Closes an existing position
     * @param positionId Position to close
     * @param slippageTolerance Slippage tolerance in basis points
     * @param deadline Timestamp deadline
     * @return profit Profit amount
     * @return fee Fee amount
     */
    function closePosition(
        bytes32 positionId,
        uint256 slippageTolerance,
        uint256 deadline
    ) external returns (uint256 profit, uint256 fee) {
        Position storage position = positions[positionId];
        require(position.active, "Position is not active");
        require(position.trader == msg.sender, "Not position owner");

        (profit, fee) = IMoonlanderRouter(tradingRouter).closePosition(
            positionId,
            slippageTolerance,
            deadline
        );

        position.active = false;
        position.closedAt = block.timestamp;

        uint256 exitPrice = getCurrentPrice(position.baseToken, position.quoteToken);

        emit PositionClosed(positionId, msg.sender, profit, fee, exitPrice);
        return (profit, fee);
    }

    /**
     * @dev Sets stop loss price for a position
     * @param positionId Position identifier
     * @param stopLossPrice Stop loss price
     */
    function setStopLoss(
        bytes32 positionId,
        uint256 stopLossPrice
    ) external {
        Position storage position = positions[positionId];
        require(position.active, "Position is not active");
        require(position.trader == msg.sender, "Not position owner");
        require(stopLossPrice > 0, "Stop loss price must be greater than 0");

        position.stopLossPrice = stopLossPrice;

        IMoonlanderRouter(tradingRouter).setStopLoss(positionId, stopLossPrice);
        emit StopLossSet(positionId, stopLossPrice);
    }

    /**
     * @dev Sets take profit price for a position
     * @param positionId Position identifier
     * @param takeProfitPrice Take profit price
     */
    function setTakeProfit(
        bytes32 positionId,
        uint256 takeProfitPrice
    ) external {
        Position storage position = positions[positionId];
        require(position.active, "Position is not active");
        require(position.trader == msg.sender, "Not position owner");
        require(takeProfitPrice > 0, "Take profit price must be greater than 0");

        position.takeProfitPrice = takeProfitPrice;

        IMoonlanderRouter(tradingRouter).setTakeProfit(positionId, takeProfitPrice);
        emit TakeProfitSet(positionId, takeProfitPrice);
    }

    // ==================== View Functions ====================

    /**
     * @dev Gets funding rate for a token pair
     * @param baseToken Base token address
     * @param quoteToken Quote token address
     * @return rate Funding rate
     */
    function getFundingRate(
        address baseToken,
        address quoteToken
    ) external view returns (int256) {
        return IMoonlanderRouter(tradingRouter).getFundingRate(baseToken, quoteToken);
    }

    /**
     * @dev Gets position details
     * @param positionId Position identifier
     * @return baseToken Base token
     * @return quoteToken Quote token
     * @return isLong Long/short direction
     * @return amount Position size
     * @return leverage Leverage multiplier
     * @return entryPrice Entry price
     * @return liquidationPrice Liquidation price
     * @return stopLossPrice Stop loss price
     * @return takeProfitPrice Take profit price
     * @return openedAt Open timestamp
     * @return closedAt Close timestamp
     * @return active Active status
     */
    function getPosition(
        bytes32 positionId
    ) external view returns (
        address baseToken,
        address quoteToken,
        bool isLong,
        uint256 amount,
        uint256 leverage,
        uint256 entryPrice,
        uint256 liquidationPrice,
        uint256 stopLossPrice,
        uint256 takeProfitPrice,
        uint256 openedAt,
        uint256 closedAt,
        bool active
    ) {
        Position storage position = positions[positionId];
        return (
            position.baseToken,
            position.quoteToken,
            position.isLong,
            position.amount,
            position.leverage,
            position.entryPrice,
            position.liquidationPrice,
            position.stopLossPrice,
            position.takeProfitPrice,
            position.openedAt,
            position.closedAt,
            position.active
        );
    }

    /**
     * @dev Gets all positions for a trader
     * @param trader Trader address
     * @return Array of position IDs
     */
    function getTraderPositions(address trader) external view returns (bytes32[] memory) {
        return traderPositions[trader];
    }

    // ==================== Public Functions ====================

    /**
     * @dev Gets current price for a token pair (mock implementation)
     * @param baseToken Base token address
     * @param quoteToken Quote token address
     * @return Current price
     */
    function getCurrentPrice(address baseToken, address quoteToken) public view returns (uint256) {
        // This would need integration with price oracle oracles
        // For now, return a mock implementation
        return 1000; // Mock price
    }

    // ==================== Internal Functions ====================

    /**
     * @dev Calculates liquidation price
     * @param entryPrice Entry price
     * @param isLong Long/short direction
     * @param leverage Leverage multiplier
     * @return Liquidation price
     */
    function calculateLiquidationPrice(
        uint256 entryPrice,
        bool isLong,
        uint256 leverage
    ) internal pure returns (uint256) {
        // Simplified liquidation price calculation
        // In reality, this would be more complex
        if (isLong) {
            return (entryPrice * (leverage - 1)) / leverage;
        } else {
            return (entryPrice * (leverage + 1)) / leverage;
        }
    }

    /**
     * @dev Calculates trading fee
     * @param amount Position size
     * @param leverage Leverage multiplier
     * @return Fee amount
     */
    function calculateFee(uint256 amount, uint256 leverage) internal view returns (uint256) {
        // Fee calculation: 0.1% of position size
        return (amount * leverage * 1) / 1000;
    }
}
