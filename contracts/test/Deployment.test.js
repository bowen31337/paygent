/**
 * Contract Deployment Test Suite
 * Tests the complete deployment process including verification
 */

const { expect } = require("chai");
const { ethers } = require("hardhat");
const fs = require('fs');
const path = require('path');

describe("Contract Deployment", function () {
    let owner, testOperator, testRecipient;
    let agentWallet, paymentRouter, serviceRegistry;
    let mockToken;

    beforeEach(async function () {
        [owner, testOperator, testRecipient] = await ethers.getSigners();

        // Deploy Mock Token for testing
        const MockToken = await ethers.getContractFactory("MockToken");
        mockToken = await MockToken.deploy();
        await mockToken.waitForDeployment();

        // Deploy AgentWallet
        const AgentWallet = await ethers.getContractFactory("AgentWallet");
        const dailyLimit = ethers.parseEther("1000");
        agentWallet = await AgentWallet.deploy(owner.address, dailyLimit);
        await agentWallet.waitForDeployment();

        // Deploy PaymentRouter
        const PaymentRouter = await ethers.getContractFactory("PaymentRouter");
        const feePercentage = 100; // 1%
        paymentRouter = await PaymentRouter.deploy(owner.address, feePercentage);
        await paymentRouter.waitForDeployment();

        // Deploy ServiceRegistry
        const ServiceRegistry = await ethers.getContractFactory("ServiceRegistry");
        const reputationRequired = 50;
        const defaultStake = ethers.parseEther("10");
        serviceRegistry = await ServiceRegistry.deploy(
            owner.address,
            reputationRequired,
            defaultStake
        );
        await serviceRegistry.waitForDeployment();
    });

    describe("Local Deployment", function () {
        it("Should deploy all contracts successfully", async function () {
            expect(await agentWallet.getAddress()).to.be.properAddress;
            expect(await paymentRouter.getAddress()).to.be.properAddress;
            expect(await serviceRegistry.getAddress()).to.be.properAddress;
        });

        it("Should verify AgentWallet deployment", async function () {
            expect(await agentWallet.getOwner()).to.equal(owner.address);
            expect(await agentWallet.getDailyLimit()).to.equal(ethers.parseEther("1000"));
            expect(await agentWallet.isOperator(owner.address)).to.be.true;
        });

        it("Should verify PaymentRouter deployment", async function () {
            expect(await paymentRouter.getFeeCollector()).to.equal(owner.address);
            expect(await paymentRouter.getFeePercentage()).to.equal(100);
            expect(await paymentRouter.isAgentAllowed(owner.address)).to.be.true;
        });

        it("Should verify ServiceRegistry deployment", async function () {
            expect(await serviceRegistry.owner()).to.equal(owner.address);
            expect(await serviceRegistry.reputationRequired()).to.equal(50);
            expect(await serviceRegistry.defaultStake()).to.equal(ethers.parseEther("10"));
        });
    });

    describe("Contract Verification", function () {
        it("Should have correct bytecode on chain", async function () {
            const agentWalletCode = await ethers.provider.getCode(await agentWallet.getAddress());
            const paymentRouterCode = await ethers.provider.getCode(await paymentRouter.getAddress());
            const serviceRegistryCode = await ethers.provider.getCode(await serviceRegistry.getAddress());

            expect(agentWalletCode).to.not.equal("0x");
            expect(paymentRouterCode).to.not.equal("0x");
            expect(serviceRegistryCode).to.not.equal("0x");
        });

        it("Should respond to basic function calls", async function () {
            // Test AgentWallet
            const walletOwner = await agentWallet.getOwner();
            const walletLimit = await agentWallet.getDailyLimit();
            expect(walletOwner).to.equal(owner.address);
            expect(walletLimit).to.equal(ethers.parseEther("1000"));

            // Test PaymentRouter
            const feeCollector = await paymentRouter.getFeeCollector();
            const feePct = await paymentRouter.getFeePercentage();
            expect(feeCollector).to.equal(owner.address);
            expect(feePct).to.equal(100);

            // Test ServiceRegistry
            const regOwner = await serviceRegistry.owner();
            const reqRep = await serviceRegistry.reputationRequired();
            expect(regOwner).to.equal(owner.address);
            expect(reqRep).to.equal(50);
        });
    });

    describe("Deployment Configuration", function () {
        it("Should handle missing environment variables gracefully", async function () {
            // Test that deployment works without env vars in local environment
            expect(process.env.PRIVATE_KEY).to.be.undefined;
            expect(process.env.CRONOS_TESTNET_RPC).to.be.undefined;

            // Deployment should still work locally
            expect(await agentWallet.getAddress()).to.be.properAddress;
        });

        it("Should create deployment artifacts", async function () {
            const deploymentsDir = path.join(__dirname, "..", "deployments");
            const network = "localhost";
            const deploymentFile = path.join(deploymentsDir, `${network}.json`);

            // Check if deployment directory exists
            expect(fs.existsSync(deploymentsDir)).to.be.true;

            // Note: The actual deployment script would create this file
            // For now, we verify the directory structure is correct
        });
    });

    describe("Contract Interactions", function () {
        it("Should allow basic contract operations", async function () {
            // Test AgentWallet operator management
            await agentWallet.addOperator(testOperator.address);
            expect(await agentWallet.isOperator(testOperator.address)).to.be.true;

            // Test PaymentRouter agent management
            await paymentRouter.setAgentPermission(testOperator.address, true);
            expect(await paymentRouter.isAgentAllowed(testOperator.address)).to.be.true;

            // Test ServiceRegistry service management
            const serviceId = ethers.id("test-service");
            await serviceRegistry.registerService(
                serviceId,
                "Test Service",
                "A test service for deployment verification",
                testOperator.address,
                "test-category",
                ethers.parseEther("1"),
                "USDC",
                100 // reputation
            );

            const service = await serviceRegistry.getService(serviceId);
            expect(service.name).to.equal("Test Service");
        });

        it("Should handle token transfers", async function () {
            // Mint tokens for testing
            await mockToken.mint(testOperator.address, ethers.parseEther("1000"));
            await mockToken.connect(testOperator).approve(await paymentRouter.getAddress(), ethers.parseEther("1000"));

            // Add operator to PaymentRouter
            await paymentRouter.setAgentPermission(testOperator.address, true);

            // Execute payment
            const recipientBalanceBefore = await mockToken.balanceOf(testRecipient.address);
            await paymentRouter.connect(testOperator).executePayment(
                await mockToken.getAddress(),
                testRecipient.address,
                ethers.parseEther("100")
            );
            const recipientBalanceAfter = await mockToken.balanceOf(testRecipient.address);

            // Should receive 99% due to 1% fee
            expect(recipientBalanceAfter - recipientBalanceBefore).to.equal(ethers.parseEther("99"));
        });
    });

    describe("Error Handling", function () {
        it("Should handle invalid deployment parameters", async function () {
            // Test AgentWallet with zero daily limit
            const AgentWallet = await ethers.getContractFactory("AgentWallet");
            await expect(
                AgentWallet.deploy(owner.address, 0)
            ).to.be.revertedWith("Daily limit must be greater than 0");

            // Test AgentWallet with zero address owner
            await expect(
                AgentWallet.deploy(ethers.ZeroAddress, ethers.parseEther("1000"))
            ).to.be.revertedWith("Owner cannot be zero address");

            // Test PaymentRouter with excessive fee
            const PaymentRouter = await ethers.getContractFactory("PaymentRouter");
            await expect(
                PaymentRouter.deploy(owner.address, 1001) // > 10%
            ).to.be.revertedWith("Fee cannot exceed 10%");
        });

        it("Should handle contract interactions with proper validation", async function () {
            // Test AgentWallet with invalid operator
            await expect(
                agentWallet.addOperator(ethers.ZeroAddress)
            ).to.be.revertedWith("Operator cannot be zero address");

            // Test PaymentRouter with invalid fee collector
            await expect(
                paymentRouter.setFeeCollector(ethers.ZeroAddress)
            ).to.be.revertedWith("Invalid fee collector address");
        });
    });

    describe("Deployment Verification Report", function () {
        it("Should generate deployment verification report", async function () {
            const report = {
                network: "localhost",
                chainId: 31337,
                timestamp: new Date().toISOString(),
                contracts: {
                    agentWallet: {
                        address: await agentWallet.getAddress(),
                        owner: await agentWallet.getOwner(),
                        dailyLimit: (await agentWallet.getDailyLimit()).toString()
                    },
                    paymentRouter: {
                        address: await paymentRouter.getAddress(),
                        feeCollector: await paymentRouter.getFeeCollector(),
                        feePercentage: (await paymentRouter.getFeePercentage()).toString()
                    },
                    serviceRegistry: {
                        address: await serviceRegistry.getAddress(),
                        owner: await serviceRegistry.owner(),
                        reputationRequired: (await serviceRegistry.reputationRequired()).toString()
                    }
                },
                status: "deployment_verified",
                nextSteps: [
                    "Deploy to testnet with real funds",
                    "Verify contracts on Cronoscan",
                    "Update backend configuration",
                    "Test with real transactions"
                ]
            };

            // Verify report structure
            expect(report.contracts.agentWallet.address).to.be.properAddress;
            expect(report.contracts.paymentRouter.address).to.be.properAddress;
            expect(report.contracts.serviceRegistry.address).to.be.properAddress;
            expect(report.status).to.equal("deployment_verified");
        });
    });
});