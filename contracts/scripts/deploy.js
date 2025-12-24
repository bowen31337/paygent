const hre = require("hardhat");

async function main() {
    console.log("Deploying Paygent smart contracts...\n");

    // Get deployer account
    const [deployer] = await ethers.getSigners();
    console.log("Deploying from account:", deployer.address);
    console.log("Account balance:", (await deployer.provider.getBalance(deployer.address)).toString(), "CRO\n");

    // Deploy AgentWallet
    console.log("1. Deploying AgentWallet...");
    const AgentWallet = await hre.ethers.getContractFactory("AgentWallet");
    const dailyLimitUSD = hre.ethers.parseEther("1000"); // $1000 daily limit
    const agentWallet = await AgentWallet.deploy(dailyLimitUSD);
    await agentWallet.waitForDeployment();
    const agentWalletAddress = await agentWallet.getAddress();
    console.log("   AgentWallet deployed to:", agentWalletAddress);

    // Deploy PaymentRouter
    console.log("\n2. Deploying PaymentRouter...");
    const PaymentRouter = await hre.ethers.getContractFactory("PaymentRouter");
    const paymentRouter = await PaymentRouter.deploy();
    await paymentRouter.waitForDeployment();
    const paymentRouterAddress = await paymentRouter.getAddress();
    console.log("   PaymentRouter deployed to:", paymentRouterAddress);

    // Deploy ServiceRegistry
    console.log("\n3. Deploying ServiceRegistry...");
    const ServiceRegistry = await hre.ethers.getContractFactory("ServiceRegistry");
    const serviceRegistry = await ServiceRegistry.deploy();
    await serviceRegistry.waitForDeployment();
    const serviceRegistryAddress = await serviceRegistry.getAddress();
    console.log("   ServiceRegistry deployed to:", serviceRegistryAddress);

    // Summary
    console.log("\n" + "=".repeat(60));
    console.log("DEPLOYMENT SUMMARY");
    console.log("=".repeat(60));
    console.log(`AgentWallet:     ${agentWalletAddress}`);
    console.log(`PaymentRouter:   ${paymentRouterAddress}`);
    console.log(`ServiceRegistry: ${serviceRegistryAddress}`);
    console.log("=".repeat(60));

    // Save addresses for reference
    const fs = require('fs');
    const path = require('path');
    const addresses = {
        network: hre.network.name,
        chainId: hre.network.config.chainId,
        deployer: deployer.address,
        contracts: {
            agentWallet: agentWalletAddress,
            paymentRouter: paymentRouterAddress,
            serviceRegistry: serviceRegistryAddress
        },
        timestamp: new Date().toISOString()
    };

    const addressesPath = path.join(__dirname, "..", "deployments", `${hre.network.name}.json`);
    const deploymentsDir = path.dirname(addressesPath);

    if (!fs.existsSync(deploymentsDir)) {
        fs.mkdirSync(deploymentsDir, { recursive: true });
    }

    fs.writeFileSync(addressesPath, JSON.stringify(addresses, null, 2));
    console.log(`\nDeployment addresses saved to: ${addressesPath}`);

    // Verify contracts are valid
    console.log("\n4. Verifying contracts...");
    try {
        const agentWalletCode = await deployer.provider.getCode(agentWalletAddress);
        const paymentRouterCode = await deployer.provider.getCode(paymentRouterAddress);
        const serviceRegistryCode = await deployer.provider.getCode(serviceRegistryAddress);

        if (agentWalletCode !== "0x" && paymentRouterCode !== "0x" && serviceRegistryCode !== "0x") {
            console.log("   ✓ All contracts verified successfully");
        } else {
            console.log("   ✗ Contract verification failed");
        }
    } catch (error) {
        console.log("   Verification error:", error.message);
    }

    console.log("\nDeployment complete!");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
