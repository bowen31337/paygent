const hre = require("hardhat");
const fs = require('fs');
const path = require('path');

async function main() {
    console.log("Deploying Paygent smart contracts...\n");

    // Get deployer account
    const [deployer] = await ethers.getSigners();
    console.log("Deploying from account:", deployer.address);
    const balance = await deployer.provider.getBalance(deployer.address);
    console.log("Account balance:", hre.ethers.formatEther(balance), "CRO\n");

    // Deploy AgentWallet
    console.log("1. Deploying AgentWallet...");
    const AgentWallet = await hre.ethers.getContractFactory("AgentWallet");

    // AgentWallet constructor: (address _owner, uint256 _dailyLimit)
    // Daily limit: $1000 in wei (1000 * 10^18)
    const dailyLimit = hre.ethers.parseEther("1000");
    const agentWallet = await AgentWallet.deploy(deployer.address, dailyLimit);
    await agentWallet.waitForDeployment();
    const agentWalletAddress = await agentWallet.getAddress();
    console.log("   AgentWallet deployed to:", agentWalletAddress);
    console.log("   Owner:", deployer.address);
    console.log("   Daily Limit:", hre.ethers.formatEther(dailyLimit), "wei");

    // Deploy PaymentRouter
    console.log("\n2. Deploying PaymentRouter...");
    const PaymentRouter = await hre.ethers.getContractFactory("PaymentRouter");

    // PaymentRouter constructor: (address _feeCollector, uint256 _feePercentage)
    // Fee: 1% = 100 basis points
    const feePercentage = 100; // 1%
    const paymentRouter = await PaymentRouter.deploy(deployer.address, feePercentage);
    await paymentRouter.waitForDeployment();
    const paymentRouterAddress = await paymentRouter.getAddress();
    console.log("   PaymentRouter deployed to:", paymentRouterAddress);
    console.log("   Fee Collector:", deployer.address);
    console.log("   Fee Percentage:", feePercentage / 100, "%");

    // Deploy ServiceRegistry
    console.log("\n3. Deploying ServiceRegistry...");
    const ServiceRegistry = await hre.ethers.getContractFactory("ServiceRegistry");

    // ServiceRegistry constructor: (address _owner, uint256 _reputationRequired, uint256 _defaultStake)
    const reputationRequired = 50; // Min reputation score
    const defaultStake = hre.ethers.parseEther("10"); // 10 CRO default stake
    const serviceRegistry = await ServiceRegistry.deploy(
        deployer.address,
        reputationRequired,
        defaultStake
    );
    await serviceRegistry.waitForDeployment();
    const serviceRegistryAddress = await serviceRegistry.getAddress();
    console.log("   ServiceRegistry deployed to:", serviceRegistryAddress);
    console.log("   Owner:", deployer.address);
    console.log("   Reputation Required:", reputationRequired);
    console.log("   Default Stake:", hre.ethers.formatEther(defaultStake), "CRO");

    // Summary
    console.log("\n" + "=".repeat(60));
    console.log("DEPLOYMENT SUMMARY");
    console.log("=".repeat(60));
    console.log(`AgentWallet:     ${agentWalletAddress}`);
    console.log(`PaymentRouter:   ${paymentRouterAddress}`);
    console.log(`ServiceRegistry: ${serviceRegistryAddress}`);
    console.log("=".repeat(60));

    // Save addresses for reference
    const addresses = {
        network: hre.network.name,
        chainId: hre.network.config.chainId,
        deployer: deployer.address,
        contracts: {
            agentWallet: agentWalletAddress,
            paymentRouter: paymentRouterAddress,
            serviceRegistry: serviceRegistryAddress
        },
        parameters: {
            agentWallet: {
                owner: deployer.address,
                dailyLimit: dailyLimit.toString()
            },
            paymentRouter: {
                feeCollector: deployer.address,
                feePercentage: feePercentage
            },
            serviceRegistry: {
                owner: deployer.address,
                reputationRequired: reputationRequired,
                defaultStake: defaultStake.toString()
            }
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

            // Additional verification: test basic function calls
            console.log("\n5. Testing basic contract functions...");

            // Test AgentWallet
            const walletOwner = await agentWallet.getOwner();
            const walletLimit = await agentWallet.getDailyLimit();
            console.log(`   AgentWallet owner: ${walletOwner}`);
            console.log(`   AgentWallet daily limit: ${hre.ethers.formatEther(walletLimit)} wei`);

            // Test PaymentRouter
            const feeCollector = await paymentRouter.getFeeCollector();
            const feePct = await paymentRouter.getFeePercentage();
            console.log(`   PaymentRouter fee collector: ${feeCollector}`);
            console.log(`   PaymentRouter fee percentage: ${feePct} basis points`);

            // Test ServiceRegistry
            const regOwner = await serviceRegistry.owner();
            const reqRep = await serviceRegistry.reputationRequired();
            const defStake = await serviceRegistry.defaultStake();
            console.log(`   ServiceRegistry owner: ${regOwner}`);
            console.log(`   ServiceRegistry reputation required: ${reqRep}`);
            console.log(`   ServiceRegistry default stake: ${hre.ethers.formatEther(defStake)} wei`);

            console.log("   ✓ All basic functions work correctly");
        } else {
            console.log("   ✗ Contract verification failed");
        }
    } catch (error) {
        console.log("   Verification error:", error.message);
    }

    console.log("\nDeployment complete!");
    console.log("\nNext steps:");
    console.log("1. Run: npx hardhat test");
    console.log("2. Deploy to testnet: npm run deploy:testnet");
    console.log("3. Verify on Cronoscan: npm run verify");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
