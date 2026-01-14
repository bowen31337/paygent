// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title MockMoonlander
 * @dev Simplified perpetual trading contract for Cronos testnet
 *
 * This is a mock implementation for hackathon/testing purposes.
 * It simulates perpetual trading functionality:
 * - Open long/short positions
 * - Close positions
 * - Set stop-loss and take-profit
 * - Funding rate simulation
 */
contract MockMoonlander is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // Position struct
    struct Position {
        address trader;
        string market;         // e.g., "BTC-USDC", "ETH-USDC", "CRO-USDC"
        bool isLong;
        uint256 size;          // Position size in USDC (6 decimals)
        uint256 collateral;    // Collateral in USDC
        uint256 entryPrice;    // Entry price (8 decimals)
        uint256 leverage;      // Leverage (1-20x)
        uint256 stopLoss;      // Stop-loss price (8 decimals), 0 = not set
        uint256 takeProfit;    // Take-profit price (8 decimals), 0 = not set
        uint256 openTime;      // Timestamp when position was opened
        bool isOpen;
    }

    // Market configuration
    struct MarketConfig {
        uint256 maxLeverage;
        uint256 fundingRate;    // Funding rate per 8 hours (basis points, 1 = 0.01%)
        uint256 mockPrice;      // Mock price for testing (8 decimals)
        bool isActive;
    }

    // State variables
    IERC20 public collateralToken;  // USDC for collateral
    uint256 public positionCounter;

    mapping(uint256 => Position) public positions;
    mapping(address => uint256[]) public traderPositions;
    mapping(string => MarketConfig) public markets;

    // Events
    event PositionOpened(
        uint256 indexed positionId,
        address indexed trader,
        string market,
        bool isLong,
        uint256 size,
        uint256 collateral,
        uint256 leverage,
        uint256 entryPrice
    );

    event PositionClosed(
        uint256 indexed positionId,
        address indexed trader,
        uint256 exitPrice,
        int256 pnl
    );

    event StopLossSet(uint256 indexed positionId, uint256 stopLoss);
    event TakeProfitSet(uint256 indexed positionId, uint256 takeProfit);
    event FundingRateUpdated(string market, uint256 newRate);
    event MarketAdded(string market, uint256 maxLeverage, uint256 mockPrice);

    constructor(address _collateralToken) Ownable(msg.sender) {
        collateralToken = IERC20(_collateralToken);

        // Initialize default markets with mock prices
        _addMarket("BTC-USDC", 20, 1, 4200000000000);  // BTC at $42,000 (8 decimals)
        _addMarket("ETH-USDC", 20, 15, 220000000000);   // ETH at $2,200
        _addMarket("CRO-USDC", 10, 8, 7500000);         // CRO at $0.075
    }

    /**
     * @dev Add or update a market
     */
    function _addMarket(
        string memory market,
        uint256 maxLeverage,
        uint256 fundingRate,
        uint256 mockPrice
    ) internal {
        markets[market] = MarketConfig({
            maxLeverage: maxLeverage,
            fundingRate: fundingRate,
            mockPrice: mockPrice,
            isActive: true
        });
        emit MarketAdded(market, maxLeverage, mockPrice);
    }

    /**
     * @dev Open a new position
     * @param market The market to trade (e.g., "BTC-USDC")
     * @param isLong True for long, false for short
     * @param collateral Collateral amount in USDC (6 decimals)
     * @param leverage Leverage multiplier (1-maxLeverage)
     */
    function openPosition(
        string calldata market,
        bool isLong,
        uint256 collateral,
        uint256 leverage
    ) external nonReentrant returns (uint256 positionId) {
        MarketConfig storage config = markets[market];
        require(config.isActive, "Market not active");
        require(leverage >= 1 && leverage <= config.maxLeverage, "Invalid leverage");
        require(collateral > 0, "Collateral must be > 0");

        // Transfer collateral
        collateralToken.safeTransferFrom(msg.sender, address(this), collateral);

        // Calculate position size
        uint256 size = collateral * leverage;

        // Create position
        positionId = positionCounter++;
        positions[positionId] = Position({
            trader: msg.sender,
            market: market,
            isLong: isLong,
            size: size,
            collateral: collateral,
            entryPrice: config.mockPrice,
            leverage: leverage,
            stopLoss: 0,
            takeProfit: 0,
            openTime: block.timestamp,
            isOpen: true
        });

        traderPositions[msg.sender].push(positionId);

        emit PositionOpened(
            positionId,
            msg.sender,
            market,
            isLong,
            size,
            collateral,
            leverage,
            config.mockPrice
        );
    }

    /**
     * @dev Close a position
     * @param positionId The position ID to close
     */
    function closePosition(uint256 positionId) external nonReentrant returns (int256 pnl) {
        Position storage pos = positions[positionId];
        require(pos.isOpen, "Position not open");
        require(pos.trader == msg.sender || msg.sender == owner(), "Not authorized");

        MarketConfig storage config = markets[pos.market];
        uint256 exitPrice = config.mockPrice;

        // Calculate PnL (simplified - no fees)
        pnl = _calculatePnL(pos, exitPrice);

        // Close position
        pos.isOpen = false;

        // Calculate payout
        int256 payout = int256(pos.collateral) + pnl;
        if (payout > 0) {
            collateralToken.safeTransfer(pos.trader, uint256(payout));
        }

        emit PositionClosed(positionId, pos.trader, exitPrice, pnl);
    }

    /**
     * @dev Set stop-loss for a position
     */
    function setStopLoss(uint256 positionId, uint256 stopLoss) external {
        Position storage pos = positions[positionId];
        require(pos.isOpen, "Position not open");
        require(pos.trader == msg.sender, "Not authorized");

        pos.stopLoss = stopLoss;
        emit StopLossSet(positionId, stopLoss);
    }

    /**
     * @dev Set take-profit for a position
     */
    function setTakeProfit(uint256 positionId, uint256 takeProfit) external {
        Position storage pos = positions[positionId];
        require(pos.isOpen, "Position not open");
        require(pos.trader == msg.sender, "Not authorized");

        pos.takeProfit = takeProfit;
        emit TakeProfitSet(positionId, takeProfit);
    }

    /**
     * @dev Get funding rate for a market
     */
    function getFundingRate(string calldata market) external view returns (uint256 rate, uint256 nextFundingTime) {
        MarketConfig storage config = markets[market];
        require(config.isActive, "Market not active");

        rate = config.fundingRate;
        // Next funding in 8 hours from now (simplified)
        nextFundingTime = block.timestamp + 8 hours;
    }

    /**
     * @dev Get current price for a market (mock)
     */
    function getPrice(string calldata market) external view returns (uint256) {
        return markets[market].mockPrice;
    }

    /**
     * @dev Update mock price (owner only - for testing)
     */
    function setMockPrice(string calldata market, uint256 newPrice) external onlyOwner {
        markets[market].mockPrice = newPrice;
    }

    /**
     * @dev Update funding rate (owner only)
     */
    function setFundingRate(string calldata market, uint256 newRate) external onlyOwner {
        markets[market].fundingRate = newRate;
        emit FundingRateUpdated(market, newRate);
    }

    /**
     * @dev Get trader's open positions
     */
    function getTraderPositions(address trader) external view returns (uint256[] memory) {
        return traderPositions[trader];
    }

    /**
     * @dev Get position details
     */
    function getPosition(uint256 positionId) external view returns (
        address trader,
        string memory market,
        bool isLong,
        uint256 size,
        uint256 collateral,
        uint256 entryPrice,
        uint256 leverage,
        uint256 stopLoss,
        uint256 takeProfit,
        bool isOpen,
        int256 unrealizedPnl
    ) {
        Position storage pos = positions[positionId];
        MarketConfig storage config = markets[pos.market];

        return (
            pos.trader,
            pos.market,
            pos.isLong,
            pos.size,
            pos.collateral,
            pos.entryPrice,
            pos.leverage,
            pos.stopLoss,
            pos.takeProfit,
            pos.isOpen,
            pos.isOpen ? _calculatePnL(pos, config.mockPrice) : int256(0)
        );
    }

    /**
     * @dev Calculate PnL for a position
     */
    function _calculatePnL(Position storage pos, uint256 currentPrice) internal view returns (int256) {
        if (!pos.isOpen) return 0;

        // PnL = (exitPrice - entryPrice) / entryPrice * size * direction
        int256 priceDiff = int256(currentPrice) - int256(pos.entryPrice);
        int256 direction = pos.isLong ? int256(1) : int256(-1);

        // Simplified PnL calculation (scaled properly)
        int256 pnl = (priceDiff * int256(pos.size) * direction) / int256(pos.entryPrice);

        return pnl;
    }

    /**
     * @dev Emergency withdraw (owner only)
     */
    function emergencyWithdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).safeTransfer(owner(), amount);
    }
}
