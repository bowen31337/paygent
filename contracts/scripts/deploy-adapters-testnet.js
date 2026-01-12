const hre = require("hardhat");
const fs = require('fs');
const path = require('path');

/**
 * Deploy adapter contracts to Cronos Testnet
 *
 * This script deploys:
 * 1. ServiceRegistry - On-chain service discovery
 * 2. MoonlanderAdapter - Perpetual trading adapter
 * 3. DelphiAdapter - Prediction market adapter
 */
async function main() {
    console.log("=".repeat(70));
    console.log("Paygent Adapter Contracts Deployment to Cronos Testnet");
    console.log("=".repeat(70));
    console.log("");

    // Get deployer account
    const [deployer] = await ethers.getSigners();
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

    const deployedContracts = {};

    // ========== 1. Deploy ServiceRegistry ==========
    console.log("1. Deploying ServiceRegistry...");
    const ServiceRegistry = await hre.ethers.getContractFactory("ServiceRegistry");

    // Constructor: (address _owner, uint256 _reputationRequired, uint256 _defaultStake)
    const reputationRequired = 50; // Min reputation score
    const defaultStake = hre.ethers.parseEther("0.1"); // 0.1 CRO for testnet

    const serviceRegistry = await ServiceRegistry.deploy(
        deployer.address,
        reputationRequired,
        defaultStake
    );
    await serviceRegistry.waitForDeployment();
    deployedContracts.serviceRegistry = await serviceRegistry.getAddress();
    console.log("   ServiceRegistry deployed to:", deployedContracts.serviceRegistry);

    // ========== 2. Deploy MoonlanderAdapter ==========
    console.log("\n2. Deploying MoonlanderAdapter...");
    const MoonlanderAdapter = await hre.ethers.getContractFactory("MoonlanderAdapter");

    // For testing, we'll use placeholder addresses since there's no real Moonlander router
    // Constructor: (address _tradingRouter, address _feeManager, uint256 _defaultLeverage)
    const mockTradingRouter = deployer.address; // Use deployer as mock router
    const mockFeeManager = deployer.address;    // Use deployer as mock fee manager
    const defaultLeverage = 5;                  // 5x default leverage

    const moonlanderAdapter = await MoonlanderAdapter.deploy(
        mockTradingRouter,
        mockFeeManager,
        defaultLeverage
    );
    await moonlanderAdapter.waitForDeployment();
    deployedContracts.moonlanderAdapter = await moonlanderAdapter.getAddress();
    console.log("   MoonlanderAdapter deployed to:", deployedContracts.moonlanderAdapter);

    // ========== 3. Deploy DelphiAdapter ==========
    console.log("\n3. Deploying DelphiAdapter...");
    const DelphiAdapter = await hre.ethers.getContractFactory("DelphiAdapter");

    // For testing, we'll use placeholder addresses since there's no real Delphi market
    // Constructor: (address _marketsRegistry, address _feeCollector, uint256 _defaultFee)
    const mockMarketsRegistry = deployer.address; // Use deployer as mock registry
    const mockFeeCollector = deployer.address;    // Use deployer as mock fee collector
    const defaultFee = 100;                       // 1% fee (100 basis points)

    const delphiAdapter = await DelphiAdapter.deploy(
        mockMarketsRegistry,
        mockFeeCollector,
        defaultFee
    );
    await delphiAdapter.waitForDeployment();
    deployedContracts.delphiAdapter = await delphiAdapter.getAddress();
    console.log("   DelphiAdapter deployed to:", deployedContracts.delphiAdapter);

    // ========== 4. Verify Deployments ==========
    console.log("\n4. Verifying deployments...");

    const serviceRegistryCode = await deployer.provider.getCode(deployedContracts.serviceRegistry);
    const moonlanderCode = await deployer.provider.getCode(deployedContracts.moonlanderAdapter);
    const delphiCode = await deployer.provider.getCode(deployedContracts.delphiAdapter);

    if (serviceRegistryCode !== "0x" && moonlanderCode !== "0x" && delphiCode !== "0x") {
        console.log("   ✓ All contracts verified successfully");
    } else {
        console.log("   ✗ Contract verification failed");
    }

    // ========== 5. Test Basic Functions ==========
    console.log("\n5. Testing basic contract functions...");

    // Test ServiceRegistry
    const regOwner = await serviceRegistry.owner();
    console.log("   ServiceRegistry owner:", regOwner);

    // Test MoonlanderAdapter
    const mlOwner = await moonlanderAdapter.owner();
    const mlLeverage = await moonlanderAdapter.defaultLeverage();
    console.log("   MoonlanderAdapter owner:", mlOwner);
    console.log("   MoonlanderAdapter default leverage:", mlLeverage.toString() + "x");

    // Test DelphiAdapter
    const daOwner = await delphiAdapter.owner();
    const daFee = await delphiAdapter.defaultFee();
    console.log("   DelphiAdapter owner:", daOwner);
    console.log("   DelphiAdapter default fee:", daFee.toString(), "basis points");

    // ========== Summary ==========
    console.log("\n" + "=".repeat(70));
    console.log("DEPLOYMENT SUMMARY - Adapter Contracts on Cronos Testnet");
    console.log("=".repeat(70));
    console.log("");
    console.log("Contracts:");
    console.log(`  ServiceRegistry:    ${deployedContracts.serviceRegistry}`);
    console.log(`  MoonlanderAdapter:  ${deployedContracts.moonlanderAdapter}`);
    console.log(`  DelphiAdapter:      ${deployedContracts.delphiAdapter}`);
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
            serviceRegistry: deployedContracts.serviceRegistry,
            moonlanderAdapter: deployedContracts.moonlanderAdapter,
            delphiAdapter: deployedContracts.delphiAdapter,
        },
        parameters: {
            serviceRegistry: {
                owner: deployer.address,
                reputationRequired: reputationRequired,
                defaultStake: defaultStake.toString(),
            },
            moonlanderAdapter: {
                tradingRouter: mockTradingRouter,
                feeManager: mockFeeManager,
                defaultLeverage: defaultLeverage,
            },
            delphiAdapter: {
                marketsRegistry: mockMarketsRegistry,
                feeCollector: mockFeeCollector,
                defaultFee: defaultFee,
            }
        }
    };

    const deploymentsDir = path.join(__dirname, "..", "deployments");
    if (!fs.existsSync(deploymentsDir)) {
        fs.mkdirSync(deploymentsDir, { recursive: true });
    }

    const deploymentPath = path.join(deploymentsDir, "adapters-testnet.json");
    fs.writeFileSync(deploymentPath, JSON.stringify(deployment, null, 2));
    console.log(`\nDeployment saved to: ${deploymentPath}`);

    console.log("\n" + "=".repeat(70));
    console.log("NEXT STEPS");
    console.log("=".repeat(70));
    console.log("");
    console.log("1. Run integration tests:");
    console.log("   pytest tests/integration/test_adapters_real.py -v");
    console.log("");
    console.log("2. Verify contracts on CronoScan (optional):");
    console.log(`   npx hardhat verify --network cronosTestnet ${deployedContracts.serviceRegistry} "${deployer.address}" "${reputationRequired}" "${defaultStake}"`);
    console.log("=".repeat(70));
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
