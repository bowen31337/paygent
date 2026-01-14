const hre = require("hardhat");

async function main() {
    console.log("Checking DelphiPrediction markets...\n");

    const [deployer] = await hre.ethers.getSigners();
    console.log("Using account:", deployer.address);

    // DelphiPrediction address from deployment
    const DELPHI_ADDRESS = "0x1EfE0Cfe86D7b1aa659C1348dce1AC949609Cab1";

    const DelphiPrediction = await hre.ethers.getContractFactory("DelphiPrediction");
    const delphi = DelphiPrediction.attach(DELPHI_ADDRESS);

    // Check market count
    const marketCount = await delphi.marketCount();
    console.log("Market count:", marketCount.toString());

    if (marketCount === 0n) {
        console.log("\nNo markets found. Creating markets...\n");

        // Create markets
        console.log("Creating Market 0: BTC $100k...");
        await delphi.createMarket(
            "Will Bitcoin exceed $100,000 by March 31, 2026?",
            90 * 24 * 60 * 60 // 90 days
        );
        console.log("✓ Market 0 created");

        console.log("Creating Market 1: ETH $5k...");
        await delphi.createMarket(
            "Will Ethereum exceed $5,000 by June 30, 2026?",
            180 * 24 * 60 * 60 // 180 days
        );
        console.log("✓ Market 1 created");

        console.log("Creating Market 2: CRO $1...");
        await delphi.createMarket(
            "Will CRO exceed $1.00 by December 31, 2026?",
            365 * 24 * 60 * 60 // 365 days
        );
        console.log("✓ Market 2 created");

        console.log("\n✅ All markets created successfully!");
    } else {
        console.log("\nMarkets already exist. Checking details...\n");

        for (let i = 0; i < Number(marketCount); i++) {
            const market = await delphi.getMarket(i);
            console.log(`Market ${i}:`);
            console.log(`  Question: ${market[0]}`);
            console.log(`  End Time: ${new Date(Number(market[1]) * 1000).toISOString()}`);
            console.log(`  Resolved: ${market[7]}`);
            console.log("");
        }
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
