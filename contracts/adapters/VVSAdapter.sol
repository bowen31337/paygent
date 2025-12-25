// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title VVSAdapter
 * @dev Adapter contract for VVS Finance DEX operations
 */
interface IUniswapV2Router {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);

    function swapTokensForExactTokens(
        uint256 amountOut,
        uint256 amountInMax,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);

    function addLiquidity(
        address tokenA,
        address tokenB,
        uint256 amountADesired,
        uint256 amountBDesired,
        uint256 amountAMin,
        uint256 amountBMin,
        address to,
        uint256 deadline
    ) external returns (uint256 amountA, uint256 amountB, uint256 liquidity);

    function removeLiquidity(
        address tokenA,
        address tokenB,
        uint256 liquidity,
        uint256 amountAMin,
        uint256 amountBMin,
        address to,
        uint256 deadline
    ) external returns (uint256 amountA, uint256 amountB);
}

interface IUniswapV2Factory {
    function getPair(address tokenA, address tokenB) external view returns (address pair);
}

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract VVSAdapter {
    // State variables
    address public router;
    address public weth;
    address public factory;
    address public owner;

    // Structs
    struct Swap {
        uint256 amountIn;
        uint256 amountOut;
        address[] path;
        uint256 deadline;
        uint256 fee;
    }

    struct LiquidityPosition {
        address tokenA;
        address tokenB;
        uint256 amountA;
        uint256 amountB;
        uint256 liquidity;
        address provider;
    }

    // Mappings
    mapping(bytes32 => Swap) public swaps;
    mapping(bytes32 => LiquidityPosition) public liquidityPositions;

    // Events
    event SwapExecuted(
        bytes32 indexed swapId,
        address indexed user,
        uint256 amountIn,
        uint256 amountOut,
        address[] path
    );
    event LiquidityAdded(
        bytes32 indexed positionId,
        address indexed user,
        address tokenA,
        address tokenB,
        uint256 amountA,
        uint256 amountB,
        uint256 liquidity
    );
    event LiquidityRemoved(
        bytes32 indexed positionId,
        address indexed user,
        uint256 amountA,
        uint256 amountB
    );

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    /**
     * @dev Constructor
     * @param _router VVS router address
     * @param _weth WETH token address
     * @param _factory VVS factory address
     */
    constructor(
        address _router,
        address _weth,
        address _factory
    ) {
        owner = msg.sender;
        router = _router;
        weth = _weth;
        factory = _factory;
    }

    // ==================== External Functions ====================

    /**
     * @dev Executes a token swap
     * @param path Array of token addresses (input -> output)
     * @param amountIn Amount of input tokens
     * @param amountOutMin Minimum expected output amount
     * @param deadline Timestamp deadline for the swap
     * @return swapId Unique identifier for the swap
     */
    function swapTokens(
        address[] calldata path,
        uint256 amountIn,
        uint256 amountOutMin,
        uint256 deadline
    ) external returns (bytes32) {
        require(path.length >= 2, "Invalid path");
        require(amountIn > 0, "Amount must be greater than 0");
        require(deadline > block.timestamp, "Deadline must be in the future");

        // Approve router to spend tokens
        IERC20(path[0]).approve(router, amountIn);

        uint256[] memory amounts = IUniswapV2Router(router).swapExactTokensForTokens(
            amountIn,
            amountOutMin,
            path,
            msg.sender,
            deadline
        );

        bytes32 swapId = keccak256(abi.encodePacked(msg.sender, block.timestamp, amountIn));

        swaps[swapId] = Swap({
            amountIn: amountIn,
            amountOut: amounts[amounts.length - 1],
            path: path,
            deadline: deadline,
            fee: 0 // Could implement fee logic here
        });

        emit SwapExecuted(swapId, msg.sender, amountIn, amounts[amounts.length - 1], path);
        return swapId;
    }

    /**
     * @dev Adds liquidity to a pool
     * @param tokenA First token address
     * @param tokenB Second token address
     * @param amountADesired Desired amount of token A
     * @param amountBDesired Desired amount of token B
     * @param amountAMin Minimum amount of token A
     * @param amountBMin Minimum amount of token B
     * @param deadline Timestamp deadline
     * @return positionId Unique identifier for the position
     */
    function addLiquidity(
        address tokenA,
        address tokenB,
        uint256 amountADesired,
        uint256 amountBDesired,
        uint256 amountAMin,
        uint256 amountBMin,
        uint256 deadline
    ) external returns (bytes32) {
        require(tokenA != address(0) && tokenB != address(0), "Invalid tokens");
        require(amountADesired > 0 && amountBDesired > 0, "Amounts must be greater than 0");
        require(deadline > block.timestamp, "Deadline must be in the future");

        // Approve router to spend tokens
        IERC20(tokenA).approve(router, amountADesired);
        IERC20(tokenB).approve(router, amountBDesired);

        (uint256 amountA, uint256 amountB, uint256 liquidity) = IUniswapV2Router(router).addLiquidity(
            tokenA,
            tokenB,
            amountADesired,
            amountBDesired,
            amountAMin,
            amountBMin,
            msg.sender,
            deadline
        );

        bytes32 positionId = keccak256(abi.encodePacked(msg.sender, tokenA, tokenB, block.timestamp));

        liquidityPositions[positionId] = LiquidityPosition({
            tokenA: tokenA,
            tokenB: tokenB,
            amountA: amountA,
            amountB: amountB,
            liquidity: liquidity,
            provider: msg.sender
        });

        emit LiquidityAdded(positionId, msg.sender, tokenA, tokenB, amountA, amountB, liquidity);
        return positionId;
    }

    /**
     * @dev Removes liquidity from a pool
     * @param tokenA First token address
     * @param tokenB Second token address
     * @param liquidity Amount of liquidity tokens to burn
     * @param amountAMin Minimum amount of token A to receive
     * @param amountBMin Minimum amount of token B to receive
     * @param deadline Timestamp deadline
     * @return positionId Unique identifier for the removal
     */
    function removeLiquidity(
        address tokenA,
        address tokenB,
        uint256 liquidity,
        uint256 amountAMin,
        uint256 amountBMin,
        uint256 deadline
    ) external returns (bytes32) {
        require(tokenA != address(0) && tokenB != address(0), "Invalid tokens");
        require(liquidity > 0, "Liquidity must be greater than 0");
        require(deadline > block.timestamp, "Deadline must be in the future");

        // Find LP token
        address pair = IUniswapV2Factory(factory).getPair(tokenA, tokenB);
        require(pair != address(0), "Pair does not exist");

        // Approve router to spend LP tokens
        IERC20(pair).approve(router, liquidity);

        (uint256 amountA, uint256 amountB) = IUniswapV2Router(router).removeLiquidity(
            tokenA,
            tokenB,
            liquidity,
            amountAMin,
            amountBMin,
            msg.sender,
            deadline
        );

        bytes32 positionId = keccak256(abi.encodePacked(msg.sender, tokenA, tokenB, liquidity, block.timestamp));

        emit LiquidityRemoved(positionId, msg.sender, amountA, amountB);
        return positionId;
    }

    // ==================== View Functions ====================

    /**
     * @dev Gets the pair address for two tokens
     * @param tokenA First token address
     * @param tokenB Second token address
     * @return Pair contract address
     */
    function getPair(address tokenA, address tokenB) external view returns (address) {
        return IUniswapV2Factory(factory).getPair(tokenA, tokenB);
    }

    /**
     * @dev Gets the reserves for a token pair
     * @param tokenA First token address
     * @param tokenB Second token address
     * @return reserveA Reserve of token A
     * @return reserveB Reserve of token B
     */
    function getReserves(address tokenA, address tokenB) external view returns (uint256 reserveA, uint256 reserveB) {
        address pair = IUniswapV2Factory(factory).getPair(tokenA, tokenB);
        if (pair == address(0)) {
            return (0, 0);
        }
        (reserveA, reserveB, ) = IUniswapV2Pair(pair).getReserves();
    }

    /**
     * @dev Estimates the output amount for a swap
     * @param path Array of token addresses
     * @param amountIn Input amount
     * @return amounts Array of amounts for each step
     */
    function estimateSwap(
        address[] calldata path,
        uint256 amountIn
    ) external view returns (uint256[] memory amounts) {
        return IUniswapV2Router(router).getAmountsOut(amountIn, path);
    }
}

interface IUniswapV2Pair {
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
    function token0() external view returns (address);
    function token1() external view returns (address);
}