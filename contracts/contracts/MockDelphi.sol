// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title MockDelphi
 * @dev Simplified prediction market contract for Cronos testnet
 *
 * This is a mock implementation for hackathon/testing purposes.
 * It simulates prediction market functionality:
 * - Create prediction markets with multiple outcomes
 * - Place bets on outcomes
 * - Resolve markets
 * - Claim winnings
 */
contract MockDelphi is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // Market struct
    struct Market {
        bytes32 marketId;
        string question;
        string category;
        string[] outcomes;
        uint256 endTime;
        uint256 resolutionTime;
        uint256 totalVolume;
        uint256 minBet;
        uint256 maxBet;
        bool isActive;
        bool isResolved;
        uint256 winningOutcome;  // Index of winning outcome (0-indexed)
        mapping(uint256 => uint256) outcomeTotals;  // Total bet on each outcome
    }

    // Bet struct
    struct Bet {
        bytes32 betId;
        bytes32 marketId;
        address bettor;
        uint256 outcomeIndex;
        uint256 amount;
        uint256 timestamp;
        bool claimed;
    }

    // State variables
    IERC20 public bettingToken;  // USDC for betting
    uint256 public marketCounter;
    uint256 public betCounter;
    uint256 public defaultFee;  // Fee in basis points (100 = 1%)
    address public feeCollector;

    mapping(bytes32 => Market) public markets;
    mapping(bytes32 => Bet) public bets;
    mapping(address => bytes32[]) public bettorBets;
    bytes32[] public allMarketIds;

    // Events
    event MarketCreated(
        bytes32 indexed marketId,
        string question,
        string category,
        uint256 endTime,
        uint256 numOutcomes
    );

    event BetPlaced(
        bytes32 indexed betId,
        bytes32 indexed marketId,
        address indexed bettor,
        uint256 outcomeIndex,
        uint256 amount
    );

    event MarketResolved(
        bytes32 indexed marketId,
        uint256 winningOutcome,
        string winningOutcomeName
    );

    event WinningsClaimed(
        bytes32 indexed betId,
        address indexed bettor,
        uint256 payout
    );

    event FeeUpdated(uint256 newFee);

    constructor(address _bettingToken) Ownable(msg.sender) {
        bettingToken = IERC20(_bettingToken);
        defaultFee = 100;  // 1% fee
        feeCollector = msg.sender;

        // Create some initial markets for testing
        _createInitialMarkets();
    }

    /**
     * @dev Create initial markets for testing
     */
    function _createInitialMarkets() internal {
        string[] memory yesNo = new string[](2);
        yesNo[0] = "Yes";
        yesNo[1] = "No";

        string[] memory chains = new string[](3);
        chains[0] = "Ethereum";
        chains[1] = "Solana";
        chains[2] = "Cronos";

        // Market 1: BTC price prediction
        _createMarket(
            "Will Bitcoin exceed $50,000 by January 31, 2025?",
            "crypto",
            yesNo,
            block.timestamp + 30 days,
            1e6,    // Min bet: 1 USDC
            1000e6  // Max bet: 1000 USDC
        );

        // Market 2: Cronos TVL prediction
        _createMarket(
            "Will Cronos network TVL exceed $1B in Q1 2025?",
            "defi",
            yesNo,
            block.timestamp + 60 days,
            1e6,
            500e6
        );

        // Market 3: Chain comparison
        _createMarket(
            "Which blockchain will have higher daily active addresses in February 2025?",
            "crypto",
            chains,
            block.timestamp + 45 days,
            5e6,
            200e6
        );
    }

    /**
     * @dev Internal function to create a market
     */
    function _createMarket(
        string memory question,
        string memory category,
        string[] memory outcomes,
        uint256 endTime,
        uint256 minBet,
        uint256 maxBet
    ) internal returns (bytes32 marketId) {
        require(outcomes.length >= 2, "Need at least 2 outcomes");
        require(endTime > block.timestamp, "End time must be in future");

        marketId = keccak256(abi.encodePacked(
            question,
            block.timestamp,
            marketCounter++
        ));

        Market storage market = markets[marketId];
        market.marketId = marketId;
        market.question = question;
        market.category = category;
        market.outcomes = outcomes;
        market.endTime = endTime;
        market.resolutionTime = endTime + 1 days;
        market.minBet = minBet;
        market.maxBet = maxBet;
        market.isActive = true;
        market.isResolved = false;

        allMarketIds.push(marketId);

        emit MarketCreated(marketId, question, category, endTime, outcomes.length);
    }

    /**
     * @dev Create a new prediction market (owner only for testing)
     */
    function createMarket(
        string calldata question,
        string calldata category,
        string[] calldata outcomes,
        uint256 endTime,
        uint256 minBet,
        uint256 maxBet
    ) external onlyOwner returns (bytes32) {
        return _createMarket(question, category, outcomes, endTime, minBet, maxBet);
    }

    /**
     * @dev Place a bet on a market outcome
     */
    function placeBet(
        bytes32 marketId,
        uint256 outcomeIndex,
        uint256 amount
    ) external nonReentrant returns (bytes32 betId) {
        Market storage market = markets[marketId];
        require(market.isActive, "Market not active");
        require(!market.isResolved, "Market already resolved");
        require(block.timestamp < market.endTime, "Betting period ended");
        require(outcomeIndex < market.outcomes.length, "Invalid outcome");
        require(amount >= market.minBet, "Below minimum bet");
        require(amount <= market.maxBet, "Above maximum bet");

        // Transfer betting tokens
        bettingToken.safeTransferFrom(msg.sender, address(this), amount);

        // Create bet
        betId = keccak256(abi.encodePacked(
            marketId,
            msg.sender,
            block.timestamp,
            betCounter++
        ));

        bets[betId] = Bet({
            betId: betId,
            marketId: marketId,
            bettor: msg.sender,
            outcomeIndex: outcomeIndex,
            amount: amount,
            timestamp: block.timestamp,
            claimed: false
        });

        bettorBets[msg.sender].push(betId);

        // Update market totals
        market.totalVolume += amount;
        market.outcomeTotals[outcomeIndex] += amount;

        emit BetPlaced(betId, marketId, msg.sender, outcomeIndex, amount);
    }

    /**
     * @dev Resolve a market (owner only)
     */
    function resolveMarket(bytes32 marketId, uint256 winningOutcome) external onlyOwner {
        Market storage market = markets[marketId];
        require(market.isActive, "Market not active");
        require(!market.isResolved, "Already resolved");
        require(winningOutcome < market.outcomes.length, "Invalid outcome");

        market.isResolved = true;
        market.isActive = false;
        market.winningOutcome = winningOutcome;

        emit MarketResolved(marketId, winningOutcome, market.outcomes[winningOutcome]);
    }

    /**
     * @dev Claim winnings from a resolved market
     */
    function claimWinnings(bytes32 betId) external nonReentrant returns (uint256 payout) {
        Bet storage bet = bets[betId];
        require(bet.bettor == msg.sender, "Not your bet");
        require(!bet.claimed, "Already claimed");

        Market storage market = markets[bet.marketId];
        require(market.isResolved, "Market not resolved");

        bet.claimed = true;

        // Check if bet won
        if (bet.outcomeIndex == market.winningOutcome) {
            // Calculate payout proportionally
            uint256 winningPool = market.outcomeTotals[market.winningOutcome];
            uint256 losingPool = market.totalVolume - winningPool;

            if (winningPool > 0) {
                // Payout = original bet + share of losing pool
                uint256 winnings = (bet.amount * losingPool) / winningPool;
                uint256 fee = (winnings * defaultFee) / 10000;
                payout = bet.amount + winnings - fee;

                // Transfer payout
                bettingToken.safeTransfer(msg.sender, payout);

                // Transfer fee
                if (fee > 0) {
                    bettingToken.safeTransfer(feeCollector, fee);
                }
            } else {
                // Edge case: refund if no one bet on winning outcome
                payout = bet.amount;
                bettingToken.safeTransfer(msg.sender, payout);
            }

            emit WinningsClaimed(betId, msg.sender, payout);
        }

        return payout;
    }

    /**
     * @dev Get market details
     */
    function getMarket(bytes32 marketId) external view returns (
        string memory question,
        string memory category,
        string[] memory outcomes,
        uint256 endTime,
        uint256 totalVolume,
        uint256 minBet,
        uint256 maxBet,
        bool isActive,
        bool isResolved,
        uint256 winningOutcome
    ) {
        Market storage market = markets[marketId];
        return (
            market.question,
            market.category,
            market.outcomes,
            market.endTime,
            market.totalVolume,
            market.minBet,
            market.maxBet,
            market.isActive,
            market.isResolved,
            market.winningOutcome
        );
    }

    /**
     * @dev Get outcome totals for a market
     */
    function getOutcomeTotals(bytes32 marketId) external view returns (uint256[] memory) {
        Market storage market = markets[marketId];
        uint256[] memory totals = new uint256[](market.outcomes.length);
        for (uint256 i = 0; i < market.outcomes.length; i++) {
            totals[i] = market.outcomeTotals[i];
        }
        return totals;
    }

    /**
     * @dev Get odds for each outcome (as implied probabilities)
     */
    function getOdds(bytes32 marketId) external view returns (uint256[] memory) {
        Market storage market = markets[marketId];
        uint256[] memory odds = new uint256[](market.outcomes.length);

        if (market.totalVolume == 0) {
            // Equal odds if no bets
            for (uint256 i = 0; i < market.outcomes.length; i++) {
                odds[i] = 10000 / market.outcomes.length;  // In basis points
            }
        } else {
            for (uint256 i = 0; i < market.outcomes.length; i++) {
                odds[i] = (market.outcomeTotals[i] * 10000) / market.totalVolume;
            }
        }
        return odds;
    }

    /**
     * @dev Get all markets
     */
    function getAllMarkets() external view returns (bytes32[] memory) {
        return allMarketIds;
    }

    /**
     * @dev Get bettor's bets
     */
    function getBettorBets(address bettor) external view returns (bytes32[] memory) {
        return bettorBets[bettor];
    }

    /**
     * @dev Get bet details
     */
    function getBet(bytes32 betId) external view returns (
        bytes32 marketId,
        address bettor,
        uint256 outcomeIndex,
        uint256 amount,
        uint256 timestamp,
        bool claimed
    ) {
        Bet storage bet = bets[betId];
        return (
            bet.marketId,
            bet.bettor,
            bet.outcomeIndex,
            bet.amount,
            bet.timestamp,
            bet.claimed
        );
    }

    /**
     * @dev Update fee (owner only)
     */
    function setFee(uint256 newFee) external onlyOwner {
        require(newFee <= 500, "Fee too high (max 5%)");
        defaultFee = newFee;
        emit FeeUpdated(newFee);
    }

    /**
     * @dev Update fee collector (owner only)
     */
    function setFeeCollector(address newCollector) external onlyOwner {
        require(newCollector != address(0), "Invalid address");
        feeCollector = newCollector;
    }

    /**
     * @dev Emergency withdraw (owner only)
     */
    function emergencyWithdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).safeTransfer(owner(), amount);
    }
}
