// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title DelphiAdapter
 * @dev Adapter contract for Delphi prediction market operations
 */
interface IDelphiMarket {
    function placeBet(
        bytes32 marketId,
        uint256 outcome,
        uint256 amount,
        uint256 odds
    ) external returns (bytes32 betId);

    function claimWinnings(bytes32 betId) external returns (uint256 payout, uint256 profit);

    function getMarketOutcome(bytes32 marketId) external view returns (uint256 winningOutcome, bool resolved);

    function getBet(bytes32 betId) external view returns (
        bytes32 marketId,
        uint256 outcome,
        uint256 amount,
        uint256 odds,
        uint256 payout,
        bool claimed
    );
}

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract DelphiAdapter {
    address public marketsRegistry;
    address public feeCollector;
    uint256 public defaultFee; // Fee in basis points

    address public owner;

    struct Bet {
        bytes32 betId;
        bytes32 marketId;
        uint256 outcome;
        uint256 amount;
        uint256 odds;
        uint256 payout;
        uint256 fee;
        bool claimed;
        address better;
        uint256 placedAt;
    }

    struct Market {
        bytes32 marketId;
        string question;
        uint256[] outcomes;
        uint256 endTime;
        uint256 resolutionTime;
        bool active;
        uint256 totalVolume;
    }

    mapping(bytes32 => Bet) public bets;
    mapping(bytes32 => Market) public markets;
    mapping(address => bytes32[]) public betterBets;

    event BetPlaced(
        bytes32 indexed betId,
        bytes32 indexed marketId,
        address indexed better,
        uint256 outcome,
        uint256 amount,
        uint256 odds,
        uint256 fee
    );
    event BetClaimed(
        bytes32 indexed betId,
        address indexed better,
        uint256 payout,
        uint256 profit
    );
    event MarketResolved(
        bytes32 indexed marketId,
        uint256 winningOutcome
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    constructor(
        address _marketsRegistry,
        address _feeCollector,
        uint256 _defaultFee
    ) {
        owner = msg.sender;
        marketsRegistry = _marketsRegistry;
        feeCollector = _feeCollector;
        defaultFee = _defaultFee;
    }

    function placeBet(
        bytes32 marketId,
        uint256 outcome,
        uint256 amount,
        uint256 odds
    ) external returns (bytes32) {
        require(marketId != bytes32(0), "Invalid market ID");
        require(amount > 0, "Amount must be greater than 0");
        require(outcome > 0, "Outcome must be greater than 0");

        // Calculate fee
        uint256 fee = (amount * defaultFee) / 10000;
        uint256 netAmount = amount - fee;

        // Transfer fee to collector
        if (fee > 0) {
            // This would need actual token transfer logic
            // For now, just emit event
        }

        bytes32 betId = IDelphiMarket(marketsRegistry).placeBet(
            marketId,
            outcome,
            netAmount,
            odds
        );

        bets[betId] = Bet({
            betId: betId,
            marketId: marketId,
            outcome: outcome,
            amount: amount,
            odds: odds,
            payout: 0, // Will be updated when claimed
            fee: fee,
            claimed: false,
            better: msg.sender,
            placedAt: block.timestamp
        });

        betterBets[msg.sender].push(betId);

        emit BetPlaced(betId, marketId, msg.sender, outcome, amount, odds, fee);
        return betId;
    }

    function claimWinnings(bytes32 betId) external returns (uint256 payout, uint256 profit) {
        Bet storage bet = bets[betId];
        require(bet.better == msg.sender, "Not bet owner");
        require(!bet.claimed, "Bet already claimed");

        (payout, profit) = IDelphiMarket(marketsRegistry).claimWinnings(betId);

        bet.claimed = true;
        bet.payout = payout;

        // Transfer payout to better (minus any additional fees)
        // This would need actual token transfer logic

        emit BetClaimed(betId, msg.sender, payout, profit);
        return (payout, profit);
    }

    function getBet(bytes32 betId) external view returns (
        bytes32 marketId,
        uint256 outcome,
        uint256 amount,
        uint256 odds,
        uint256 payout,
        bool claimed,
        address better,
        uint256 placedAt
    ) {
        Bet storage bet = bets[betId];
        return (
            bet.marketId,
            bet.outcome,
            bet.amount,
            bet.odds,
            bet.payout,
            bet.claimed,
            bet.better,
            bet.placedAt
        );
    }

    function getMarketOutcome(bytes32 marketId) external view returns (
        uint256 winningOutcome,
        bool resolved
    ) {
        return IDelphiMarket(marketsRegistry).getMarketOutcome(marketId);
    }

    function getBetterBets(address better) external view returns (bytes32[] memory) {
        return betterBets[better];
    }

    function getMarketDetails(bytes32 marketId) external view returns (
        bytes32 id,
        string memory question,
        uint256[] memory outcomes,
        uint256 endTime,
        uint256 resolutionTime,
        bool active,
        uint256 totalVolume
    ) {
        Market storage market = markets[marketId];
        return (
            market.marketId,
            market.question,
            market.outcomes,
            market.endTime,
            market.resolutionTime,
            market.active,
            market.totalVolume
        );
    }

    function updateFee(uint256 newFee) external onlyOwner {
        require(newFee <= 1000, "Fee cannot exceed 10%"); // Max 10%
        defaultFee = newFee;
    }

    function setMarketsRegistry(address newRegistry) external onlyOwner {
        marketsRegistry = newRegistry;
    }

    function setFeeCollector(address newCollector) external onlyOwner {
        feeCollector = newCollector;
    }
}