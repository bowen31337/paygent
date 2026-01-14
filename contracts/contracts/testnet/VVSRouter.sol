// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title VVSRouter
 * @notice Simplified DEX router for testnet demo
 * @dev Based on Uniswap V2 Router architecture but simplified for demo purposes
 */
contract VVSRouter is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // Pair info
    struct Pair {
        address token0;
        address token1;
        uint256 reserve0;
        uint256 reserve1;
        uint256 totalLiquidity;
    }

    // Constants
    uint256 public constant FEE_DENOMINATOR = 10000;
    uint256 public swapFee = 30; // 0.3%

    // State
    mapping(bytes32 => Pair) public pairs;
    mapping(bytes32 => mapping(address => uint256)) public liquidityBalance;

    // Mock exchange rates (token1 per token0, 18 decimals)
    mapping(bytes32 => uint256) public exchangeRates;

    // Events
    event Swap(
        address indexed sender,
        address indexed tokenIn,
        address indexed tokenOut,
        uint256 amountIn,
        uint256 amountOut,
        address to
    );

    event AddLiquidity(
        address indexed provider,
        address indexed token0,
        address indexed token1,
        uint256 amount0,
        uint256 amount1,
        uint256 liquidity
    );

    event RemoveLiquidity(
        address indexed provider,
        address indexed token0,
        address indexed token1,
        uint256 amount0,
        uint256 amount1,
        uint256 liquidity
    );

    // Demo interaction events
    event CROReceived(address indexed sender, uint256 amount);
    event Ping(address indexed sender, uint256 blockNumber, uint256 value);

    constructor() Ownable(msg.sender) {}

    // ============ External Functions ============

    /**
     * @notice Swap exact tokens for tokens
     * @param tokenIn Input token address
     * @param tokenOut Output token address
     * @param amountIn Amount of input tokens
     * @param amountOutMin Minimum output amount (slippage protection)
     * @param to Recipient address
     */
    function swapExactTokensForTokens(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 amountOutMin,
        address to
    ) external nonReentrant returns (uint256 amountOut) {
        require(amountIn > 0, "Invalid amount");
        require(tokenIn != tokenOut, "Same token");

        // Transfer input tokens
        IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), amountIn);

        // Calculate output amount
        amountOut = getAmountOut(tokenIn, tokenOut, amountIn);
        require(amountOut >= amountOutMin, "Slippage exceeded");

        // Update reserves
        bytes32 pairKey = getPairKey(tokenIn, tokenOut);
        Pair storage pair = pairs[pairKey];

        if (tokenIn < tokenOut) {
            pair.reserve0 += amountIn;
            pair.reserve1 -= amountOut;
        } else {
            pair.reserve1 += amountIn;
            pair.reserve0 -= amountOut;
        }

        // Transfer output tokens
        IERC20(tokenOut).safeTransfer(to, amountOut);

        emit Swap(msg.sender, tokenIn, tokenOut, amountIn, amountOut, to);
    }

    /**
     * @notice Add liquidity to a pair
     * @param token0 First token
     * @param token1 Second token
     * @param amount0 Amount of token0
     * @param amount1 Amount of token1
     */
    function addLiquidity(
        address token0,
        address token1,
        uint256 amount0,
        uint256 amount1
    ) external nonReentrant returns (uint256 liquidity) {
        require(amount0 > 0 && amount1 > 0, "Invalid amounts");

        // Ensure token order
        if (token0 > token1) {
            (token0, token1) = (token1, token0);
            (amount0, amount1) = (amount1, amount0);
        }

        // Transfer tokens
        IERC20(token0).safeTransferFrom(msg.sender, address(this), amount0);
        IERC20(token1).safeTransferFrom(msg.sender, address(this), amount1);

        bytes32 pairKey = getPairKey(token0, token1);
        Pair storage pair = pairs[pairKey];

        // Initialize pair if new
        if (pair.token0 == address(0)) {
            pair.token0 = token0;
            pair.token1 = token1;
        }

        // Calculate liquidity tokens
        if (pair.totalLiquidity == 0) {
            liquidity = sqrt(amount0 * amount1);
        } else {
            uint256 liquidity0 = amount0 * pair.totalLiquidity / pair.reserve0;
            uint256 liquidity1 = amount1 * pair.totalLiquidity / pair.reserve1;
            liquidity = liquidity0 < liquidity1 ? liquidity0 : liquidity1;
        }

        // Update state
        pair.reserve0 += amount0;
        pair.reserve1 += amount1;
        pair.totalLiquidity += liquidity;
        liquidityBalance[pairKey][msg.sender] += liquidity;

        emit AddLiquidity(msg.sender, token0, token1, amount0, amount1, liquidity);
    }

    /**
     * @notice Remove liquidity from a pair
     * @param token0 First token
     * @param token1 Second token
     * @param liquidity Amount of liquidity to remove
     */
    function removeLiquidity(
        address token0,
        address token1,
        uint256 liquidity
    ) external nonReentrant returns (uint256 amount0, uint256 amount1) {
        if (token0 > token1) {
            (token0, token1) = (token1, token0);
        }

        bytes32 pairKey = getPairKey(token0, token1);
        Pair storage pair = pairs[pairKey];

        require(liquidityBalance[pairKey][msg.sender] >= liquidity, "Insufficient liquidity");

        // Calculate token amounts
        amount0 = liquidity * pair.reserve0 / pair.totalLiquidity;
        amount1 = liquidity * pair.reserve1 / pair.totalLiquidity;

        // Update state
        pair.reserve0 -= amount0;
        pair.reserve1 -= amount1;
        pair.totalLiquidity -= liquidity;
        liquidityBalance[pairKey][msg.sender] -= liquidity;

        // Transfer tokens
        IERC20(token0).safeTransfer(msg.sender, amount0);
        IERC20(token1).safeTransfer(msg.sender, amount1);

        emit RemoveLiquidity(msg.sender, token0, token1, amount0, amount1, liquidity);
    }

    // ============ View Functions ============

    function getPairKey(address tokenA, address tokenB) public pure returns (bytes32) {
        (address token0, address token1) = tokenA < tokenB ? (tokenA, tokenB) : (tokenB, tokenA);
        return keccak256(abi.encodePacked(token0, token1));
    }

    function getAmountOut(address tokenIn, address tokenOut, uint256 amountIn) public view returns (uint256) {
        bytes32 pairKey = getPairKey(tokenIn, tokenOut);
        Pair memory pair = pairs[pairKey];

        // If no liquidity, use mock exchange rate
        if (pair.reserve0 == 0 || pair.reserve1 == 0) {
            uint256 rate = exchangeRates[pairKey];
            if (rate == 0) rate = 1e18; // 1:1 default

            uint256 amountInWithFee = amountIn * (FEE_DENOMINATOR - swapFee) / FEE_DENOMINATOR;

            if (tokenIn < tokenOut) {
                return amountInWithFee * rate / 1e18;
            } else {
                return amountInWithFee * 1e18 / rate;
            }
        }

        // Use constant product formula
        uint256 reserveIn;
        uint256 reserveOut;
        if (tokenIn < tokenOut) {
            reserveIn = pair.reserve0;
            reserveOut = pair.reserve1;
        } else {
            reserveIn = pair.reserve1;
            reserveOut = pair.reserve0;
        }

        uint256 amountInWithFee = amountIn * (FEE_DENOMINATOR - swapFee);
        uint256 numerator = amountInWithFee * reserveOut;
        uint256 denominator = reserveIn * FEE_DENOMINATOR + amountInWithFee;

        return numerator / denominator;
    }

    function getReserves(address tokenA, address tokenB) external view returns (uint256 reserveA, uint256 reserveB) {
        bytes32 pairKey = getPairKey(tokenA, tokenB);
        Pair memory pair = pairs[pairKey];

        if (tokenA < tokenB) {
            return (pair.reserve0, pair.reserve1);
        } else {
            return (pair.reserve1, pair.reserve0);
        }
    }

    function quote(address tokenIn, address tokenOut, uint256 amountIn) external view returns (uint256) {
        return getAmountOut(tokenIn, tokenOut, amountIn);
    }

    // ============ Admin Functions ============

    function setSwapFee(uint256 _swapFee) external onlyOwner {
        require(_swapFee <= 1000, "Fee too high"); // Max 10%
        swapFee = _swapFee;
    }

    function setExchangeRate(address tokenA, address tokenB, uint256 rate) external onlyOwner {
        bytes32 pairKey = getPairKey(tokenA, tokenB);
        exchangeRates[pairKey] = rate;
    }

    function initializePair(
        address token0,
        address token1,
        uint256 reserve0,
        uint256 reserve1
    ) external onlyOwner {
        if (token0 > token1) {
            (token0, token1) = (token1, token0);
            (reserve0, reserve1) = (reserve1, reserve0);
        }

        bytes32 pairKey = getPairKey(token0, token1);
        pairs[pairKey] = Pair({
            token0: token0,
            token1: token1,
            reserve0: reserve0,
            reserve1: reserve1,
            totalLiquidity: sqrt(reserve0 * reserve1)
        });
    }

    // ============ Internal Functions ============

    function sqrt(uint256 y) internal pure returns (uint256 z) {
        if (y > 3) {
            z = y;
            uint256 x = y / 2 + 1;
            while (x < z) {
                z = x;
                x = (y / x + x) / 2;
            }
        } else if (y != 0) {
            z = 1;
        }
    }

    // ============ Demo/Interaction Functions ============

    /// @notice Allow contract to receive CRO for demo interactions
    receive() external payable {
        emit CROReceived(msg.sender, msg.value);
    }

    /// @notice Record a discovery/query interaction (for demo purposes)
    /// @return blockNumber Current block number
    /// @return fee Current swap fee in basis points
    function ping() external payable returns (uint256 blockNumber, uint256 fee) {
        emit Ping(msg.sender, block.number, msg.value);
        return (block.number, swapFee);
    }
}
