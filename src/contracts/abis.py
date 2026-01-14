"""
Smart contract ABIs for deployed testnet contracts.
"""

# VVSRouter ABI
VVS_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenIn", "type": "address"},
            {"internalType": "address", "name": "tokenOut", "type": "address"},
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address", "name": "to", "type": "address"}
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"}
        ],
        "name": "getAmountOut",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"}
        ],
        "name": "quote",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"}
        ],
        "name": "getReserves",
        "outputs": [
            {"internalType": "uint256", "name": "reserveA", "type": "uint256"},
            {"internalType": "uint256", "name": "reserveB", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
]

# MoonlanderPerp ABI
MOONLANDER_PERP_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "_asset", "type": "string"},
            {"internalType": "uint256", "name": "_collateralAmount", "type": "uint256"},
            {"internalType": "uint256", "name": "_sizeDelta", "type": "uint256"},
            {"internalType": "bool", "name": "_isLong", "type": "bool"}
        ],
        "name": "increasePosition",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "string", "name": "_asset", "type": "string"},
            {"internalType": "uint256", "name": "_collateralDelta", "type": "uint256"},
            {"internalType": "uint256", "name": "_sizeDelta", "type": "uint256"},
            {"internalType": "bool", "name": "_isLong", "type": "bool"}
        ],
        "name": "decreasePosition",
        "outputs": [{"internalType": "int256", "name": "pnl", "type": "int256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "_account", "type": "address"},
            {"internalType": "string", "name": "_asset", "type": "string"},
            {"internalType": "bool", "name": "_isLong", "type": "bool"}
        ],
        "name": "getPosition",
        "outputs": [
            {"internalType": "uint256", "name": "size", "type": "uint256"},
            {"internalType": "uint256", "name": "collateral", "type": "uint256"},
            {"internalType": "uint256", "name": "averagePrice", "type": "uint256"},
            {"internalType": "uint256", "name": "entryFundingRate", "type": "uint256"},
            {"internalType": "uint256", "name": "lastUpdatedTime", "type": "uint256"},
            {"internalType": "bool", "name": "isLong", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "string", "name": "_asset", "type": "string"}],
        "name": "getPrice",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalOpenInterestLong",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalOpenInterestShort",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "collateralToken",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "fundingRate",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
]

# DelphiPrediction ABI
DELPHI_PREDICTION_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "marketId", "type": "uint256"},
            {"internalType": "bool", "name": "isYes", "type": "bool"},
            {"internalType": "uint256", "name": "stake", "type": "uint256"}
        ],
        "name": "placeBet",
        "outputs": [
            {"internalType": "uint256", "name": "betId", "type": "uint256"},
            {"internalType": "uint256", "name": "shares", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "marketId", "type": "uint256"}],
        "name": "getMarket",
        "outputs": [
            {"internalType": "string", "name": "question", "type": "string"},
            {"internalType": "uint256", "name": "endTime", "type": "uint256"},
            {"internalType": "uint256", "name": "totalYesShares", "type": "uint256"},
            {"internalType": "uint256", "name": "totalNoShares", "type": "uint256"},
            {"internalType": "uint256", "name": "totalYesStake", "type": "uint256"},
            {"internalType": "uint256", "name": "totalNoStake", "type": "uint256"},
            {"internalType": "uint8", "name": "outcome", "type": "uint8"},
            {"internalType": "bool", "name": "resolved", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "marketId", "type": "uint256"}],
        "name": "getPrice",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "marketId", "type": "uint256"}],
        "name": "getOdds",
        "outputs": [
            {"internalType": "uint256", "name": "yesOdds", "type": "uint256"},
            {"internalType": "uint256", "name": "noOdds", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "marketCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "collateralToken",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "platformFee",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
]

# ERC20 ABI for token operations
ERC20_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "spender", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "address", "name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
]
