// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title DelphiPrediction
 * @notice Simplified prediction market for testnet demo
 * @dev Based on Polymarket architecture but simplified for demo purposes
 */
contract DelphiPrediction is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // Market structure
    struct Market {
        string question;
        uint256 endTime;
        uint256 resolutionTime;
        uint256 totalYesShares;
        uint256 totalNoShares;
        uint256 totalYesStake;
        uint256 totalNoStake;
        Outcome outcome;
        bool resolved;
    }

    // Bet structure
    struct Bet {
        uint256 marketId;
        address bettor;
        bool isYes;
        uint256 stake;
        uint256 shares;
        bool claimed;
    }

    enum Outcome { PENDING, YES, NO, INVALID }

    // Constants
    uint256 public constant BASIS_POINTS = 10000;
    uint256 public platformFee = 100; // 1%
    uint256 public marketCount;
    uint256 public betCount;

    // State
    IERC20 public collateralToken;
    mapping(uint256 => Market) public markets;
    mapping(uint256 => Bet) public bets;
    mapping(address => uint256[]) public userBets;
    mapping(uint256 => mapping(address => uint256)) public userMarketShares; // marketId => user => shares

    // Events
    event MarketCreated(
        uint256 indexed marketId,
        string question,
        uint256 endTime
    );

    event BetPlaced(
        uint256 indexed betId,
        uint256 indexed marketId,
        address indexed bettor,
        bool isYes,
        uint256 stake,
        uint256 shares,
        uint256 price
    );

    event MarketResolved(
        uint256 indexed marketId,
        Outcome outcome
    );

    event WinningsClaimed(
        uint256 indexed betId,
        address indexed bettor,
        uint256 payout
    );

    // Demo interaction events
    event CROReceived(address indexed sender, uint256 amount);
    event Ping(address indexed sender, uint256 blockNumber, uint256 value);

    constructor(address _collateralToken) Ownable(msg.sender) {
        collateralToken = IERC20(_collateralToken);
    }

    // ============ External Functions ============

    /**
     * @notice Create a new prediction market
     * @param question The market question
     * @param duration Market duration in seconds
     */
    function createMarket(
        string calldata question,
        uint256 duration
    ) external onlyOwner returns (uint256 marketId) {
        marketId = marketCount++;

        markets[marketId] = Market({
            question: question,
            endTime: block.timestamp + duration,
            resolutionTime: 0,
            totalYesShares: 0,
            totalNoShares: 0,
            totalYesStake: 0,
            totalNoStake: 0,
            outcome: Outcome.PENDING,
            resolved: false
        });

        emit MarketCreated(marketId, question, block.timestamp + duration);
    }

    /**
     * @notice Place a bet on a market
     * @param marketId Market ID
     * @param isYes True for YES, false for NO
     * @param stake Amount to stake
     */
    function placeBet(
        uint256 marketId,
        bool isYes,
        uint256 stake
    ) external nonReentrant returns (uint256 betId, uint256 shares) {
        Market storage market = markets[marketId];
        require(market.endTime > 0, "Market does not exist");
        require(block.timestamp < market.endTime, "Market ended");
        require(!market.resolved, "Market resolved");
        require(stake > 0, "Invalid stake");

        // Transfer collateral
        collateralToken.safeTransferFrom(msg.sender, address(this), stake);

        // Calculate shares based on current odds
        uint256 price = getPrice(marketId, isYes);
        shares = stake * BASIS_POINTS / price;

        // Apply fee
        uint256 fee = stake * platformFee / BASIS_POINTS;
        uint256 netStake = stake - fee;

        // Create bet
        betId = betCount++;
        bets[betId] = Bet({
            marketId: marketId,
            bettor: msg.sender,
            isYes: isYes,
            stake: netStake,
            shares: shares,
            claimed: false
        });

        userBets[msg.sender].push(betId);

        // Update market
        if (isYes) {
            market.totalYesShares += shares;
            market.totalYesStake += netStake;
        } else {
            market.totalNoShares += shares;
            market.totalNoStake += netStake;
        }

        emit BetPlaced(betId, marketId, msg.sender, isYes, stake, shares, price);
    }

    /**
     * @notice Resolve a market
     * @param marketId Market ID
     * @param outcome Final outcome
     */
    function resolveMarket(uint256 marketId, Outcome outcome) external onlyOwner {
        Market storage market = markets[marketId];
        require(market.endTime > 0, "Market does not exist");
        require(block.timestamp >= market.endTime, "Market not ended");
        require(!market.resolved, "Already resolved");
        require(outcome != Outcome.PENDING, "Invalid outcome");

        market.resolved = true;
        market.outcome = outcome;
        market.resolutionTime = block.timestamp;

        emit MarketResolved(marketId, outcome);
    }

    /**
     * @notice Claim winnings from a bet
     * @param betId Bet ID
     */
    function claimWinnings(uint256 betId) external nonReentrant returns (uint256 payout) {
        Bet storage bet = bets[betId];
        require(bet.bettor == msg.sender, "Not your bet");
        require(!bet.claimed, "Already claimed");

        Market storage market = markets[bet.marketId];
        require(market.resolved, "Market not resolved");

        bet.claimed = true;

        // Calculate payout
        if (market.outcome == Outcome.INVALID) {
            // Refund on invalid
            payout = bet.stake;
        } else if (
            (market.outcome == Outcome.YES && bet.isYes) ||
            (market.outcome == Outcome.NO && !bet.isYes)
        ) {
            // Winner - proportional payout from losing side + original stake
            uint256 totalPool = market.totalYesStake + market.totalNoStake;
            uint256 winningShares = bet.isYes ? market.totalYesShares : market.totalNoShares;

            if (winningShares > 0) {
                payout = bet.shares * totalPool / winningShares;
            }
        }
        // Losers get nothing (payout = 0)

        if (payout > 0) {
            collateralToken.safeTransfer(msg.sender, payout);
        }

        emit WinningsClaimed(betId, msg.sender, payout);
    }

    // ============ View Functions ============

    /**
     * @notice Get current price for YES or NO shares
     * @dev Price in basis points (e.g., 6500 = 65%)
     */
    function getPrice(uint256 marketId, bool isYes) public view returns (uint256) {
        Market memory market = markets[marketId];

        uint256 totalShares = market.totalYesShares + market.totalNoShares;
        if (totalShares == 0) {
            return 5000; // 50% default
        }

        uint256 price;
        if (isYes) {
            // YES price = NO shares / total shares
            price = market.totalNoShares * BASIS_POINTS / totalShares;
        } else {
            // NO price = YES shares / total shares
            price = market.totalYesShares * BASIS_POINTS / totalShares;
        }
        
        // Prevent division by zero in placeBet - minimum price is 1 basis point
        if (price == 0) {
            price = 1;
        }
        
        return price;
    }

    function getMarket(uint256 marketId) external view returns (
        string memory question,
        uint256 endTime,
        uint256 totalYesShares,
        uint256 totalNoShares,
        uint256 totalYesStake,
        uint256 totalNoStake,
        Outcome outcome,
        bool resolved
    ) {
        Market memory m = markets[marketId];
        return (
            m.question,
            m.endTime,
            m.totalYesShares,
            m.totalNoShares,
            m.totalYesStake,
            m.totalNoStake,
            m.outcome,
            m.resolved
        );
    }

    function getBet(uint256 betId) external view returns (
        uint256 marketId,
        address bettor,
        bool isYes,
        uint256 stake,
        uint256 shares,
        bool claimed
    ) {
        Bet memory b = bets[betId];
        return (b.marketId, b.bettor, b.isYes, b.stake, b.shares, b.claimed);
    }

    function getUserBets(address user) external view returns (uint256[] memory) {
        return userBets[user];
    }

    function getOdds(uint256 marketId) external view returns (uint256 yesOdds, uint256 noOdds) {
        yesOdds = getPrice(marketId, true);
        noOdds = getPrice(marketId, false);
    }

    // ============ Admin Functions ============

    function setPlatformFee(uint256 _fee) external onlyOwner {
        require(_fee <= 1000, "Fee too high"); // Max 10%
        platformFee = _fee;
    }

    function withdrawFees(address to) external onlyOwner {
        uint256 balance = collateralToken.balanceOf(address(this));
        if (balance > 0) {
            collateralToken.safeTransfer(to, balance);
        }
    }

    // ============ Demo/Interaction Functions ============

    /// @notice Allow contract to receive CRO for demo interactions
    receive() external payable {
        emit CROReceived(msg.sender, msg.value);
    }

    /// @notice Record a discovery/query interaction (for demo purposes)
    /// @return blockNumber Current block number
    /// @return marketCount_ Total number of markets created
    function ping() external payable returns (uint256 blockNumber, uint256 marketCount_) {
        emit Ping(msg.sender, block.number, msg.value);
        return (block.number, marketCount);
    }

    /// @notice Get total number of markets created
    function getMarketCount() external view returns (uint256) {
        return marketCount;
    }
}
