// SPDX-License-Identifier: MIT
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("ServiceRegistry", function () {
    let ServiceRegistry;
    let serviceRegistry;
    let owner;
    let serviceOwner;
    let nonOwner;
    let reputationRequired;
    let defaultStake;

    beforeEach(async function () {
        [owner, serviceOwner, nonOwner] = await ethers.getSigners();

        // Deploy ServiceRegistry
        ServiceRegistry = await ethers.getContractFactory("ServiceRegistry");
        reputationRequired = 50;
        defaultStake = ethers.parseEther("10");
        serviceRegistry = await ServiceRegistry.deploy(
            owner.address,
            reputationRequired,
            defaultStake
        );
        await serviceRegistry.waitForDeployment();
    });

    describe("Deployment", function () {
        it("Should set the correct owner", async function () {
            expect(await serviceRegistry.owner()).to.equal(owner.address);
        });

        it("Should set the correct reputation required", async function () {
            expect(await serviceRegistry.reputationRequired()).to.equal(reputationRequired);
        });

        it("Should set the correct default stake", async function () {
            expect(await serviceRegistry.defaultStake()).to.equal(defaultStake);
        });
    });

    describe("Service Registration", function () {
        const serviceName = "Test Service";
        const serviceDesc = "A test service";
        const serviceEndpoint = "https://api.test.com";
        const pricingModel = "pay-per-call";
        const priceAmount = ethers.parseEther("0.1");
        const priceToken = "USDC";
        const mcpCompatible = true;

        it("Should register a service correctly", async function () {
            const tx = await serviceRegistry.connect(serviceOwner).registerService(
                serviceName,
                serviceDesc,
                serviceEndpoint,
                pricingModel,
                priceAmount,
                priceToken,
                mcpCompatible,
                { value: defaultStake }
            );

            const serviceId = keccak256(ethers.AbiCoder.encode(
                ["string", "address"],
                [serviceEndpoint, serviceOwner.address]
            ));

            const service = await serviceRegistry.services(serviceId);
            expect(service.name).to.equal(serviceName);
            expect(service.description).to.equal(serviceDesc);
            expect(service.endpoint).to.equal(serviceEndpoint);
            expect(service.pricingModel).to.equal(pricingModel);
            expect(service.priceAmount).to.equal(priceAmount);
            expect(service.priceToken).to.equal(priceToken);
            expect(service.mcpCompatible).to.equal(mcpCompatible);
            expect(service.reputationScore).to.equal(50); // Starting reputation
            expect(service.totalCalls).to.equal(0);
            expect(service.serviceOwner).to.equal(serviceOwner.address);
            expect(service.active).to.be.true;
        });

        it("Should emit ServiceRegistered event", async function () {
            const serviceId = keccak256(ethers.AbiCoder.encode(
                ["string", "address"],
                [serviceEndpoint, serviceOwner.address]
            ));

            await expect(
                serviceRegistry.connect(serviceOwner).registerService(
                    serviceName,
                    serviceDesc,
                    serviceEndpoint,
                    pricingModel,
                    priceAmount,
                    priceToken,
                    mcpCompatible,
                    { value: defaultStake }
                )
            )
            .to.emit(serviceRegistry, "ServiceRegistered")
            .withArgs(serviceId, serviceName, serviceOwner.address, defaultStake);
        });

        it("Should revert with insufficient stake", async function () {
            await expect(
                serviceRegistry.connect(serviceOwner).registerService(
                    serviceName,
                    serviceDesc,
                    serviceEndpoint,
                    pricingModel,
                    priceAmount,
                    priceToken,
                    mcpCompatible,
                    { value: ethers.parseEther("5") } // Less than default
                )
            ).to.be.revertedWith("Insufficient stake");
        });

        it("Should revert with empty name", async function () {
            await expect(
                serviceRegistry.connect(serviceOwner).registerService(
                    "",
                    serviceDesc,
                    serviceEndpoint,
                    pricingModel,
                    priceAmount,
                    priceToken,
                    mcpCompatible,
                    { value: defaultStake }
                )
            ).to.be.revertedWith("Name cannot be empty");
        });

        it("Should revert with empty endpoint", async function () {
            await expect(
                serviceRegistry.connect(serviceOwner).registerService(
                    serviceName,
                    serviceDesc,
                    "",
                    pricingModel,
                    priceAmount,
                    priceToken,
                    mcpCompatible,
                    { value: defaultStake }
                )
            ).to.be.revertedWith("Endpoint cannot be empty");
        });

        it("Should revert when service already exists", async function () {
            await serviceRegistry.connect(serviceOwner).registerService(
                serviceName,
                serviceDesc,
                serviceEndpoint,
                pricingModel,
                priceAmount,
                priceToken,
                mcpCompatible,
                { value: defaultStake }
            );

            await expect(
                serviceRegistry.connect(serviceOwner).registerService(
                    serviceName,
                    serviceDesc,
                    serviceEndpoint,
                    pricingModel,
                    priceAmount,
                    priceToken,
                    mcpCompatible,
                    { value: defaultStake }
                )
            ).to.be.revertedWith("Service already registered");
        });
    });

    describe("Service Update", function () {
        let serviceId;

        beforeEach(async function () {
            const serviceName = "Test Service";
            const serviceDesc = "A test service";
            const serviceEndpoint = "https://api.test.com";
            const pricingModel = "pay-per-call";
            const priceAmount = ethers.parseEther("0.1");
            const priceToken = "USDC";
            const mcpCompatible = true;

            await serviceRegistry.connect(serviceOwner).registerService(
                serviceName,
                serviceDesc,
                serviceEndpoint,
                pricingModel,
                priceAmount,
                priceToken,
                mcpCompatible,
                { value: defaultStake }
            );

            serviceId = keccak256(ethers.AbiCoder.encode(
                ["string", "address"],
                [serviceEndpoint, serviceOwner.address]
            ));
        });

        it("Should update service correctly", async function () {
            const newDesc = "Updated description";
            const newPrice = ethers.parseEther("0.2");
            const newToken = "USDT";

            await serviceRegistry.connect(serviceOwner).updateService(
                serviceId,
                newDesc,
                newPrice,
                newToken
            );

            const service = await serviceRegistry.services(serviceId);
            expect(service.description).to.equal(newDesc);
            expect(service.priceAmount).to.equal(newPrice);
            expect(service.priceToken).to.equal(newToken);
        });

        it("Should emit ServiceUpdated event", async function () {
            const newDesc = "Updated description";

            await expect(
                serviceRegistry.connect(serviceOwner).updateService(
                    serviceId,
                    newDesc,
                    ethers.parseEther("0.2"),
                    "USDT"
                )
            )
            .to.emit(serviceRegistry, "ServiceUpdated")
            .withArgs(serviceId, newDesc);
        });

        it("Should revert when non-owner tries to update", async function () {
            await expect(
                serviceRegistry.connect(nonOwner).updateService(
                    serviceId,
                    "New desc",
                    ethers.parseEther("0.2"),
                    "USDT"
                )
            ).to.be.revertedWith("Not service owner");
        });

        it("Should revert when service is inactive", async function () {
            await serviceRegistry.connect(serviceOwner).deactivateService(serviceId);

            await expect(
                serviceRegistry.connect(serviceOwner).updateService(
                    serviceId,
                    "New desc",
                    ethers.parseEther("0.2"),
                    "USDT"
                )
            ).to.be.revertedWith("Service is not active");
        });
    });

    describe("Service Activation/Deactivation", function () {
        let serviceId;

        beforeEach(async function () {
            const serviceName = "Test Service";
            const serviceDesc = "A test service";
            const serviceEndpoint = "https://api.test.com";
            const pricingModel = "pay-per-call";
            const priceAmount = ethers.parseEther("0.1");
            const priceToken = "USDC";
            const mcpCompatible = true;

            await serviceRegistry.connect(serviceOwner).registerService(
                serviceName,
                serviceDesc,
                serviceEndpoint,
                pricingModel,
                priceAmount,
                priceToken,
                mcpCompatible,
                { value: defaultStake }
            );

            serviceId = keccak256(ethers.AbiCoder.encode(
                ["string", "address"],
                [serviceEndpoint, serviceOwner.address]
            ));
        });

        it("Should deactivate service", async function () {
            await serviceRegistry.connect(serviceOwner).deactivateService(serviceId);
            const service = await serviceRegistry.services(serviceId);
            expect(service.active).to.be.false;
        });

        it("Should emit ServiceDeactivated event", async function () {
            await expect(
                serviceRegistry.connect(serviceOwner).deactivateService(serviceId)
            )
            .to.emit(serviceRegistry, "ServiceDeactivated")
            .withArgs(serviceId);
        });

        it("Should reactivate service", async function () {
            await serviceRegistry.connect(serviceOwner).deactivateService(serviceId);
            await serviceRegistry.connect(serviceOwner).activateService(serviceId);
            const service = await serviceRegistry.services(serviceId);
            expect(service.active).to.be.true;
        });

        it("Should revert when non-owner deactivates", async function () {
            await expect(
                serviceRegistry.connect(nonOwner).deactivateService(serviceId)
            ).to.be.revertedWith("Not service owner");
        });
    });

    describe("Reputation Update", function () {
        let serviceId;

        beforeEach(async function () {
            const serviceName = "Test Service";
            const serviceDesc = "A test service";
            const serviceEndpoint = "https://api.test.com";
            const pricingModel = "pay-per-call";
            const priceAmount = ethers.parseEther("0.1");
            const priceToken = "USDC";
            const mcpCompatible = true;

            await serviceRegistry.connect(serviceOwner).registerService(
                serviceName,
                serviceDesc,
                serviceEndpoint,
                pricingModel,
                priceAmount,
                priceToken,
                mcpCompatible,
                { value: defaultStake }
            );

            serviceId = keccak256(ethers.AbiCoder.encode(
                ["string", "address"],
                [serviceEndpoint, serviceOwner.address]
            ));
        });

        it("Should increase reputation", async function () {
            await serviceRegistry.updateReputation(serviceId, 10);
            const service = await serviceRegistry.services(serviceId);
            expect(service.reputationScore).to.equal(60); // 50 + 10
        });

        it("Should decrease reputation", async function () {
            await serviceRegistry.updateReputation(serviceId, -10);
            const service = await serviceRegistry.services(serviceId);
            expect(service.reputationScore).to.equal(40); // 50 - 10
        });

        it("Should cap reputation at 100", async function () {
            await serviceRegistry.updateReputation(serviceId, 100);
            const service = await serviceRegistry.services(serviceId);
            expect(service.reputationScore).to.equal(100);
        });

        it("Should cap reputation at 0", async function () {
            await serviceRegistry.updateReputation(serviceId, -100);
            const service = await serviceRegistry.services(serviceId);
            expect(service.reputationScore).to.equal(0);
        });

        it("Should emit ReputationUpdated event", async function () {
            await expect(
                serviceRegistry.updateReputation(serviceId, 10)
            )
            .to.emit(serviceRegistry, "ReputationUpdated")
            .withArgs(serviceId, 60);
        });

        it("Should revert when non-owner updates reputation", async function () {
            await expect(
                serviceRegistry.connect(nonOwner).updateReputation(serviceId, 10)
            ).to.be.revertedWith("Only owner can call this function");
        });

        it("Should revert when service is inactive", async function () {
            await serviceRegistry.connect(serviceOwner).deactivateService(serviceId);

            await expect(
                serviceRegistry.updateReputation(serviceId, 10)
            ).to.be.revertedWith("Service is not active");
        });
    });

    describe("Stake Management", function () {
        let serviceId;

        beforeEach(async function () {
            const serviceName = "Test Service";
            const serviceDesc = "A test service";
            const serviceEndpoint = "https://api.test.com";
            const pricingModel = "pay-per-call";
            const priceAmount = ethers.parseEther("0.1");
            const priceToken = "USDC";
            const mcpCompatible = true;

            await serviceRegistry.connect(serviceOwner).registerService(
                serviceName,
                serviceDesc,
                serviceEndpoint,
                pricingModel,
                priceAmount,
                priceToken,
                mcpCompatible,
                { value: defaultStake }
            );

            serviceId = keccak256(ethers.AbiCoder.encode(
                ["string", "address"],
                [serviceEndpoint, serviceOwner.address]
            ));
        });

        it("Should deposit additional stake", async function () {
            const additionalStake = ethers.parseEther("5");
            await serviceRegistry.connect(serviceOwner).depositStake(serviceId, { value: additionalStake });

            const stake = await serviceRegistry.getStake(serviceId);
            expect(stake).to.equal(defaultStake + additionalStake);
        });

        it("Should emit StakeDeposited event", async function () {
            const additionalStake = ethers.parseEther("5");

            await expect(
                serviceRegistry.connect(serviceOwner).depositStake(serviceId, { value: additionalStake })
            )
            .to.emit(serviceRegistry, "StakeDeposited")
            .withArgs(serviceId, additionalStake);
        });

        it("Should withdraw stake", async function () {
            const withdrawAmount = ethers.parseEther("5");
            const ownerBalanceBefore = await ethers.provider.getBalance(serviceOwner.address);

            await serviceRegistry.connect(serviceOwner).withdrawStake(serviceId, withdrawAmount);

            const stake = await serviceRegistry.getStake(serviceId);
            expect(stake).to.equal(defaultStake - withdrawAmount);
        });

        it("Should emit StakeWithdrawn event", async function () {
            const withdrawAmount = ethers.parseEther("5");

            await expect(
                serviceRegistry.connect(serviceOwner).withdrawStake(serviceId, withdrawAmount)
            )
            .to.emit(serviceRegistry, "StakeWithdrawn")
            .withArgs(serviceId, withdrawAmount);
        });

        it("Should revert when withdrawing more than stake", async function () {
            await expect(
                serviceRegistry.connect(serviceOwner).withdrawStake(serviceId, ethers.parseEther("20"))
            ).to.be.revertedWith("Insufficient stake");
        });

        it("Should revert when withdrawing from inactive service", async function () {
            await serviceRegistry.connect(serviceOwner).deactivateService(serviceId);

            await expect(
                serviceRegistry.connect(serviceOwner).withdrawStake(serviceId, ethers.parseEther("5"))
            ).to.be.revertedWith("Cannot withdraw from inactive service");
        });

        it("Should revert when non-owner withdraws", async function () {
            await expect(
                serviceRegistry.connect(nonOwner).withdrawStake(serviceId, ethers.parseEther("5"))
            ).to.be.revertedWith("Not service owner");
        });
    });

    describe("View Functions", function () {
        let serviceId;

        beforeEach(async function () {
            const serviceName = "Test Service";
            const serviceDesc = "A test service";
            const serviceEndpoint = "https://api.test.com";
            const pricingModel = "pay-per-call";
            const priceAmount = ethers.parseEther("0.1");
            const priceToken = "USDC";
            const mcpCompatible = true;

            await serviceRegistry.connect(serviceOwner).registerService(
                serviceName,
                serviceDesc,
                serviceEndpoint,
                pricingModel,
                priceAmount,
                priceToken,
                mcpCompatible,
                { value: defaultStake }
            );

            serviceId = keccak256(ethers.AbiCoder.encode(
                ["string", "address"],
                [serviceEndpoint, serviceOwner.address]
            ));
        });

        it("Should return correct service data", async function () {
            const [
                name, description, endpoint, pricingModel, priceAmount, priceToken,
                mcpCompatible, reputationScore, totalCalls, serviceOwnerAddr, registrationTime, active
            ] = await serviceRegistry.getService(serviceId);

            expect(name).to.equal("Test Service");
            expect(description).to.equal("A test service");
            expect(endpoint).to.equal("https://api.test.com");
            expect(pricingModel).to.equal("pay-per-call");
            expect(priceAmount).to.equal(ethers.parseEther("0.1"));
            expect(priceToken).to.equal("USDC");
            expect(mcpCompatible).to.be.true;
            expect(reputationScore).to.equal(50);
            expect(totalCalls).to.equal(0);
            expect(serviceOwnerAddr).to.equal(serviceOwner.address);
            expect(active).to.be.true;
        });

        it("Should return correct stake", async function () {
            const stake = await serviceRegistry.getStake(serviceId);
            expect(stake).to.equal(defaultStake);
        });

        it("Should return service IDs by owner", async function () {
            const ids = await serviceRegistry.getServiceIdsByOwner(serviceOwner.address);
            expect(ids.length).to.equal(1);
            expect(ids[0]).to.equal(serviceId);
        });
    });

    describe("Call Count", function () {
        let serviceId;

        beforeEach(async function () {
            const serviceName = "Test Service";
            const serviceDesc = "A test service";
            const serviceEndpoint = "https://api.test.com";
            const pricingModel = "pay-per-call";
            const priceAmount = ethers.parseEther("0.1");
            const priceToken = "USDC";
            const mcpCompatible = true;

            await serviceRegistry.connect(serviceOwner).registerService(
                serviceName,
                serviceDesc,
                serviceEndpoint,
                pricingModel,
                priceAmount,
                priceToken,
                mcpCompatible,
                { value: defaultStake }
            );

            serviceId = keccak256(ethers.AbiCoder.encode(
                ["string", "address"],
                [serviceEndpoint, serviceOwner.address]
            ));
        });

        it("Should increment call count", async function () {
            await serviceRegistry.incrementCallCount(serviceId);
            const service = await serviceRegistry.services(serviceId);
            expect(service.totalCalls).to.equal(1);
        });

        it("Should increment multiple times", async function () {
            await serviceRegistry.incrementCallCount(serviceId);
            await serviceRegistry.incrementCallCount(serviceId);
            await serviceRegistry.incrementCallCount(serviceId);
            const service = await serviceRegistry.services(serviceId);
            expect(service.totalCalls).to.equal(3);
        });

        it("Should revert when service is inactive", async function () {
            await serviceRegistry.connect(serviceOwner).deactivateService(serviceId);

            await expect(
                serviceRegistry.incrementCallCount(serviceId)
            ).to.be.revertedWith("Service is not active");
        });
    });
});

// Helper function to compute keccak256 hash
function keccak256(data) {
    return ethers.keccak256(data);
}
