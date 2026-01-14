const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
    console.log("Redeploying DelphiPrediction contract...\n");

    const [deployer] = await hre.ethers.getSigners();
    console.log("Deployer address:", deployer.address);

    const balance = await hre.ethers.provider.getBalance(deployer.address);
    console.log("Deployer balance:", hre.ethers.formatEther(balance), "CRO\n");

    // Get collateral token from existing deployment
    const deploymentsPath = path.join(__dirname, "../deployments");
    const defiPath = path.join(deploymentsPath, "defi-testnet.json");
    const existingDeployment = JSON.parse(fs.readFileSync(defiPath, "utf8"));
    const collateralToken = existingDeployment.collateralToken;

    console.log("Using collateral token (tUSDC):", collateralToken);

    // Deploy DelphiPrediction
    console.log("\nDeploying DelphiPrediction...");
    const DelphiPrediction = await hre.ethers.getContractFactory("DelphiPrediction");
    const delphiPrediction = await DelphiPrediction.deploy(collateralToken);
    await delphiPrediction.waitForDeployment();
    const delphiPredictionAddress = await delphiPrediction.getAddress();
    console.log("   DelphiPrediction deployed to:", delphiPredictionAddress);

    // Create prediction markets
    console.log("\nCreating prediction markets...");
    await delphiPrediction.createMarket(
        "Will Bitcoin exceed $100,000 by March 31, 2026?",
        90 * 24 * 60 * 60 // 90 days
    );
    console.log("   Market 0: BTC $100k created");

    await delphiPrediction.createMarket(
        "Will Ethereum exceed $5,000 by June 30, 2026?",
        180 * 24 * 60 * 60 // 180 days
    );
    console.log("   Market 1: ETH $5k created");

    await delphiPrediction.createMarket(
        "Will CRO exceed $1.00 by December 31, 2026?",
        365 * 24 * 60 * 60 // 365 days
    );
    console.log("   Market 2: CRO $1 created");

    // Update deployment file
    existingDeployment.contracts.delphiPrediction = delphiPredictionAddress;
    existingDeployment.delphiPrediction.address = delphiPredictionAddress;
    existingDeployment.timestamp = new Date().toISOString();

    fs.writeFileSync(defiPath, JSON.stringify(existingDeployment, null, 2));
    console.log("\nUpdated defi-testnet.json");

    // Also update adapters-testnet.json
    const adaptersPath = path.join(deploymentsPath, "adapters-testnet.json");
    if (fs.existsSync(adaptersPath)) {
        const adaptersDeployment = JSON.parse(fs.readFileSync(adaptersPath, "utf8"));
        adaptersDeployment.contracts.delphiPrediction = delphiPredictionAddress;
        fs.writeFileSync(adaptersPath, JSON.stringify(adaptersDeployment, null, 2));
        console.log("Updated adapters-testnet.json");
    }

    console.log("\n============================================================");
    console.log("REDEPLOYMENT COMPLETE");
    console.log("============================================================\n");
    console.log("DelphiPrediction:", delphiPredictionAddress);
    console.log("Explorer:", `https://explorer.cronos.org/testnet/address/${delphiPredictionAddress}`);
    console.log("============================================================");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
