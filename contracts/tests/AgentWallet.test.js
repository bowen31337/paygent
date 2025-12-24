// SPDX-License-Identifier: MIT
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("AgentWallet", function () {
    let AgentWallet;
    let agentWallet;
    let owner;
    let operator;
    let nonOwner;
    let recipient;
    let mockToken;

    beforeEach(async function () {
        [owner, operator, nonOwner, recipient] = await ethers.getSigners();

        // Deploy mock ERC20 token for testing
        const MockToken = await ethers.getContractFactory("MockToken");
        mockToken = await MockToken.deploy();
        await mockToken.waitForDeployment();

        // Deploy AgentWallet
        AgentWallet = await ethers.getContractFactory("AgentWallet");
        const dailyLimit = ethers.parseEther("1000");
        agentWallet = await AgentWallet.deploy(owner.address, dailyLimit);
        await agentWallet.waitForDeployment();
    });

    describe("Deployment", function () {
        it("Should set the correct owner", async function () {
            expect(await agentWallet.owner()).to.equal(owner.address);
        });

        it("Should set the correct daily limit", async function () {
            const expectedLimit = ethers.parseEther("1000");
            expect(await agentWallet.dailyLimit()).to.equal(expectedLimit);
        });

        it("Should make owner an operator", async function () {
            expect(await agentWallet.isOperator(owner.address)).to.be.true;
        });

        it("Should revert with zero owner", async function () {
            await expect(
                AgentWallet.deploy(ethers.ZeroAddress, ethers.parseEther("1000"))
            ).to.be.revertedWith("Owner cannot be zero address");
        });

        it("Should revert with zero daily limit", async function () {
            await expect(
                AgentWallet.deploy(owner.address, 0)
            ).to.be.revertedWith("Daily limit must be greater than 0");
        });
    });

    describe("Operator Management", function () {
        it("Should allow owner to add operator", async function () {
            await agentWallet.addOperator(operator.address);
            expect(await agentWallet.isOperator(operator.address)).to.be.true;
        });

        it("Should emit OperatorAdded event", async function () {
            await expect(agentWallet.addOperator(operator.address))
                .to.emit(agentWallet, "OperatorAdded")
                .withArgs(operator.address);
        });

        it("Should revert when non-owner adds operator", async function () {
            await expect(
                agentWallet.connect(nonOwner).addOperator(operator.address)
            ).to.be.revertedWith("Only owner can call this function");
        });

        it("Should revert when adding existing operator", async function () {
            await agentWallet.addOperator(operator.address);
            await expect(
                agentWallet.addOperator(operator.address)
            ).to.be.revertedWith("Operator already exists");
        });

        it("Should revert when adding zero address as operator", async function () {
            await expect(
                agentWallet.addOperator(ethers.ZeroAddress)
            ).to.be.revertedWith("Operator cannot be zero address");
        });

        it("Should allow owner to remove operator", async function () {
            await agentWallet.addOperator(operator.address);
            await agentWallet.removeOperator(operator.address);
            expect(await agentWallet.isOperator(operator.address)).to.be.false;
        });

        it("Should emit OperatorRemoved event", async function () {
            await agentWallet.addOperator(operator.address);
            await expect(agentWallet.removeOperator(operator.address))
                .to.emit(agentWallet, "OperatorRemoved")
                .withArgs(operator.address);
        });

        it("Should revert when removing non-existent operator", async function () {
            await expect(
                agentWallet.removeOperator(operator.address)
            ).to.be.revertedWith("Operator does not exist");
        });
    });

    describe("Daily Limit Management", function () {
        it("Should allow owner to set daily limit", async function () {
            const newLimit = ethers.parseEther("500");
            await agentWallet.setDailyLimit(newLimit);
            expect(await agentWallet.dailyLimit()).to.equal(newLimit);
        });

        it("Should emit DailyLimitSet event", async function () {
            const newLimit = ethers.parseEther("500");
            await expect(agentWallet.setDailyLimit(newLimit))
                .to.emit(agentWallet, "DailyLimitSet")
                .withArgs(newLimit);
        });

        it("Should revert when non-owner sets daily limit", async function () {
            await expect(
                agentWallet.connect(nonOwner).setDailyLimit(ethers.parseEther("500"))
            ).to.be.revertedWith("Only owner can call this function");
        });

        it("Should revert when setting zero daily limit", async function () {
            await expect(
                agentWallet.setDailyLimit(0)
            ).to.be.revertedWith("Daily limit must be greater than 0");
        });
    });

    describe("Execute Payment", function () {
        const paymentAmount = ethers.parseEther("100");

        beforeEach(async function () {
            // Add operator
            await agentWallet.addOperator(operator.address);

            // Mint tokens to operator
            await mockToken.mint(operator.address, ethers.parseEther("1000"));

            // Approve agentWallet to spend operator's tokens
            await mockToken.connect(operator).approve(await agentWallet.getAddress(), ethers.parseEther("1000"));
        });

        it("Should allow operator to execute payment", async function () {
            const recipientBalanceBefore = await mockToken.balanceOf(recipient.address);

            await agentWallet.connect(operator).executePayment(
                await mockToken.getAddress(),
                recipient.address,
                paymentAmount
            );

            const recipientBalanceAfter = await mockToken.balanceOf(recipient.address);
            expect(recipientBalanceAfter - recipientBalanceBefore).to.equal(paymentAmount);
        });

        it("Should emit PaymentExecuted event", async function () {
            const remainingAllowance = ethers.parseEther("900"); // 1000 - 100

            await expect(
                agentWallet.connect(operator).executePayment(
                    await mockToken.getAddress(),
                    recipient.address,
                    paymentAmount
                )
            )
            .to.emit(agentWallet, "PaymentExecuted")
            .withArgs(
                operator.address,
                recipient.address,
                await mockToken.getAddress(),
                paymentAmount,
                remainingAllowance
            );
        });

        it("Should track daily spending", async function () {
            await agentWallet.connect(operator).executePayment(
                await mockToken.getAddress(),
                recipient.address,
                paymentAmount
            );

            const spentToday = await agentWallet.getSpentToday();
            expect(spentToday).to.equal(paymentAmount);
        });

        it("Should revert when non-operator tries to execute payment", async function () {
            await expect(
                agentWallet.connect(nonOwner).executePayment(
                    await mockToken.getAddress(),
                    recipient.address,
                    paymentAmount
                )
            ).to.be.revertedWith("Only operator can call this function");
        });

        it("Should revert when payment exceeds daily limit", async function () {
            const tooMuch = ethers.parseEther("1100"); // More than 1000 daily limit

            await expect(
                agentWallet.connect(operator).executePayment(
                    await mockToken.getAddress(),
                    recipient.address,
                    tooMuch
                )
            ).to.be.revertedWith("Daily spending limit exceeded");
        });

        it("Should revert with zero recipient", async function () {
            await expect(
                agentWallet.connect(operator).executePayment(
                    await mockToken.getAddress(),
                    ethers.ZeroAddress,
                    paymentAmount
                )
            ).to.be.revertedWith("Invalid recipient");
        });

        it("Should revert with zero amount", async function () {
            await expect(
                agentWallet.connect(operator).executePayment(
                    await mockToken.getAddress(),
                    recipient.address,
                    0
                )
            ).to.be.revertedWith("Amount must be greater than 0");
        });

        it("Should revert with zero token address", async function () {
            await expect(
                agentWallet.connect(operator).executePayment(
                    ethers.ZeroAddress,
                    recipient.address,
                    paymentAmount
                )
            ).to.be.revertedWith("Invalid token address");
        });

        it("Should allow multiple payments within limit", async function () {
            // First payment
            await agentWallet.connect(operator).executePayment(
                await mockToken.getAddress(),
                recipient.address,
                ethers.parseEther("400")
            );

            // Second payment
            await agentWallet.connect(operator).executePayment(
                await mockToken.getAddress(),
                recipient.address,
                ethers.parseEther("500")
            );

            // Third payment should fail (400 + 500 + 200 = 1100 > 1000)
            await expect(
                agentWallet.connect(operator).executePayment(
                    await mockToken.getAddress(),
                    recipient.address,
                    ethers.parseEther("200")
                )
            ).to.be.revertedWith("Daily spending limit exceeded");
        });
    });

    describe("Withdraw", function () {
        it("Should allow owner to call withdraw (emits event)", async function () {
            const tokenAddress = await mockToken.getAddress();
            const amount = ethers.parseEther("100");

            await expect(agentWallet.withdraw(tokenAddress, amount))
                .to.emit(agentWallet, "Withdrawal")
                .withArgs(owner.address, tokenAddress, amount);
        });

        it("Should revert when non-owner tries to withdraw", async function () {
            await expect(
                agentWallet.connect(nonOwner).withdraw(
                    await mockToken.getAddress(),
                    ethers.parseEther("100")
                )
            ).to.be.revertedWith("Only owner can call this function");
        });

        it("Should revert with zero token address", async function () {
            await expect(
                agentWallet.withdraw(ethers.ZeroAddress, ethers.parseEther("100"))
            ).to.be.revertedWith("Invalid token address");
        });

        it("Should revert with zero amount", async function () {
            await expect(
                agentWallet.withdraw(await mockToken.getAddress(), 0)
            ).to.be.revertedWith("Amount must be greater than 0");
        });
    });

    describe("View Functions", function () {
        it("Should return correct remaining allowance", async function () {
            const remaining = await agentWallet.getRemainingAllowance();
            expect(remaining).to.equal(ethers.parseEther("1000"));
        });

        it("Should return correct owner", async function () {
            expect(await agentWallet.getOwner()).to.equal(owner.address);
        });

        it("Should return correct daily limit", async function () {
            expect(await agentWallet.getDailyLimit()).to.equal(ethers.parseEther("1000"));
        });

        it("Should return correct operator status", async function () {
            expect(await agentWallet.isOperatorAddress(owner.address)).to.be.true;
            expect(await agentWallet.isOperatorAddress(operator.address)).to.be.false;
        });

        it("Should return 0 spent today for new day", async function () {
            expect(await agentWallet.getSpentToday()).to.equal(0);
        });
    });
});

// Mock ERC20 token for testing
describe("MockToken", function () {
    let MockToken;
    let mockToken;
    let owner;
    let recipient;

    beforeEach(async function () {
        [owner, recipient] = await ethers.getSigners();
        MockToken = await ethers.getContractFactory("MockToken");
        mockToken = await MockToken.deploy();
        await mockToken.waitForDeployment();
    });

    it("Should mint tokens correctly", async function () {
        const amount = ethers.parseEther("1000");
        await mockToken.mint(owner.address, amount);
        expect(await mockToken.balanceOf(owner.address)).to.equal(amount);
    });

    it("Should transfer tokens correctly", async function () {
        const amount = ethers.parseEther("100");
        await mockToken.mint(owner.address, amount);
        await mockToken.transfer(recipient.address, amount);
        expect(await mockToken.balanceOf(recipient.address)).to.equal(amount);
    });
});
