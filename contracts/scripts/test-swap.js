const hre = require("hardhat");
const fs = require('fs');
const nodePath = require('path');

/**
 * Test swap on VVS-compatible DEX: CRO -> USDC
 */
async function main() {
    console.log("=".repeat(70));
    console.log("Testing VVS Swap: CRO -> USDC on Cronos Testnet");
    console.log("=".repeat(70));
    console.log("");

    // Load deployment config
    const deploymentPath = nodePath.join(__dirname, "..", "deployments", "vvs-testnet.json");
    if (!fs.existsSync(deploymentPath)) {
        console.error("Deployment config not found. Run deploy-vvs-testnet.js first.");
        process.exit(1);
    }
    const deployment = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
    const contracts = deployment.contracts;

    console.log("Contract Addresses:");
    console.log("  Router:", contracts.router);
    console.log("  WCRO:", contracts.wcro);
    console.log("  tUSDC:", contracts.tUSDC);
    console.log("");

    // Get signer
    const [signer] = await hre.ethers.getSigners();
    console.log("Signer address:", signer.address);

    // Check initial balances
    const croBalance = await signer.provider.getBalance(signer.address);
    console.log("CRO balance:", hre.ethers.formatEther(croBalance), "CRO");

    const usdc = await hre.ethers.getContractAt("TestUSDC", contracts.tUSDC);
    const usdcBalanceBefore = await usdc.balanceOf(signer.address);
    console.log("USDC balance before:", hre.ethers.formatUnits(usdcBalanceBefore, 6), "tUSDC");
    console.log("");

    // Get router contract
    const router = await hre.ethers.getContractAt("UniswapV2Router", contracts.router);

    // Swap parameters
    const swapAmountCRO = hre.ethers.parseEther("1"); // 1 CRO
    const swapPath = [contracts.wcro, contracts.tUSDC]; // CRO -> USDC
    const deadline = Math.floor(Date.now() / 1000) + 600; // 10 minutes

    // Get quote first
    console.log("1. Getting quote for 1 CRO -> USDC...");
    try {
        const amountsOut = await router.getAmountsOut(swapAmountCRO, swapPath);
        const expectedUSDC = amountsOut[1];
        console.log("   Expected output:", hre.ethers.formatUnits(expectedUSDC, 6), "tUSDC");

        // Calculate minimum with 5% slippage
        const minAmountOut = expectedUSDC * 95n / 100n;
        console.log("   Min output (5% slippage):", hre.ethers.formatUnits(minAmountOut, 6), "tUSDC");
        console.log("");

        // Execute swap
        console.log("2. Executing swap: 1 CRO -> USDC...");
        const tx = await router.swapExactETHForTokens(
            minAmountOut,
            swapPath,
            signer.address,
            deadline,
            { value: swapAmountCRO }
        );

        console.log("   Transaction hash:", tx.hash);
        console.log("   Waiting for confirmation...");

        const receipt = await tx.wait();
        console.log("   Confirmed in block:", receipt.blockNumber);
        console.log("   Gas used:", receipt.gasUsed.toString());
        console.log("");

        // Check final balances
        console.log("3. Checking final balances...");
        const croBalanceAfter = await signer.provider.getBalance(signer.address);
        const usdcBalanceAfter = await usdc.balanceOf(signer.address);

        console.log("   CRO balance after:", hre.ethers.formatEther(croBalanceAfter), "CRO");
        console.log("   USDC balance after:", hre.ethers.formatUnits(usdcBalanceAfter, 6), "tUSDC");
        console.log("");

        // Calculate differences
        const croDiff = croBalance - croBalanceAfter;
        const usdcDiff = usdcBalanceAfter - usdcBalanceBefore;

        console.log("=".repeat(70));
        console.log("SWAP RESULTS");
        console.log("=".repeat(70));
        console.log("  CRO spent:", hre.ethers.formatEther(croDiff), "CRO (including gas)");
        console.log("  USDC received:", hre.ethers.formatUnits(usdcDiff, 6), "tUSDC");
        console.log("  Effective rate:", (parseFloat(hre.ethers.formatUnits(usdcDiff, 6)) / 1).toFixed(4), "USDC per CRO");
        console.log("  Transaction:", `https://explorer.cronos.org/testnet/tx/${tx.hash}`);
        console.log("=".repeat(70));
        console.log("");
        console.log("✅ Swap successful!");

    } catch (err) {
        console.error("Swap failed:", err.message);
        if (err.data) {
            console.error("Error data:", err.data);
        }
        process.exit(1);
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
