// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ServiceRegistry
 * @dev Registry contract for managing services and their reputations
 */
contract ServiceRegistry {
    address public owner;
    uint256 public reputationRequired;
    uint256 public defaultStake;

    struct Service {
        string name;
        string description;
        string endpoint;
        string pricingModel; // "pay-per-call", "subscription", "metered"
        uint256 priceAmount;
        string priceToken;
        bool mcpCompatible;
        uint256 reputationScore;
        uint256 totalCalls;
        address serviceOwner;
        uint256 registrationTime;
        bool active;
    }

    mapping(bytes32 => Service) public services;
    mapping(address => bytes32[]) public serviceOwners;
    mapping(bytes32 => uint256) public serviceStakes;

    event ServiceRegistered(
        bytes32 indexed serviceId,
        string name,
        address indexed owner,
        uint256 stake
    );
    event ServiceUpdated(bytes32 indexed serviceId, string description);
    event ServiceDeactivated(bytes32 indexed serviceId);
    event ReputationUpdated(bytes32 indexed serviceId, uint256 newScore);
    event StakeDeposited(bytes32 indexed serviceId, uint256 amount);
    event StakeWithdrawn(bytes32 indexed serviceId, uint256 amount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    modifier onlyServiceOwner(bytes32 serviceId) {
        require(services[serviceId].serviceOwner == msg.sender, "Not service owner");
        _;
    }

    constructor(
        address _owner,
        uint256 _reputationRequired,
        uint256 _defaultStake
    ) {
        owner = _owner;
        reputationRequired = _reputationRequired;
        defaultStake = _defaultStake;
    }

    function registerService(
        string calldata name,
        string calldata description,
        string calldata endpoint,
        string calldata pricingModel,
        uint256 priceAmount,
        string calldata priceToken,
        bool mcpCompatible
    ) external payable returns (bytes32) {
        require(msg.value >= defaultStake, "Insufficient stake");
        require(bytes(name).length > 0, "Name cannot be empty");
        require(bytes(endpoint).length > 0, "Endpoint cannot be empty");

        bytes32 serviceId = keccak256(abi.encodePacked(endpoint, msg.sender));
        require(services[serviceId].serviceOwner == address(0), "Service already registered");

        services[serviceId] = Service({
            name: name,
            description: description,
            endpoint: endpoint,
            pricingModel: pricingModel,
            priceAmount: priceAmount,
            priceToken: priceToken,
            mcpCompatible: mcpCompatible,
            reputationScore: 50, // Starting reputation
            totalCalls: 0,
            serviceOwner: msg.sender,
            registrationTime: block.timestamp,
            active: true
        });

        serviceStakes[serviceId] = msg.value;
        serviceOwners[msg.sender].push(serviceId);

        emit ServiceRegistered(serviceId, name, msg.sender, msg.value);
        return serviceId;
    }

    function updateService(
        bytes32 serviceId,
        string calldata description,
        uint256 priceAmount,
        string calldata priceToken
    ) external onlyServiceOwner(serviceId) {
        Service storage service = services[serviceId];
        require(service.active, "Service is not active");

        service.description = description;
        service.priceAmount = priceAmount;
        service.priceToken = priceToken;

        emit ServiceUpdated(serviceId, description);
    }

    function deactivateService(bytes32 serviceId) external onlyServiceOwner(serviceId) {
        services[serviceId].active = false;
        emit ServiceDeactivated(serviceId);
    }

    function activateService(bytes32 serviceId) external onlyServiceOwner(serviceId) {
        services[serviceId].active = true;
    }

    function updateReputation(bytes32 serviceId, int256 scoreChange) external onlyOwner {
        Service storage service = services[serviceId];
        require(service.active, "Service is not active");

        // Update reputation (clamped between 0 and 100)
        if (scoreChange > 0) {
            service.reputationScore = uint256(int256(service.reputationScore) + scoreChange);
            if (service.reputationScore > 100) {
                service.reputationScore = 100;
            }
        } else {
            if (int256(service.reputationScore) + scoreChange < 0) {
                service.reputationScore = 0;
            } else {
                service.reputationScore = uint256(int256(service.reputationScore) + scoreChange);
            }
        }

        emit ReputationUpdated(serviceId, service.reputationScore);
    }

    function incrementCallCount(bytes32 serviceId) external {
        // This could be called by PaymentRouter or other authorized contracts
        require(services[serviceId].active, "Service is not active");
        services[serviceId].totalCalls++;
    }

    function getStake(bytes32 serviceId) external view returns (uint256) {
        return serviceStakes[serviceId];
    }

    function depositStake(bytes32 serviceId) external payable {
        require(services[serviceId].serviceOwner == msg.sender, "Not service owner");
        require(msg.value > 0, "Must deposit positive amount");

        serviceStakes[serviceId] += msg.value;
        emit StakeDeposited(serviceId, msg.value);
    }

    function withdrawStake(bytes32 serviceId, uint256 amount) external onlyServiceOwner(serviceId) {
        require(serviceStakes[serviceId] >= amount, "Insufficient stake");
        require(services[serviceId].active, "Cannot withdraw from inactive service");

        serviceStakes[serviceId] -= amount;
        payable(msg.sender).transfer(amount);

        emit StakeWithdrawn(serviceId, amount);
    }

    function getService(bytes32 serviceId) external view returns (
        string memory name,
        string memory description,
        string memory endpoint,
        string memory pricingModel,
        uint256 priceAmount,
        string memory priceToken,
        bool mcpCompatible,
        uint256 reputationScore,
        uint256 totalCalls,
        address serviceOwner,
        uint256 registrationTime,
        bool active
    ) {
        Service storage service = services[serviceId];
        return (
            service.name,
            service.description,
            service.endpoint,
            service.pricingModel,
            service.priceAmount,
            service.priceToken,
            service.mcpCompatible,
            service.reputationScore,
            service.totalCalls,
            service.serviceOwner,
            service.registrationTime,
            service.active
        );
    }

    function getServiceIdsByOwner(address owner) external view returns (bytes32[] memory) {
        return serviceOwners[owner];
    }
}