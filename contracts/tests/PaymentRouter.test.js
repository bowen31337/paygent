// SPDX-License-Identifier: MIT
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("PaymentRouter", function () {
    let PaymentRouter;
    let paymentRouter;
    let owner;
    let agent;
    let recipient;
    let feeCollector;
    let nonAllowed;
    let mockToken;

    beforeEach(async function () {
        [owner, agent, recipient, feeCollector, nonAllowed] = await ethers.getSigners();

        // Deploy mock ERC20 token
        const MockToken = await ethers.getContractFactory("MockToken");
        mockToken = await MockToken.deploy();
        await mockToken.waitForDeployment();

        // Deploy PaymentRouter
        PaymentRouter = await ethers.getContractFactory("PaymentRouter");
        const feePercentage = 100; // 1%
        paymentRouter = await PaymentRouter.deploy(feeCollector.address, feePercentage);
        await paymentRouter.waitForDeployment();
    });

    describe("Deployment", function () {
        it("Should set the correct owner", async function () {
            expect(await paymentRouter.owner()).to.equal(owner.address);
        });

        it("Should set the correct fee collector", async function () {
            expect(await paymentRouter.feeCollector()).to.equal(feeCollector.address);
        });

        it("Should set the correct fee percentage", async function () {
            expect(await paymentRouter.feePercentage()).to.equal(100);
        });

        it("Should make owner an allowed agent", async function () {
            expect(await paymentRouter.allowedAgents(owner.address)).to.be.true;
        });
    });

    describe("Fee Management", function () {
        it("Should allow owner to set fee percentage", async function () {
            await paymentRouter.setFeePercentage(200); // 2%
            expect(await paymentRouter.feePercentage()).to.equal(200);
        });

        it("Should emit FeeUpdated event", async function () {
            await expect(paymentRouter.setFeePercentage(200))
                .to.emit(paymentRouter, "FeeUpdated")
                .withArgs(200);
        });

        it("Should revert when fee exceeds 10%", async function () {
            await expect(
                paymentRouter.setFeePercentage(1001)
            ).to.be.revertedWith("Fee cannot exceed 10%");
        });

        it("Should revert when non-owner sets fee", async function () {
            await expect(
                paymentRouter.connect(nonAllowed).setFeePercentage(200)
            ).to.be.revertedWith("Only owner can call this function");
        });

        it("Should allow owner to set fee collector", async function () {
            const newCollector = agent.address;
            await paymentRouter.setFeeCollector(newCollector);
            expect(await paymentRouter.feeCollector()).to.equal(newCollector);
        });

        it("Should emit FeeCollectorUpdated event", async function () {
            const newCollector = agent.address;
            await expect(paymentRouter.setFeeCollector(newCollector))
                .to.emit(paymentRouter, "FeeCollectorUpdated")
                .withArgs(newCollector);
        });

        it("Should revert when setting zero address as fee collector", async function () {
            await expect(
                paymentRouter.setFeeCollector(ethers.ZeroAddress)
            ).to.be.revertedWith("Invalid fee collector address");
        });
    });

    describe("Agent Permission", function () {
        it("Should allow owner to add agent", async function () {
            await paymentRouter.setAgentPermission(agent.address, true);
            expect(await paymentRouter.allowedAgents(agent.address)).to.be.true;
        });

        it("Should emit AgentPermissionUpdated event", async function () {
            await expect(paymentRouter.setAgentPermission(agent.address, true))
                .to.emit(paymentRouter, "AgentPermissionUpdated")
                .withArgs(agent.address, true);
        });

        it("Should allow owner to remove agent", async function () {
            await paymentRouter.setAgentPermission(agent.address, true);
            await paymentRouter.setAgentPermission(agent.address, false);
            expect(await paymentRouter.allowedAgents(agent.address)).to.be.false;
        });

        it("Should revert when non-owner sets permission", async function () {
            await expect(
                paymentRouter.connect(nonAllowed).setAgentPermission(agent.address, true)
            ).to.be.revertedWith("Only owner can call this function");
        });
    });

    describe("Execute Payment", function () {
        const paymentAmount = ethers.parseEther("100");

        beforeEach(async function () {
            // Add agent
            await paymentRouter.setAgentPermission(agent.address, true);

            // Mint and approve tokens
            await mockToken.mint(agent.address, ethers.parseEther("1000"));
            await mockToken.connect(agent).approve(await paymentRouter.getAddress(), ethers.parseEther("1000"));
        });

        it("Should execute single payment correctly", async function () {
            const recipientBalanceBefore = await mockToken.balanceOf(recipient.address);
            const feeCollectorBalanceBefore = await mockToken.balanceOf(feeCollector.address);

            await paymentRouter.connect(agent).executePayment(
                await mockToken.getAddress(),
                recipient.address,
                paymentAmount
            );

            const recipientBalanceAfter = await mockToken.balanceOf(recipient.address);
            const feeCollectorBalanceAfter = await mockToken.balanceOf(feeCollector.address);

            // 1% fee = 1 token, net = 99 tokens
            expect(recipientBalanceAfter - recipientBalanceBefore).to.equal(ethers.parseEther("99"));
            expect(feeCollectorBalanceAfter - feeCollectorBalanceBefore).to.equal(ethers.parseEther("1"));
        });

        it("Should emit PaymentExecuted event", async function () {
            await expect(
                paymentRouter.connect(agent).executePayment(
                    await mockToken.getAddress(),
                    recipient.address,
                    paymentAmount
                )
            )
            .to.emit(paymentRouter, "PaymentExecuted")
            .withArgs(
                agent.address,
                recipient.address,
                await mockToken.getAddress(),
                paymentAmount,
                ethers.parseEther("1"), // fee
                ethers.parseEther("99") // net
            );
        });

        it("Should revert when non-allowed agent tries payment", async function () {
            await expect(
                paymentRouter.connect(nonAllowed).executePayment(
                    await mockToken.getAddress(),
                    recipient.address,
                    paymentAmount
                )
            ).to.be.revertedWith("Agent not allowed");
        });

        it("Should revert with zero recipient", async function () {
            await expect(
                paymentRouter.connect(agent).executePayment(
                    await mockToken.getAddress(),
                    ethers.ZeroAddress,
                    paymentAmount
                )
            ).to.be.revertedWith("Invalid recipient");
        });

        it("Should revert with zero amount", async function () {
            await expect(
                paymentRouter.connect(agent).executePayment(
                    await mockToken.getAddress(),
                    recipient.address,
                    0
                )
            ).to.be.revertedWith("Amount must be greater than 0");
        });

        it("Should revert with zero token address", async function () {
            await expect(
                paymentRouter.connect(agent).executePayment(
                    ethers.ZeroAddress,
                    recipient.address,
                    paymentAmount
                )
            ).to.be.revertedWith("Invalid token address");
        });
    });

    describe("Batch Payment", function () {
        const recipients = [];
        const amounts = [];

        beforeEach(async function () {
            // Setup recipients and amounts
            const [r1, r2, r3] = await ethers.getSigners();
            recipients.push(r1.address, r2.address, r3.address);
            amounts.push(
                ethers.parseEther("100"),
                ethers.parseEther("200"),
                ethers.parseEther("300")
            );

            // Add agent
            await paymentRouter.setAgentPermission(agent.address, true);

            // Mint and approve tokens
            const totalAmount = ethers.parseEther("600");
            await mockToken.mint(agent.address, totalAmount);
            await mockToken.connect(agent).approve(await paymentRouter.getAddress(), totalAmount);
        });

        it("Should execute batch payment correctly", async function () {
            const balancesBefore = await Promise.all(
                recipients.map(addr => mockToken.balanceOf(addr))
            );
            const feeCollectorBalanceBefore = await mockToken.balanceOf(feeCollector.address);

            await paymentRouter.connect(agent).batchPay(
                await mockToken.getAddress(),
                recipients,
                amounts
            );

            const balancesAfter = await Promise.all(
                recipients.map(addr => mockToken.balanceOf(addr))
            );
            const feeCollectorBalanceAfter = await mockToken.balanceOf(feeCollector.address);

            // Each recipient gets 99% of their amount
            expect(balancesAfter[0] - balancesBefore[0]).to.equal(ethers.parseEther("99")); // 100 * 0.99
            expect(balancesAfter[1] - balancesBefore[1]).to.equal(ethers.parseEther("198")); // 200 * 0.99
            expect(balancesAfter[2] - balancesBefore[2]).to.equal(ethers.parseEther("297")); // 300 * 0.99

            // Fee collector gets 1% of total = 6 tokens
            expect(feeCollectorBalanceAfter - feeCollectorBalanceBefore).to.equal(ethers.parseEther("6"));
        });

        it("Should emit BatchPaymentExecuted event", async function () {
            await expect(
                paymentRouter.connect(agent).batchPay(
                    await mockToken.getAddress(),
                    recipients,
                    amounts
                )
            )
            .to.emit(paymentRouter, "BatchPaymentExecuted")
            .withArgs(
                agent.address,
                await mockToken.getAddress(),
                ethers.parseEther("600"), // total amount
                ethers.parseEther("6"),   // total fee
                ethers.parseEther("594"), // total net
                3                          // payment count
            );
        });

        it("Should revert when arrays have different lengths", async function () {
            const badAmounts = [ethers.parseEther("100")];

            await expect(
                paymentRouter.connect(agent).batchPay(
                    await mockToken.getAddress(),
                    recipients,
                    badAmounts
                )
            ).to.be.revertedWith("Arrays must have same length");
        });

        it("Should revert with empty arrays", async function () {
            await expect(
                paymentRouter.connect(agent).batchPay(
                    await mockToken.getAddress(),
                    [],
                    []
                )
            ).to.be.revertedWith("Empty arrays not allowed");
        });

        it("Should revert with invalid recipient in batch", async function () {
            const badRecipients = [recipients[0], ethers.ZeroAddress, recipients[2]];

            await expect(
                paymentRouter.connect(agent).batchPay(
                    await mockToken.getAddress(),
                    badRecipients,
                    amounts
                )
            ).to.be.revertedWith("Invalid recipient");
        });

        it("Should revert with zero amount in batch", async function () {
            const badAmounts = [ethers.parseEther("100"), 0, ethers.parseEther("300")];

            await expect(
                paymentRouter.connect(agent).batchPay(
                    await mockToken.getAddress(),
                    recipients,
                    badAmounts
                )
            ).to.be.revertedWith("Amount must be greater than 0");
        });
    });

    describe("View Functions", function () {
        it("Should return correct payment details", async function () {
            const [feeAmount, netAmount] = await paymentRouter.getPaymentDetails(ethers.parseEther("100"));
            expect(feeAmount).to.equal(ethers.parseEther("1")); // 1%
            expect(netAmount).to.equal(ethers.parseEther("99"));
        });

        it("Should return correct agent permission status", async function () {
            expect(await paymentRouter.isAgentAllowed(owner.address)).to.be.true;
            expect(await paymentRouter.isAgentAllowed(agent.address)).to.be.false;
        });

        it("Should return correct fee collector", async function () {
            expect(await paymentRouter.getFeeCollector()).to.equal(feeCollector.address);
        });

        it("Should return correct fee percentage", async function () {
            expect(await paymentRouter.getFeePercentage()).to.equal(100);
        });
    });
});
