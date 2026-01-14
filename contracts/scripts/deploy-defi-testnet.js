const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("Deploying DeFi contracts to Cronos Testnet...\n");

  const [deployer] = await hre.ethers.getSigners();
  console.log("Deployer address:", deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Deployer balance:", hre.ethers.formatEther(balance), "CRO\n");

  // Get collateral token (tUSDC) address from existing deployment
  const existingDeployment = JSON.parse(
    fs.readFileSync(
      path.join(__dirname, "../deployments/adapters-testnet.json"),
      "utf8"
    )
  );
  const collateralToken = existingDeployment.collateralToken;
  console.log("Using collateral token (tUSDC):", collateralToken);

  // Deploy VVSRouter
  console.log("\n1. Deploying VVSRouter...");
  const VVSRouter = await hre.ethers.getContractFactory("VVSRouter");
  const vvsRouter = await VVSRouter.deploy();
  await vvsRouter.waitForDeployment();
  const vvsRouterAddress = await vvsRouter.getAddress();
  console.log("   VVSRouter deployed to:", vvsRouterAddress);

  // Deploy MoonlanderPerp
  console.log("\n2. Deploying MoonlanderPerp...");
  const MoonlanderPerp = await hre.ethers.getContractFactory("MoonlanderPerp");
  const moonlanderPerp = await MoonlanderPerp.deploy(collateralToken);
  await moonlanderPerp.waitForDeployment();
  const moonlanderPerpAddress = await moonlanderPerp.getAddress();
  console.log("   MoonlanderPerp deployed to:", moonlanderPerpAddress);

  // Deploy DelphiPrediction
  console.log("\n3. Deploying DelphiPrediction...");
  const DelphiPrediction = await hre.ethers.getContractFactory("DelphiPrediction");
  const delphiPrediction = await DelphiPrediction.deploy(collateralToken);
  await delphiPrediction.waitForDeployment();
  const delphiPredictionAddress = await delphiPrediction.getAddress();
  console.log("   DelphiPrediction deployed to:", delphiPredictionAddress);

  // Initialize VVSRouter with mock liquidity
  console.log("\n4. Initializing VVSRouter pairs...");

  // WCRO address on testnet (or use a mock)
  const WCRO = "0x52462c26Ad624F8AE6360f7EA8eEca43C92edDA7"; // Testnet WCRO from vvs-testnet.json

  // Initialize CRO-USDC pair with mock reserves
  // Rate: 1 USDC = ~13 CRO (0.075 USD per CRO)
  const croReserve = hre.ethers.parseEther("1000000"); // 1M CRO
  const usdcReserve = hre.ethers.parseUnits("75000", 6); // 75K USDC

  try {
    await vvsRouter.initializePair(WCRO, collateralToken, croReserve, usdcReserve);
    console.log("   CRO-USDC pair initialized");

    // Set exchange rate for CRO/USDC (13.33 CRO per USDC in 18 decimals)
    const exchangeRate = hre.ethers.parseEther("13.33");
    await vvsRouter.setExchangeRate(WCRO, collateralToken, exchangeRate);
    console.log("   Exchange rate set: 1 USDC = 13.33 CRO");
  } catch (e) {
    console.log("   Warning: Could not initialize pair -", e.message);
  }

  // Create initial prediction markets on Delphi
  console.log("\n5. Creating prediction markets...");
  try {
    // Market 1: BTC 100k
    await delphiPrediction.createMarket(
      "Will Bitcoin exceed $100,000 by March 31, 2026?",
      90 * 24 * 60 * 60 // 90 days
    );
    console.log("   Market 0: BTC $100k created");

    // Market 2: ETH 5k
    await delphiPrediction.createMarket(
      "Will Ethereum exceed $5,000 by June 30, 2026?",
      180 * 24 * 60 * 60 // 180 days
    );
    console.log("   Market 1: ETH $5k created");

    // Market 3: CRO $1
    await delphiPrediction.createMarket(
      "Will CRO exceed $1.00 by December 31, 2026?",
      365 * 24 * 60 * 60 // 365 days
    );
    console.log("   Market 2: CRO $1 created");
  } catch (e) {
    console.log("   Warning: Could not create markets -", e.message);
  }

  // Save deployment info
  const deployment = {
    network: "cronosTestnet",
    chainId: 338,
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    collateralToken: collateralToken,
    contracts: {
      vvsRouter: vvsRouterAddress,
      moonlanderPerp: moonlanderPerpAddress,
      delphiPrediction: delphiPredictionAddress,
    },
    vvsRouter: {
      address: vvsRouterAddress,
      pairs: ["CRO-USDC"],
      swapFee: "0.3%",
    },
    moonlanderPerp: {
      address: moonlanderPerpAddress,
      markets: ["BTC-USD", "ETH-USD", "CRO-USD"],
      maxLeverage: "100x",
      collateralToken: collateralToken,
    },
    delphiPrediction: {
      address: delphiPredictionAddress,
      platformFee: "1%",
      collateralToken: collateralToken,
      initialMarkets: 3,
    },
  };

  const deploymentPath = path.join(__dirname, "../deployments/defi-testnet.json");
  fs.writeFileSync(deploymentPath, JSON.stringify(deployment, null, 2));
  console.log("\n6. Deployment saved to:", deploymentPath);

  // Update the main adapters-testnet.json
  existingDeployment.contracts.vvsRouter = vvsRouterAddress;
  existingDeployment.contracts.moonlanderPerp = moonlanderPerpAddress;
  existingDeployment.contracts.delphiPrediction = delphiPredictionAddress;
  existingDeployment.defi = deployment;

  fs.writeFileSync(
    path.join(__dirname, "../deployments/adapters-testnet.json"),
    JSON.stringify(existingDeployment, null, 2)
  );
  console.log("7. Updated adapters-testnet.json\n");

  // Print summary
  console.log("=".repeat(60));
  console.log("DEPLOYMENT SUMMARY");
  console.log("=".repeat(60));
  console.log("\nContracts:");
  console.log(`  VVSRouter:        ${vvsRouterAddress}`);
  console.log(`  MoonlanderPerp:   ${moonlanderPerpAddress}`);
  console.log(`  DelphiPrediction: ${delphiPredictionAddress}`);
  console.log(`\nCollateral Token:   ${collateralToken}`);
  console.log("\nExplorer Links:");
  console.log(`  VVSRouter:        https://explorer.cronos.org/testnet/address/${vvsRouterAddress}`);
  console.log(`  MoonlanderPerp:   https://explorer.cronos.org/testnet/address/${moonlanderPerpAddress}`);
  console.log(`  DelphiPrediction: https://explorer.cronos.org/testnet/address/${delphiPredictionAddress}`);
  console.log("=".repeat(60));
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
