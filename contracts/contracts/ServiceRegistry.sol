// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ServiceRegistry
 * @dev Registry contract for managing services and their reputations
 */
contract ServiceRegistry {
    // State variables
    address public owner;
    uint256 public reputationRequired;
    uint256 public defaultStake;

    // Structs
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

    // Mappings
    mapping(bytes32 => Service) public services;
    mapping(address => bytes32[]) public serviceOwners;
    mapping(bytes32 => uint256) public serviceStakes;

    // Events
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

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    modifier onlyServiceOwner(bytes32 serviceId) {
        require(services[serviceId].serviceOwner == msg.sender, "Not service owner");
        _;
    }

    /**
     * @dev Constructor
     * @param _owner Address of the registry owner
     * @param _reputationRequired Minimum reputation score required
     * @param _defaultStake Default stake amount for registration
     */
    constructor(
        address _owner,
        uint256 _reputationRequired,
        uint256 _defaultStake
    ) {
        owner = _owner;
        reputationRequired = _reputationRequired;
        defaultStake = _defaultStake;
    }

    // ==================== External Functions ====================

    /**
     * @dev Registers a new service in the registry
     * @param name Service name
     * @param description Service description
     * @param endpoint Service endpoint URL
     * @param pricingModel Pricing model (pay-per-call, subscription, metered)
     * @param priceAmount Price amount
     * @param priceToken Price token symbol
     * @param mcpCompatible Whether service is MCP compatible
     * @return serviceId The unique service ID
     */
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

    /**
     * @dev Updates an existing service's details
     * @param serviceId The service ID to update
     * @param description New description
     * @param priceAmount New price amount
     * @param priceToken New price token
     */
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

    /**
     * @dev Deactivates a service
     * @param serviceId The service ID to deactivate
     */
    function deactivateService(bytes32 serviceId) external onlyServiceOwner(serviceId) {
        services[serviceId].active = false;
        emit ServiceDeactivated(serviceId);
    }

    /**
     * @dev Activates a service
     * @param serviceId The service ID to activate
     */
    function activateService(bytes32 serviceId) external onlyServiceOwner(serviceId) {
        services[serviceId].active = true;
    }

    /**
     * @dev Updates a service's reputation score
     * @param serviceId The service ID to update
     * @param scoreChange Amount to change reputation (positive or negative)
     */
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

    /**
     * @dev Increments the call count for a service
     * @param serviceId The service ID to increment
     */
    function incrementCallCount(bytes32 serviceId) external {
        // This could be called by PaymentRouter or other authorized contracts
        require(services[serviceId].active, "Service is not active");
        services[serviceId].totalCalls++;
    }

    /**
     * @dev Deposits additional stake for a service
     * @param serviceId The service ID to deposit stake for
     */
    function depositStake(bytes32 serviceId) external payable {
        require(services[serviceId].serviceOwner == msg.sender, "Not service owner");
        require(msg.value > 0, "Must deposit positive amount");

        serviceStakes[serviceId] += msg.value;
        emit StakeDeposited(serviceId, msg.value);
    }

    /**
     * @dev Withdraws stake from a service
     * @param serviceId The service ID to withdraw stake from
     * @param amount Amount to withdraw
     */
    function withdrawStake(bytes32 serviceId, uint256 amount) external onlyServiceOwner(serviceId) {
        require(serviceStakes[serviceId] >= amount, "Insufficient stake");
        require(services[serviceId].active, "Cannot withdraw from inactive service");

        serviceStakes[serviceId] -= amount;
        payable(msg.sender).transfer(amount);

        emit StakeWithdrawn(serviceId, amount);
    }

    // ==================== View Functions ====================

    /**
     * @dev Gets the stake amount for a service
     * @param serviceId The service ID
     * @return The staked amount
     */
    function getStake(bytes32 serviceId) external view returns (uint256) {
        return serviceStakes[serviceId];
    }

    /**
     * @dev Gets complete service details
     * @param serviceId The service ID
     * @return name Service name
     * @return description Service description
     * @return endpoint Service endpoint
     * @return pricingModel Pricing model
     * @return priceAmount Price amount
     * @return priceToken Price token
     * @return mcpCompatible MCP compatibility
     * @return reputationScore Reputation score
     * @return totalCalls Total call count
     * @return serviceOwner Service owner address
     * @return registrationTime Registration timestamp
     * @return active Active status
     */
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

    /**
     * @dev Gets all service IDs owned by an address
     * @param owner The owner address
     * @return Array of service IDs
     */
    function getServiceIdsByOwner(address owner) external view returns (bytes32[] memory) {
        return serviceOwners[owner];
    }
}