const hre = require("hardhat");
const fs = require('fs');
const path = require('path');

/**
 * Contract verification script for Paygent smart contracts
 * This script verifies deployed contracts on Cronoscan testnet/mainnet
 */
async function verifyContracts() {
    console.log("🧪 Verifying Paygent smart contracts on Cronoscan...\n");

    try {
        // Check if we have the required environment variables
        const network = hre.network.name;
        const chainId = hre.network.config.chainId;

        console.log(`Network: ${network} (Chain ID: ${chainId})`);

        // Check for Cronoscan API key
        if (!process.env.CRONOSCAN_API_KEY) {
            console.log("⚠️  Warning: No CRONOSCAN_API_KEY environment variable set");
            console.log("   Please set your Cronoscan API key to verify contracts");
            console.log("   Visit: https://cronoscan.com/myapikey");
            return false;
        }

        // Check for private key if needed
        if (!process.env.PRIVATE_KEY && network !== "localhost") {
            console.log("⚠️  Warning: No PRIVATE_KEY environment variable set");
            console.log("   Contract addresses will need to be provided manually");
        }

        // Check for deployment files
        const deploymentsDir = path.join(__dirname, "..", "deployments");
        const deploymentFile = path.join(deploymentsDir, `${network}.json`);

        let deployedContracts = {};

        if (fs.existsSync(deploymentFile)) {
            console.log(`✓ Found deployment file: ${deploymentFile}`);
            deployedContracts = JSON.parse(fs.readFileSync(deploymentFile, 'utf8'));
        } else {
            console.log("⚠️  No deployment file found. You'll need to provide contract addresses manually.");
        }

        const contractsToVerify = [
            {
                name: "AgentWallet",
                contractPath: "contracts/AgentWallet.sol:AgentWallet",
                constructorArgs: ["0x0000000000000000000000000000000000000000"] // owner address (will be replaced)
            },
            {
                name: "PaymentRouter",
                contractPath: "contracts/PaymentRouter.sol:PaymentRouter",
                constructorArgs: ["0x0000000000000000000000000000000000000000"] // feeCollector address (will be replaced)
            },
            {
                name: "ServiceRegistry",
                contractPath: "contracts/ServiceRegistry.sol:ServiceRegistry",
                constructorArgs: []
            },
            {
                name: "MockToken",
                contractPath: "contracts/MockToken.sol:MockToken",
                constructorArgs: ["Paygent Token", "PAYG", 18, "1000000000000000000000000"] // name, symbol, decimals, initialSupply
            }
        ];

        const verifiedContracts = [];
        const failedVerifications = [];

        for (const contract of contractsToVerify) {
            try {
                console.log(`\n🔍 Verifying ${contract.name}...`);

                let contractAddress = "";

                // Try to get address from deployment file
                if (deployedContracts.contracts && deployedContracts.contracts[contract.name.toLowerCase()]) {
                    contractAddress = deployedContracts.contracts[contract.name.toLowerCase()];
                    console.log(`   Found address in deployment file: ${contractAddress}`);
                } else {
                    console.log(`   No deployment found for ${contract.name}`);
                    console.log(`   Please provide the contract address manually:`);
                    console.log(`   npx hardhat verify --network ${network} <address> --contract "${contract.contractPath}"`);
                    continue;
                }

                // Skip verification if no address found
                if (!contractAddress || contractAddress === "0x0000000000000000000000000000000000000000") {
                    console.log(`   Skipping ${contract.name} - no valid address`);
                    continue;
                }

                // Verify the contract
                console.log(`   Running verification for ${contract.name} at ${contractAddress}...`);

                await hre.run("verify:verify", {
                    address: contractAddress,
                    contract: contract.contractPath,
                    constructorArguments: contract.constructorArgs
                });

                console.log(`   ✓ ${contract.name} verified successfully!`);
                verifiedContracts.push({
                    name: contract.name,
                    address: contractAddress,
                    explorerUrl: getExplorerUrl(network, contractAddress)
                });

            } catch (error) {
                console.log(`   ✗ Verification failed for ${contract.name}:`);
                console.log(`     ${error.message}`);

                failedVerifications.push({
                    name: contract.name,
                    error: error.message
                });

                // Sometimes verification fails due to timing, try again after a delay
                if (error.message.includes("Contract source code not verified")) {
                    console.log(`   Waiting 30 seconds before retry...`);
                    await new Promise(resolve => setTimeout(resolve, 30000));

                    try {
                        await hre.run("verify:verify", {
                            address: contractAddress,
                            contract: contract.contractPath,
                            constructorArguments: contract.constructorArgs
                        });
                        console.log(`   ✓ ${contract.name} verified on retry!`);
                        verifiedContracts.push({
                            name: contract.name,
                            address: contractAddress,
                            explorerUrl: getExplorerUrl(network, contractAddress)
                        });
                        // Remove from failed list
                        failedVerifications.pop();
                    } catch (retryError) {
                        console.log(`   ✗ Retry failed for ${contract.name}: ${retryError.message}`);
                    }
                }
            }
        }

        // Generate verification report
        const report = {
            timestamp: new Date().toISOString(),
            network: network,
            chainId: chainId,
            verifiedContracts: verifiedContracts,
            failedVerifications: failedVerifications,
            summary: {
                total: contractsToVerify.length,
                verified: verifiedContracts.length,
                failed: failedVerifications.length
            }
        };

        // Save verification report
        const reportDir = path.join(deploymentsDir, "verification");
        if (!fs.existsSync(reportDir)) {
            fs.mkdirSync(reportDir, { recursive: true });
        }

        const reportFile = path.join(reportDir, `verification-report-${network}-${Date.now()}.json`);
        fs.writeFileSync(reportFile, JSON.stringify(report, null, 2));

        // Print summary
        console.log("\n" + "=".repeat(60));
        console.log("CONTRACT VERIFICATION SUMMARY");
        console.log("=".repeat(60));

        if (verifiedContracts.length > 0) {
            console.log(`✓ Successfully verified ${verifiedContracts.length} contract(s):`);
            verifiedContracts.forEach(contract => {
                console.log(`  - ${contract.name}: ${contract.address}`);
                console.log(`    Explorer: ${contract.explorerUrl}`);
            });
        }

        if (failedVerifications.length > 0) {
            console.log(`\n✗ Failed to verify ${failedVerifications.length} contract(s):`);
            failedVerifications.forEach(failed => {
                console.log(`  - ${failed.name}: ${failed.error}`);
            });
        }

        console.log(`\n📄 Verification report saved to: ${reportFile}`);
        console.log("=".repeat(60));

        // Show next steps
        if (verifiedContracts.length === 0) {
            console.log("\n📋 MANUAL VERIFICATION STEPS:");
            console.log("1. Deploy contracts to your target network");
            console.log("2. Set CRONOSCAN_API_KEY environment variable");
            console.log("3. Run this script again, or verify manually:");
            contractsToVerify.forEach(contract => {
                console.log(`   npx hardhat verify --network ${network} <${contract.name}_address> --contract "${contract.contractPath}"`);
            });
        } else {
            console.log("\n🎉 Contract verification complete!");
        }

        return verifiedContracts.length > 0;

    } catch (error) {
        console.error("❌ Contract verification failed:", error.message);
        return false;
    }
}

/**
 * Get the explorer URL for a contract address
 */
function getExplorerUrl(network, address) {
    if (network === "cronosTestnet") {
        return `https://testnet.cronoscan.com/address/${address}`;
    } else if (network === "cronosMainnet") {
        return `https://cronoscan.com/address/${address}`;
    } else {
        return `https://explorer.cronos.org/address/${address}`;
    }
}

// Run the verification
verifyContracts()
    .then((success) => {
        process.exit(success ? 0 : 1);
    })
    .catch((error) => {
        console.error("❌ Unexpected error:", error);
        process.exit(1);
    });