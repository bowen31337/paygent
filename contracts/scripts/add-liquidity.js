const hre = require("hardhat");
const fs = require('fs');
const path = require('path');

/**
 * Add liquidity to existing VVS-compatible DEX contracts
 * Uses the deployment config from contracts/deployments/vvs-testnet.json
 */
async function main() {
    console.log("=".repeat(70));
    console.log("Adding Liquidity to VVS-Compatible DEX on Cronos Testnet");
    console.log("=".repeat(70));
    console.log("");

    // Load deployment config
    const deploymentPath = path.join(__dirname, "..", "deployments", "vvs-testnet.json");
    if (!fs.existsSync(deploymentPath)) {
        console.error("Deployment config not found. Run deploy-vvs-testnet.js first.");
        process.exit(1);
    }
    const deployment = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
    const contracts = deployment.contracts;

    console.log("Loaded deployment config:");
    console.log("  Router:", contracts.router);
    console.log("  WCRO:", contracts.wcro);
    console.log("  tUSDC:", contracts.tUSDC);
    console.log("  tUSDT:", contracts.tUSDT);
    console.log("  tVVS:", contracts.tVVS);
    console.log("");

    // Get deployer account
    const [deployer] = await hre.ethers.getSigners();
    console.log("Deployer address:", deployer.address);
    const balance = await deployer.provider.getBalance(deployer.address);
    console.log("Balance:", hre.ethers.formatEther(balance), "CRO");
    console.log("");

    // Get contract instances
    const wcro = await hre.ethers.getContractAt("WCRO", contracts.wcro);
    const testUSDC = await hre.ethers.getContractAt("TestUSDC", contracts.tUSDC);
    const testUSDT = await hre.ethers.getContractAt("TestUSDT", contracts.tUSDT);
    const testVVS = await hre.ethers.getContractAt("TestVVS", contracts.tVVS);
    const router = await hre.ethers.getContractAt("UniswapV2Router", contracts.router);

    // ========== 1. Call Faucet Functions ==========
    console.log("1. Calling Faucet Functions...");

    try {
        console.log("   Calling tUSDC.faucet()...");
        const usdcTx = await testUSDC.faucet();
        await usdcTx.wait();
        const usdcBalance = await testUSDC.balanceOf(deployer.address);
        console.log("   tUSDC balance:", hre.ethers.formatUnits(usdcBalance, 6));
    } catch (err) {
        console.log("   tUSDC faucet failed:", err.message);
    }

    try {
        console.log("   Calling tUSDT.faucet()...");
        const usdtTx = await testUSDT.faucet();
        await usdtTx.wait();
        const usdtBalance = await testUSDT.balanceOf(deployer.address);
        console.log("   tUSDT balance:", hre.ethers.formatUnits(usdtBalance, 6));
    } catch (err) {
        console.log("   tUSDT faucet failed:", err.message);
    }

    try {
        console.log("   Calling tVVS.faucet()...");
        const vvsTx = await testVVS.faucet();
        await vvsTx.wait();
        const vvsBalance = await testVVS.balanceOf(deployer.address);
        console.log("   tVVS balance:", hre.ethers.formatEther(vvsBalance));
    } catch (err) {
        console.log("   tVVS faucet failed:", err.message);
    }

    // ========== 2. Wrap CRO ==========
    console.log("\n2. Wrapping CRO...");
    const wrapAmount = hre.ethers.parseEther("20"); // 20 CRO
    try {
        console.log("   Wrapping 20 CRO to WCRO...");
        const wrapTx = await wcro.deposit({ value: wrapAmount });
        await wrapTx.wait();
        const wcroBalance = await wcro.balanceOf(deployer.address);
        console.log("   WCRO balance:", hre.ethers.formatEther(wcroBalance));
    } catch (err) {
        console.log("   Wrapping failed:", err.message);
    }

    // ========== 3. Approve Tokens ==========
    console.log("\n3. Approving tokens for Router...");
    const maxApproval = hre.ethers.MaxUint256;

    try {
        await (await wcro.approve(contracts.router, maxApproval)).wait();
        console.log("   WCRO approved");
        await (await testUSDC.approve(contracts.router, maxApproval)).wait();
        console.log("   tUSDC approved");
        await (await testUSDT.approve(contracts.router, maxApproval)).wait();
        console.log("   tUSDT approved");
        await (await testVVS.approve(contracts.router, maxApproval)).wait();
        console.log("   tVVS approved");
    } catch (err) {
        console.log("   Approval failed:", err.message);
    }

    // ========== 4. Add Liquidity to Pools ==========
    console.log("\n4. Adding Liquidity to Pools...");

    // WCRO-USDC pool
    console.log("\n   Creating WCRO-tUSDC pool...");
    const wcroAmount1 = hre.ethers.parseEther("5"); // 5 WCRO
    const usdcAmount = 50n * 10n ** 6n; // 50 USDC (6 decimals)

    try {
        const addLiqTx1 = await router.addLiquidity(
            contracts.wcro,
            contracts.tUSDC,
            wcroAmount1,
            usdcAmount,
            0,
            0,
            deployer.address,
            Math.floor(Date.now() / 1000) + 3600
        );
        await addLiqTx1.wait();
        console.log("   WCRO-tUSDC pool created (5 WCRO + 50 tUSDC)");
    } catch (err) {
        console.log("   Failed:", err.message);
    }

    // WCRO-USDT pool
    console.log("   Creating WCRO-tUSDT pool...");
    const wcroAmount2 = hre.ethers.parseEther("5"); // 5 WCRO
    const usdtAmount = 50n * 10n ** 6n; // 50 USDT

    try {
        const addLiqTx2 = await router.addLiquidity(
            contracts.wcro,
            contracts.tUSDT,
            wcroAmount2,
            usdtAmount,
            0,
            0,
            deployer.address,
            Math.floor(Date.now() / 1000) + 3600
        );
        await addLiqTx2.wait();
        console.log("   WCRO-tUSDT pool created (5 WCRO + 50 tUSDT)");
    } catch (err) {
        console.log("   Failed:", err.message);
    }

    // USDC-USDT pool
    console.log("   Creating tUSDC-tUSDT pool...");
    const usdcAmount2 = 100n * 10n ** 6n; // 100 USDC
    const usdtAmount2 = 100n * 10n ** 6n; // 100 USDT

    try {
        const addLiqTx3 = await router.addLiquidity(
            contracts.tUSDC,
            contracts.tUSDT,
            usdcAmount2,
            usdtAmount2,
            0,
            0,
            deployer.address,
            Math.floor(Date.now() / 1000) + 3600
        );
        await addLiqTx3.wait();
        console.log("   tUSDC-tUSDT pool created (100 tUSDC + 100 tUSDT)");
    } catch (err) {
        console.log("   Failed:", err.message);
    }

    // WCRO-VVS pool
    console.log("   Creating WCRO-tVVS pool...");
    const wcroAmount3 = hre.ethers.parseEther("5"); // 5 WCRO
    const vvsAmount = hre.ethers.parseEther("500"); // 500 VVS

    try {
        const addLiqTx4 = await router.addLiquidity(
            contracts.wcro,
            contracts.tVVS,
            wcroAmount3,
            vvsAmount,
            0,
            0,
            deployer.address,
            Math.floor(Date.now() / 1000) + 3600
        );
        await addLiqTx4.wait();
        console.log("   WCRO-tVVS pool created (5 WCRO + 500 tVVS)");
    } catch (err) {
        console.log("   Failed:", err.message);
    }

    // ========== 5. Test Swaps ==========
    console.log("\n5. Testing Swaps...");

    try {
        const testAmount = 1n * 10n ** 6n; // 1 USDC
        const path = [contracts.tUSDC, contracts.tUSDT];
        const amountsOut = await router.getAmountsOut(testAmount, path);
        console.log("   Quote: 1 tUSDC ->", hre.ethers.formatUnits(amountsOut[1], 6), "tUSDT");
    } catch (err) {
        console.log("   USDC->USDT quote failed:", err.message);
    }

    try {
        const testAmount = hre.ethers.parseEther("1"); // 1 CRO
        const path = [contracts.wcro, contracts.tUSDC];
        const amountsOut = await router.getAmountsOut(testAmount, path);
        console.log("   Quote: 1 WCRO ->", hre.ethers.formatUnits(amountsOut[1], 6), "tUSDC");
    } catch (err) {
        console.log("   WCRO->USDC quote failed:", err.message);
    }

    // ========== Summary ==========
    console.log("\n" + "=".repeat(70));
    console.log("LIQUIDITY SETUP COMPLETE");
    console.log("=".repeat(70));

    const finalBalance = await deployer.provider.getBalance(deployer.address);
    console.log("\nFinal CRO balance:", hre.ethers.formatEther(finalBalance), "CRO");

    console.log("\nCreated Pools:");
    console.log("  - WCRO/tUSDC");
    console.log("  - WCRO/tUSDT");
    console.log("  - tUSDC/tUSDT");
    console.log("  - WCRO/tVVS");
    console.log("=".repeat(70));
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
