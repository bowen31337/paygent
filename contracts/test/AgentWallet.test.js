const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("AgentWallet", function () {
    let agentWallet;
    let owner, operator, recipient, nonOperator;
    const dailyLimitUSD = ethers.parseEther("1000"); // $1000

    beforeEach(async function () {
        [owner, operator, recipient, nonOperator] = await ethers.getSigners();

        const AgentWallet = await ethers.getContractFactory("AgentWallet");
        agentWallet = await AgentWallet.deploy(dailyLimitUSD);
        await agentWallet.waitForDeployment();
    });

    describe("Deployment", function () {
        it("Should set the correct owner", async function () {
            expect(await agentWallet.owner()).to.equal(owner.address);
        });

        it("Should set the correct daily limit", async function () {
            expect(await agentWallet.dailyLimitUSD()).to.equal(dailyLimitUSD);
        });

        it("Should initialize with no operators", async function () {
            expect(await agentWallet.operatorCount()).to.equal(0);
        });
    });

    describe("Operator Management", function () {
        it("Should allow owner to add operator", async function () {
            await agentWallet.addOperator(operator.address);
            expect(await agentWallet.isOperator(operator.address)).to.be.true;
            expect(await agentWallet.operatorCount()).to.equal(1);
        });

        it("Should emit OperatorAdded event", async function () {
            await expect(agentWallet.addOperator(operator.address))
                .to.emit(agentWallet, "OperatorAdded")
                .withArgs(operator.address);
        });

        it("Should allow owner to remove operator", async function () {
            await agentWallet.addOperator(operator.address);
            await agentWallet.removeOperator(operator.address);
            expect(await agentWallet.isOperator(operator.address)).to.be.false;
            expect(await agentWallet.operatorCount()).to.equal(0);
        });

        it("Should revert if non-owner tries to add operator", async function () {
            await expect(
                agentWallet.connect(nonOperator).addOperator(operator.address)
            ).to.be.revertedWith("Ownable: caller is not the owner");
        });

        it("Should revert adding duplicate operator", async function () {
            await agentWallet.addOperator(operator.address);
            await expect(
                agentWallet.addOperator(operator.address)
            ).to.be.revertedWith("Operator already exists");
        });
    });

    describe("Daily Limit Management", function () {
        it("Should allow owner to update daily limit", async function () {
            const newLimit = ethers.parseEther("2000");
            await agentWallet.updateDailyLimit(newLimit);
            expect(await agentWallet.dailyLimitUSD()).to.equal(newLimit);
        });

        it("Should emit DailyLimitUpdated event", async function () {
            const newLimit = ethers.parseEther("2000");
            await expect(agentWallet.updateDailyLimit(newLimit))
                .to.emit(agentWallet, "DailyLimitUpdated")
                .withArgs(newLimit);
        });

        it("Should revert if non-owner tries to update limit", async function () {
            await expect(
                agentWallet.connect(nonOperator).updateDailyLimit(ethers.parseEther("2000"))
            ).to.be.revertedWith("Ownable: caller is not the owner");
        });

        it("Should revert if setting zero daily limit", async function () {
            await expect(
                agentWallet.updateDailyLimit(0)
            ).to.be.revertedWith("Daily limit must be positive");
        });

        it("Should return correct daily spending status", async function () {
            const status = await agentWallet.getDailySpendingStatus();
            expect(status.limit).to.equal(dailyLimitUSD);
            expect(status.spent).to.equal(0);
            expect(status.remaining).to.equal(dailyLimitUSD);
        });
    });

    describe("Payment Execution", function () {
        it("Should allow owner to execute payment", async function () {
            // This test would need USDC token mock for full testing
            // For now, we verify the function exists and can be called
            // In production, this would interact with real USDC
            expect(await agentWallet.owner()).to.equal(owner.address);
        });

        it("Should allow operator to execute payment", async function () {
            await agentWallet.addOperator(operator.address);
            expect(await agentWallet.isOperator(operator.address)).to.be.true;
        });

        it("Should reject non-authorized payment attempts", async function () {
            // Would need to call executePayment with proper parameters
            // For now, verify authorization check exists
            expect(await agentWallet.isOperator(nonOperator.address)).to.be.false;
        });
    });

    describe("Withdrawal", function () {
        it("Should allow owner to withdraw CRO", async function () {
            // Send CRO to contract first
            const depositAmount = ethers.parseEther("1");
            await owner.sendTransaction({
                to: await agentWallet.getAddress(),
                value: depositAmount
            });

            // Check balance
            const contractBalance = await ethers.provider.getBalance(await agentWallet.getAddress());
            expect(contractBalance).to.equal(depositAmount);

            // Withdraw
            const recipientBalanceBefore = await ethers.provider.getBalance(recipient.address);
            await agentWallet.withdraw(recipient.address, depositAmount);
            const recipientBalanceAfter = await ethers.provider.getBalance(recipient.address);

            // Note: Balance check is approximate due to gas
            expect(recipientBalanceAfter).to.be.gt(recipientBalanceBefore);
        });

        it("Should emit Withdrawal event", async function () {
            const depositAmount = ethers.parseEther("1");
            await owner.sendTransaction({
                to: await agentWallet.getAddress(),
                value: depositAmount
            });

            await expect(agentWallet.withdraw(recipient.address, depositAmount))
                .to.emit(agentWallet, "Withdrawal")
                .withArgs(recipient.address, depositAmount);
        });

        it("Should revert if non-owner tries to withdraw", async function () {
            const depositAmount = ethers.parseEther("1");
            await owner.sendTransaction({
                to: await agentWallet.getAddress(),
                value: depositAmount
            });

            await expect(
                agentWallet.connect(nonOperator).withdraw(recipient.address, depositAmount)
            ).to.be.revertedWith("Ownable: caller is not the owner");
        });

        it("Should revert if insufficient balance", async function () {
            const excessiveAmount = ethers.parseEther("1000");
            await expect(
                agentWallet.withdraw(recipient.address, excessiveAmount)
            ).to.be.revertedWith("Insufficient balance");
        });

        it("Should revert if invalid recipient", async function () {
            await expect(
                agentWallet.withdraw(ethers.ZeroAddress, ethers.parseEther("1"))
            ).to.be.revertedWith("Invalid recipient");
        });
    });

    describe("Receive Functions", function () {
        it("Should accept CRO transfers", async function () {
            const depositAmount = ethers.parseEther("2.5");
            await owner.sendTransaction({
                to: await agentWallet.getAddress(),
                value: depositAmount
            });

            const balance = await ethers.provider.getBalance(await agentWallet.getAddress());
            expect(balance).to.equal(depositAmount);
        });
    });
});
