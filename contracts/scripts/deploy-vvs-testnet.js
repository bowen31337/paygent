const hre = require("hardhat");
const fs = require('fs');
const path = require('path');

/**
 * Deploy VVS-compatible DEX contracts to Cronos Testnet
 *
 * This script deploys:
 * 1. WCRO - Wrapped CRO token
 * 2. Test tokens (tUSDC, tUSDT, tVVS)
 * 3. UniswapV2Factory
 * 4. UniswapV2Router
 * 5. Creates initial liquidity pools
 */
async function main() {
    console.log("=".repeat(70));
    console.log("VVS-Compatible DEX Deployment to Cronos Testnet");
    console.log("=".repeat(70));
    console.log("");

    // Get deployer account
    const [deployer] = await ethers.getSigners();
    console.log("Deployer address:", deployer.address);
    const balance = await deployer.provider.getBalance(deployer.address);
    console.log("Balance:", hre.ethers.formatEther(balance), "CRO");
    console.log("");

    // Verify we have enough balance
    if (balance < hre.ethers.parseEther("10")) {
        console.log("WARNING: Low balance. Get testnet CRO from faucet:");
        console.log("https://cronos.org/faucet");
        console.log("");
    }

    const deployedContracts = {};

    // ========== 1. Deploy WCRO ==========
    console.log("1. Deploying WCRO (Wrapped CRO)...");
    const WCRO = await hre.ethers.getContractFactory("WCRO");
    const wcro = await WCRO.deploy();
    await wcro.waitForDeployment();
    deployedContracts.WCRO = await wcro.getAddress();
    console.log("   WCRO deployed to:", deployedContracts.WCRO);

    // ========== 2. Deploy Test Tokens ==========
    console.log("\n2. Deploying Test Tokens...");

    // Deploy TestUSDC
    const TestUSDC = await hre.ethers.getContractFactory("TestUSDC");
    const testUSDC = await TestUSDC.deploy();
    await testUSDC.waitForDeployment();
    deployedContracts.tUSDC = await testUSDC.getAddress();
    console.log("   tUSDC deployed to:", deployedContracts.tUSDC);

    // Deploy TestUSDT
    const TestUSDT = await hre.ethers.getContractFactory("TestUSDT");
    const testUSDT = await TestUSDT.deploy();
    await testUSDT.waitForDeployment();
    deployedContracts.tUSDT = await testUSDT.getAddress();
    console.log("   tUSDT deployed to:", deployedContracts.tUSDT);

    // Deploy TestVVS
    const TestVVS = await hre.ethers.getContractFactory("TestVVS");
    const testVVS = await TestVVS.deploy();
    await testVVS.waitForDeployment();
    deployedContracts.tVVS = await testVVS.getAddress();
    console.log("   tVVS deployed to:", deployedContracts.tVVS);

    // ========== 3. Deploy UniswapV2Factory ==========
    console.log("\n3. Deploying UniswapV2Factory...");
    const UniswapV2Factory = await hre.ethers.getContractFactory("UniswapV2Factory");
    const factory = await UniswapV2Factory.deploy(deployer.address);
    await factory.waitForDeployment();
    deployedContracts.Factory = await factory.getAddress();
    console.log("   Factory deployed to:", deployedContracts.Factory);

    // Get pair init code hash (needed for router)
    const pairCodeHash = await factory.pairCodeHash();
    console.log("   Pair code hash:", pairCodeHash);

    // ========== 4. Deploy UniswapV2Router ==========
    console.log("\n4. Deploying UniswapV2Router...");
    const UniswapV2Router = await hre.ethers.getContractFactory("UniswapV2Router");
    const router = await UniswapV2Router.deploy(deployedContracts.Factory, deployedContracts.WCRO);
    await router.waitForDeployment();
    deployedContracts.Router = await router.getAddress();
    console.log("   Router deployed to:", deployedContracts.Router);

    // ========== 5. Create Initial Liquidity Pools ==========
    console.log("\n5. Creating Initial Liquidity Pools...");

    // Wrap some CRO first (using small amount to preserve CRO for gas)
    const wrapAmount = hre.ethers.parseEther("10"); // 10 CRO
    console.log("   Wrapping 10 CRO...");
    const wrapTx = await wcro.deposit({ value: wrapAmount });
    await wrapTx.wait();
    console.log("   Wrapped 10 CRO to WCRO");

    // Approve tokens for router
    console.log("   Approving tokens for router...");
    const maxApproval = hre.ethers.MaxUint256;

    await (await wcro.approve(deployedContracts.Router, maxApproval)).wait();
    await (await testUSDC.approve(deployedContracts.Router, maxApproval)).wait();
    await (await testUSDT.approve(deployedContracts.Router, maxApproval)).wait();
    await (await testVVS.approve(deployedContracts.Router, maxApproval)).wait();
    console.log("   All tokens approved");

    // Create WCRO-USDC pool
    console.log("\n   Creating WCRO-tUSDC pool...");
    const wcroAmount1 = hre.ethers.parseEther("5"); // 5 WCRO
    const usdcAmount = 50n * 10n ** 6n; // 50 USDC (6 decimals) -> 1 CRO = $10

    try {
        const addLiqTx1 = await router.addLiquidity(
            deployedContracts.WCRO,
            deployedContracts.tUSDC,
            wcroAmount1,
            usdcAmount,
            0, // amountAMin
            0, // amountBMin
            deployer.address,
            Math.floor(Date.now() / 1000) + 3600 // 1 hour deadline
        );
        await addLiqTx1.wait();
        console.log("   WCRO-tUSDC pool created (5 WCRO + 50 tUSDC)");
    } catch (err) {
        console.log("   Failed to create WCRO-tUSDC pool:", err.message);
    }

    // Create WCRO-USDT pool
    console.log("   Creating WCRO-tUSDT pool...");
    const wcroAmount2 = hre.ethers.parseEther("5"); // 5 WCRO
    const usdtAmount = 50n * 10n ** 6n; // 50 USDT (6 decimals)

    try {
        const addLiqTx2 = await router.addLiquidity(
            deployedContracts.WCRO,
            deployedContracts.tUSDT,
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
        console.log("   Failed to create WCRO-tUSDT pool:", err.message);
    }

    // Create USDC-USDT pool
    console.log("   Creating tUSDC-tUSDT pool...");
    const usdcAmount2 = 100n * 10n ** 6n; // 100 USDC
    const usdtAmount2 = 100n * 10n ** 6n; // 100 USDT (1:1 ratio)

    try {
        const addLiqTx3 = await router.addLiquidity(
            deployedContracts.tUSDC,
            deployedContracts.tUSDT,
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
        console.log("   Failed to create tUSDC-tUSDT pool:", err.message);
    }

    // ========== 6. Test Swap ==========
    console.log("\n6. Testing Swap...");
    try {
        const testSwapAmount = 1n * 10n ** 6n; // 1 USDC
        const path = [deployedContracts.tUSDC, deployedContracts.tUSDT];
        const amountsOut = await router.getAmountsOut(testSwapAmount, path);
        console.log("   Test quote: 1 tUSDC ->", hre.ethers.formatUnits(amountsOut[1], 6), "tUSDT");
    } catch (err) {
        console.log("   Quote test failed:", err.message);
    }

    // ========== Summary ==========
    console.log("\n" + "=".repeat(70));
    console.log("DEPLOYMENT SUMMARY - VVS-Compatible DEX on Cronos Testnet");
    console.log("=".repeat(70));
    console.log("");
    console.log("Core Contracts:");
    console.log(`  Factory:  ${deployedContracts.Factory}`);
    console.log(`  Router:   ${deployedContracts.Router}`);
    console.log(`  WCRO:     ${deployedContracts.WCRO}`);
    console.log("");
    console.log("Test Tokens:");
    console.log(`  tUSDC:    ${deployedContracts.tUSDC}`);
    console.log(`  tUSDT:    ${deployedContracts.tUSDT}`);
    console.log(`  tVVS:     ${deployedContracts.tVVS}`);
    console.log("");
    console.log("Network: Cronos Testnet (Chain ID: 338)");
    console.log("RPC: https://evm-t3.cronos.org");
    console.log("Explorer: https://explorer.cronos.org/testnet");
    console.log("=".repeat(70));

    // ========== Save Deployment ==========
    const deployment = {
        network: "cronosTestnet",
        chainId: 338,
        deployer: deployer.address,
        timestamp: new Date().toISOString(),
        contracts: {
            factory: deployedContracts.Factory,
            router: deployedContracts.Router,
            wcro: deployedContracts.WCRO,
            tUSDC: deployedContracts.tUSDC,
            tUSDT: deployedContracts.tUSDT,
            tVVS: deployedContracts.tVVS,
        },
        pairCodeHash: pairCodeHash,
        // VVS connector compatible config
        vvsCompatible: {
            routerAddress: deployedContracts.Router,
            factoryAddress: deployedContracts.Factory,
            wethAddress: deployedContracts.WCRO,
            tokenAddresses: {
                WCRO: deployedContracts.WCRO,
                CRO: deployedContracts.WCRO,
                USDC: deployedContracts.tUSDC,
                USDT: deployedContracts.tUSDT,
                VVS: deployedContracts.tVVS,
            }
        }
    };

    const deploymentsDir = path.join(__dirname, "..", "deployments");
    if (!fs.existsSync(deploymentsDir)) {
        fs.mkdirSync(deploymentsDir, { recursive: true });
    }

    const deploymentPath = path.join(deploymentsDir, "vvs-testnet.json");
    fs.writeFileSync(deploymentPath, JSON.stringify(deployment, null, 2));
    console.log(`\nDeployment saved to: ${deploymentPath}`);

    // ========== Update Python Connector Config ==========
    console.log("\n" + "=".repeat(70));
    console.log("NEXT STEPS");
    console.log("=".repeat(70));
    console.log("");
    console.log("1. Update src/connectors/vvs.py with these testnet addresses:");
    console.log("");
    console.log("   TESTNET_ROUTER_ADDRESS = \"" + deployedContracts.Router + "\"");
    console.log("");
    console.log("   TESTNET_TOKEN_ADDRESSES = {");
    console.log("       \"WCRO\": \"" + deployedContracts.WCRO + "\",");
    console.log("       \"USDC\": \"" + deployedContracts.tUSDC + "\",");
    console.log("       \"USDT\": \"" + deployedContracts.tUSDT + "\",");
    console.log("       \"CRO\": \"" + deployedContracts.WCRO + "\",");
    console.log("       \"VVS\": \"" + deployedContracts.tVVS + "\",");
    console.log("   }");
    console.log("");
    console.log("2. Get test tokens using faucet functions:");
    console.log("   - Call tUSDC.faucet() to get 1000 tUSDC");
    console.log("   - Call tUSDT.faucet() to get 1000 tUSDT");
    console.log("   - Call tVVS.faucet() to get 10000 tVVS");
    console.log("");
    console.log("3. Verify contracts on CronoScan (optional):");
    console.log("   npx hardhat verify --network cronosTestnet " + deployedContracts.Router);
    console.log("=".repeat(70));
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
