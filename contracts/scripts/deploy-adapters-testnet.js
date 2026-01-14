const hre = require("hardhat");
const fs = require('fs');
const path = require('path');

/**
 * Deploy MockMoonlander and MockDelphi contracts to Cronos Testnet
 *
 * This script deploys:
 * 1. MockMoonlander - Self-contained perpetual trading for testing
 * 2. MockDelphi - Self-contained prediction markets for testing
 *
 * Both use tUSDC as the collateral/betting token from the VVS deployment.
 */
async function main() {
    console.log("=".repeat(70));
    console.log("Moonlander & Delphi Mock Contracts Deployment to Cronos Testnet");
    console.log("=".repeat(70));
    console.log("");

    // Get deployer account
    const signers = await hre.ethers.getSigners();
    if (signers.length === 0) {
        console.log("ERROR: No accounts configured. Set PRIVATE_KEY environment variable.");
        console.log("Example: export PRIVATE_KEY=0x...");
        process.exit(1);
    }
    const [deployer] = signers;
    console.log("Deployer address:", deployer.address);
    const balance = await deployer.provider.getBalance(deployer.address);
    console.log("Balance:", hre.ethers.formatEther(balance), "CRO");
    console.log("");

    // Verify we have enough balance
    if (balance < hre.ethers.parseEther("5")) {
        console.log("WARNING: Low balance. Get testnet CRO from faucet:");
        console.log("https://cronos.org/faucet");
        console.log("");
    }

    // Load VVS deployment to get tUSDC address
    const vvsDeploymentPath = path.join(__dirname, "..", "deployments", "vvs-testnet.json");
    if (!fs.existsSync(vvsDeploymentPath)) {
        console.log("ERROR: VVS deployment not found. Run deploy-vvs-testnet.js first.");
        console.log("Expected path:", vvsDeploymentPath);
        process.exit(1);
    }

    const vvsDeployment = JSON.parse(fs.readFileSync(vvsDeploymentPath, 'utf8'));
    const tUSDCAddress = vvsDeployment.contracts.tUSDC;
    console.log("Using tUSDC from VVS deployment:", tUSDCAddress);
    console.log("");

    const deployedContracts = {};

    // ========== 1. Deploy MockMoonlander ==========
    console.log("1. Deploying MockMoonlander (Perpetual Trading)...");
    const MockMoonlander = await hre.ethers.getContractFactory("MockMoonlander");
    const moonlander = await MockMoonlander.deploy(tUSDCAddress);
    await moonlander.waitForDeployment();
    deployedContracts.MockMoonlander = await moonlander.getAddress();
    console.log("   MockMoonlander deployed to:", deployedContracts.MockMoonlander);

    // Log market info
    console.log("\n   Initial Markets:");
    const btcPrice = await moonlander.getPrice("BTC-USDC");
    const ethPrice = await moonlander.getPrice("ETH-USDC");
    const croPrice = await moonlander.getPrice("CRO-USDC");
    console.log("   - BTC-USDC: Max 20x leverage, Mock price: $" + (Number(btcPrice) / 1e8).toLocaleString());
    console.log("   - ETH-USDC: Max 20x leverage, Mock price: $" + (Number(ethPrice) / 1e8).toLocaleString());
    console.log("   - CRO-USDC: Max 10x leverage, Mock price: $" + (Number(croPrice) / 1e8).toFixed(4));

    // ========== 2. Deploy MockDelphi ==========
    console.log("\n2. Deploying MockDelphi (Prediction Markets)...");
    const MockDelphi = await hre.ethers.getContractFactory("MockDelphi");
    const delphi = await MockDelphi.deploy(tUSDCAddress);
    await delphi.waitForDeployment();
    deployedContracts.MockDelphi = await delphi.getAddress();
    console.log("   MockDelphi deployed to:", deployedContracts.MockDelphi);

    // Log initial markets
    console.log("\n   Initial Markets:");
    const allMarkets = await delphi.getAllMarkets();
    console.log("   - " + allMarkets.length + " prediction markets created");
    for (let i = 0; i < Math.min(allMarkets.length, 3); i++) {
        const marketId = allMarkets[i];
        const market = await delphi.getMarket(marketId);
        console.log(`   - Market ${i + 1}: "${market[0].substring(0, 50)}..."`);
        console.log(`     Category: ${market[1]}, Outcomes: ${market[2].length}`);
    }

    // ========== 3. Verify Contracts ==========
    console.log("\n3. Verifying Contract State...");

    // Check Moonlander owner and config
    const moonlanderOwner = await moonlander.owner();
    console.log("   Moonlander owner:", moonlanderOwner);
    console.log("   Moonlander collateral token:", await moonlander.collateralToken());

    // Check Delphi owner and config
    const delphiOwner = await delphi.owner();
    const delphiFee = await delphi.defaultFee();
    console.log("   Delphi owner:", delphiOwner);
    console.log("   Delphi fee:", Number(delphiFee) / 100, "%");

    // ========== Summary ==========
    console.log("\n" + "=".repeat(70));
    console.log("DEPLOYMENT SUMMARY - Mock Adapters on Cronos Testnet");
    console.log("=".repeat(70));
    console.log("");
    console.log("Mock Contracts:");
    console.log(`  MockMoonlander:  ${deployedContracts.MockMoonlander}`);
    console.log(`  MockDelphi:      ${deployedContracts.MockDelphi}`);
    console.log("");
    console.log("Collateral Token:");
    console.log(`  tUSDC:           ${tUSDCAddress}`);
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
        collateralToken: tUSDCAddress,
        contracts: {
            moonlanderAdapter: deployedContracts.MockMoonlander,
            delphiAdapter: deployedContracts.MockDelphi,
        },
        moonlander: {
            address: deployedContracts.MockMoonlander,
            markets: ["BTC-USDC", "ETH-USDC", "CRO-USDC"],
            maxLeverage: {
                "BTC-USDC": 20,
                "ETH-USDC": 20,
                "CRO-USDC": 10
            }
        },
        delphi: {
            address: deployedContracts.MockDelphi,
            defaultFee: Number(delphiFee),
            initialMarkets: allMarkets.length
        }
    };

    const deploymentsDir = path.join(__dirname, "..", "deployments");
    if (!fs.existsSync(deploymentsDir)) {
        fs.mkdirSync(deploymentsDir, { recursive: true });
    }

    const deploymentPath = path.join(deploymentsDir, "adapters-testnet.json");
    fs.writeFileSync(deploymentPath, JSON.stringify(deployment, null, 2));
    console.log(`\nDeployment saved to: ${deploymentPath}`);

    // ========== Usage Instructions ==========
    console.log("\n" + "=".repeat(70));
    console.log("USAGE INSTRUCTIONS");
    console.log("=".repeat(70));
    console.log("");
    console.log("MockMoonlander (Perpetual Trading):");
    console.log("  1. Approve tUSDC for MockMoonlander contract");
    console.log("  2. Call openPosition(market, isLong, collateral, leverage)");
    console.log("     Example: openPosition('BTC-USDC', true, 100e6, 10)");
    console.log("  3. Set stop-loss/take-profit with setStopLoss() and setTakeProfit()");
    console.log("  4. Close with closePosition(positionId)");
    console.log("");
    console.log("MockDelphi (Prediction Markets):");
    console.log("  1. Approve tUSDC for MockDelphi contract");
    console.log("  2. Get market IDs with getAllMarkets()");
    console.log("  3. Place bet with placeBet(marketId, outcomeIndex, amount)");
    console.log("  4. After market resolves, claim with claimWinnings(betId)");
    console.log("");
    console.log("Test Tokens:");
    console.log("  - Get tUSDC from faucet at:", tUSDCAddress);
    console.log("  - Call faucet() to get 1000 tUSDC");
    console.log("=".repeat(70));
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
