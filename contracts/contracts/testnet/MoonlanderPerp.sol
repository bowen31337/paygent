// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title MoonlanderPerp
 * @notice Simplified perpetual trading contract for testnet demo
 * @dev Based on GMX Vault architecture but simplified for demo purposes
 */
contract MoonlanderPerp is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // Position structure matching GMX
    struct Position {
        uint256 size;           // Position size in USD (30 decimals)
        uint256 collateral;     // Collateral in USD (30 decimals)
        uint256 averagePrice;   // Average entry price (30 decimals)
        uint256 entryFundingRate;
        uint256 lastUpdatedTime;
        bool isLong;
    }

    // Constants
    uint256 public constant PRICE_PRECISION = 10 ** 30;
    uint256 public constant BASIS_POINTS_DIVISOR = 10000;
    uint256 public constant MAX_LEVERAGE = 100 * 10000; // 100x
    uint256 public constant MIN_LEVERAGE = 1 * 10000;   // 1x

    // State variables
    IERC20 public collateralToken;
    uint256 public totalOpenInterestLong;
    uint256 public totalOpenInterestShort;
    uint256 public fundingRate;
    uint256 public lastFundingTime;

    // Fee settings (in basis points)
    uint256 public positionFee = 10;     // 0.1%
    uint256 public fundingRateFactor = 100; // Funding rate factor

    // Mappings
    mapping(bytes32 => Position) public positions;
    mapping(address => bytes32[]) public userPositions;
    mapping(address => uint256) public userCollateral;

    // Mock prices for demo (in PRICE_PRECISION)
    mapping(string => uint256) public assetPrices;

    // Events
    event IncreasePosition(
        bytes32 indexed positionKey,
        address indexed account,
        string indexed asset,
        uint256 collateralDelta,
        uint256 sizeDelta,
        bool isLong,
        uint256 price
    );

    event DecreasePosition(
        bytes32 indexed positionKey,
        address indexed account,
        string indexed asset,
        uint256 collateralDelta,
        uint256 sizeDelta,
        bool isLong,
        uint256 price,
        int256 pnl
    );

    event ClosePosition(
        bytes32 indexed positionKey,
        address indexed account,
        uint256 size,
        uint256 collateral,
        int256 pnl
    );

    event LiquidatePosition(
        bytes32 indexed positionKey,
        address indexed account,
        address indexed liquidator,
        uint256 size,
        uint256 collateral
    );

    // Demo interaction events
    event CROReceived(address indexed sender, uint256 amount);
    event Ping(address indexed sender, uint256 blockNumber, uint256 value);

    constructor(address _collateralToken) Ownable(msg.sender) {
        collateralToken = IERC20(_collateralToken);

        // Set initial mock prices (30 decimals)
        assetPrices["BTC"] = 42000 * PRICE_PRECISION;
        assetPrices["ETH"] = 2200 * PRICE_PRECISION;
        assetPrices["CRO"] = 75 * PRICE_PRECISION / 1000; // 0.075

        lastFundingTime = block.timestamp;
    }

    // ============ External Functions ============

    /**
     * @notice Open or increase a perpetual position
     * @param _asset Asset symbol (BTC, ETH, CRO)
     * @param _collateralAmount Collateral amount in token decimals
     * @param _sizeDelta Position size delta in USD (6 decimals for simplicity)
     * @param _isLong True for long, false for short
     */
    function increasePosition(
        string calldata _asset,
        uint256 _collateralAmount,
        uint256 _sizeDelta,
        bool _isLong
    ) external nonReentrant returns (bytes32 positionKey) {
        require(assetPrices[_asset] > 0, "Invalid asset");
        require(_collateralAmount > 0, "Invalid collateral");
        require(_sizeDelta > 0, "Invalid size");

        // Transfer collateral
        collateralToken.safeTransferFrom(msg.sender, address(this), _collateralAmount);

        // Calculate position key
        positionKey = getPositionKey(msg.sender, _asset, _isLong);

        Position storage position = positions[positionKey];
        uint256 price = assetPrices[_asset];

        // Convert to 30 decimal precision
        uint256 collateralUsd = _collateralAmount * PRICE_PRECISION / (10 ** 6); // Assuming 6 decimal collateral
        uint256 sizeUsd = _sizeDelta * PRICE_PRECISION / (10 ** 6);

        // Check leverage
        uint256 leverage = (position.size + sizeUsd) * BASIS_POINTS_DIVISOR / (position.collateral + collateralUsd);
        require(leverage <= MAX_LEVERAGE, "Leverage too high");
        require(leverage >= MIN_LEVERAGE, "Leverage too low");

        // Update position
        if (position.size == 0) {
            position.averagePrice = price;
            position.entryFundingRate = fundingRate;
            position.lastUpdatedTime = block.timestamp;
            position.isLong = _isLong;
            userPositions[msg.sender].push(positionKey);
        } else {
            // Update average price
            position.averagePrice = (position.averagePrice * position.size + price * sizeUsd) / (position.size + sizeUsd);
        }

        position.size += sizeUsd;
        position.collateral += collateralUsd;
        userCollateral[msg.sender] += _collateralAmount;

        // Update open interest
        if (_isLong) {
            totalOpenInterestLong += sizeUsd;
        } else {
            totalOpenInterestShort += sizeUsd;
        }

        emit IncreasePosition(positionKey, msg.sender, _asset, _collateralAmount, _sizeDelta, _isLong, price);
    }

    /**
     * @notice Decrease or close a perpetual position
     * @param _asset Asset symbol
     * @param _collateralDelta Collateral to withdraw (6 decimals)
     * @param _sizeDelta Size to close (6 decimals)
     */
    function decreasePosition(
        string calldata _asset,
        uint256 _collateralDelta,
        uint256 _sizeDelta,
        bool _isLong
    ) external nonReentrant returns (int256 pnl) {
        bytes32 positionKey = getPositionKey(msg.sender, _asset, _isLong);
        Position storage position = positions[positionKey];

        require(position.size > 0, "Position does not exist");

        uint256 price = assetPrices[_asset];
        uint256 sizeUsd = _sizeDelta * PRICE_PRECISION / (10 ** 6);
        uint256 collateralUsd = _collateralDelta * PRICE_PRECISION / (10 ** 6);

        require(sizeUsd <= position.size, "Size exceeds position");
        require(collateralUsd <= position.collateral, "Collateral exceeds position");

        // Calculate PnL
        pnl = _calculatePnL(position, price, sizeUsd);

        // Update position
        position.size -= sizeUsd;
        position.collateral -= collateralUsd;

        // Update open interest
        if (_isLong) {
            totalOpenInterestLong -= sizeUsd;
        } else {
            totalOpenInterestShort -= sizeUsd;
        }

        // Transfer collateral back + PnL
        uint256 transferAmount = _collateralDelta;
        if (pnl > 0) {
            transferAmount += uint256(pnl) / PRICE_PRECISION * (10 ** 6);
        } else if (pnl < 0) {
            uint256 loss = uint256(-pnl) / PRICE_PRECISION * (10 ** 6);
            transferAmount = transferAmount > loss ? transferAmount - loss : 0;
        }

        if (transferAmount > 0) {
            collateralToken.safeTransfer(msg.sender, transferAmount);
        }

        userCollateral[msg.sender] -= _collateralDelta;

        emit DecreasePosition(positionKey, msg.sender, _asset, _collateralDelta, _sizeDelta, _isLong, price, pnl);

        // If position fully closed, emit close event
        if (position.size == 0) {
            emit ClosePosition(positionKey, msg.sender, sizeUsd, collateralUsd, pnl);
        }
    }

    // ============ View Functions ============

    function getPositionKey(address _account, string memory _asset, bool _isLong) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(_account, _asset, _isLong));
    }

    function getPosition(address _account, string calldata _asset, bool _isLong) external view returns (
        uint256 size,
        uint256 collateral,
        uint256 averagePrice,
        uint256 entryFundingRate,
        uint256 lastUpdatedTime,
        bool isLong
    ) {
        bytes32 key = getPositionKey(_account, _asset, _isLong);
        Position memory pos = positions[key];
        return (pos.size, pos.collateral, pos.averagePrice, pos.entryFundingRate, pos.lastUpdatedTime, pos.isLong);
    }

    function getUserPositionKeys(address _account) external view returns (bytes32[] memory) {
        return userPositions[_account];
    }

    function getPrice(string calldata _asset) external view returns (uint256) {
        return assetPrices[_asset];
    }

    // ============ Admin Functions ============

    function setPrice(string calldata _asset, uint256 _price) external onlyOwner {
        assetPrices[_asset] = _price;
    }

    function setFees(uint256 _positionFee, uint256 _fundingRateFactor) external onlyOwner {
        positionFee = _positionFee;
        fundingRateFactor = _fundingRateFactor;
    }

    // ============ Internal Functions ============

    function _calculatePnL(Position memory _position, uint256 _currentPrice, uint256 _sizeDelta) internal pure returns (int256) {
        if (_position.size == 0) return 0;

        int256 priceDelta;
        if (_position.isLong) {
            priceDelta = int256(_currentPrice) - int256(_position.averagePrice);
        } else {
            priceDelta = int256(_position.averagePrice) - int256(_currentPrice);
        }

        return priceDelta * int256(_sizeDelta) / int256(_position.averagePrice);
    }

    // ============ Demo/Interaction Functions ============

    /// @notice Allow contract to receive CRO for demo interactions
    receive() external payable {
        emit CROReceived(msg.sender, msg.value);
    }

    /// @notice Record a discovery/query interaction (for demo purposes)
    /// @return blockNumber Current block number
    /// @return timestamp Current block timestamp
    function ping() external payable returns (uint256 blockNumber, uint256 timestamp) {
        emit Ping(msg.sender, block.number, msg.value);
        return (block.number, block.timestamp);
    }

    /// @notice Get max leverage as simple multiplier (e.g., 100 for 100x)
    function maxLeverage() external pure returns (uint256) {
        return MAX_LEVERAGE / 10000;
    }
}
