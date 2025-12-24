// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title ServiceRegistry
 * @dev Decentralized service registry for AI agent services
 * Allows service providers to register, update, and manage their services
 * Supports reputation tracking and pricing information
 */
contract ServiceRegistry is Ownable, ReentrancyGuard {
    // Events
    event ServiceRegistered(
        bytes32 indexed serviceId,
        address indexed owner,
        string name,
        string serviceUrl,
        uint256 pricePerCall,
        uint256 timestamp
    );
    event ServiceUpdated(
        bytes32 indexed serviceId,
        string newServiceUrl,
        uint256 newPrice,
        uint256 timestamp
    );
    event ServiceDeactivated(bytes32 indexed serviceId, uint256 timestamp);
    event ReputationUpdated(
        bytes32 indexed serviceId,
        uint256 newRating,
        uint256 totalCalls
    );
    event PricingModelUpdated(
        bytes32 indexed serviceId,
        PricingModel newModel
    );
    event SubscriptionCreated(
        bytes32 indexed serviceId,
        address indexed subscriber,
        uint256 expiresAt
    );
    event SubscriptionRenewed(
        bytes32 indexed serviceId,
        address indexed subscriber,
        uint256 newExpiresAt
    );

    enum PricingModel {
        METERED,    // Pay per call
        SUBSCRIPTION // Flat rate subscription
    }

    struct Service {
        bytes32 id;
        address owner;
        string name;
        string serviceUrl;
        uint256 pricePerCall;
        uint256 reputation; // 0-1000 scale (1000 = 5.0 stars)
        uint256 totalCalls;
        bool isActive;
        PricingModel pricingModel;
        uint256 subscriptionPrice; // Price per subscription period
        uint256 subscriptionPeriod; // Duration in days
    }

    struct Subscription {
        address subscriber;
        bytes32 serviceId;
        uint256 expiresAt;
        bool isActive;
    }

    // Service storage
    mapping(bytes32 => Service) public services;
    mapping(bytes32 => mapping(address => Subscription)) public subscriptions;
    mapping(address => bytes32[]) public userServices; // Services owned by user
    mapping(address => bytes32[]) public userSubscriptions; // Services subscribed by user

    uint256 public serviceCount;

    // Constants
    uint256 public constant MAX_REPUTATION = 1000; // 5.0 stars * 200
    uint256 public constant MIN_REPUTATION = 0;

    // Modifiers
    modifier onlyServiceOwner(bytes32 _serviceId) {
        require(services[_serviceId].owner == msg.sender, "Not service owner");
        _;
    }

    modifier serviceExists(bytes32 _serviceId) {
        require(services[_serviceId].owner != address(0), "Service does not exist");
        _;
    }

    modifier serviceActive(bytes32 _serviceId) {
        require(services[_serviceId].isActive, "Service is not active");
        _;
    }

    /**
     * @dev Register a new service
     */
    function registerService(
        string calldata _name,
        string calldata _serviceUrl,
        uint256 _pricePerCall,
        PricingModel _pricingModel,
        uint256 _subscriptionPrice,
        uint256 _subscriptionPeriod
    ) external nonReentrant returns (bytes32) {
        require(bytes(_name).length > 0, "Name required");
        require(bytes(_serviceUrl).length > 0, "URL required");
        require(_pricePerCall >= 0, "Invalid price");

        bytes32 serviceId = keccak256(abi.encodePacked(_name, msg.sender, block.timestamp));

        Service storage newService = services[serviceId];
        newService.id = serviceId;
        newService.owner = msg.sender;
        newService.name = _name;
        newService.serviceUrl = _serviceUrl;
        newService.pricePerCall = _pricePerCall;
        newService.reputation = 500; // Start with 2.5 stars
        newService.totalCalls = 0;
        newService.isActive = true;
        newService.pricingModel = _pricingModel;
        newService.subscriptionPrice = _subscriptionPrice;
        newService.subscriptionPeriod = _subscriptionPeriod;

        userServices[msg.sender].push(serviceId);
        serviceCount++;

        emit ServiceRegistered(
            serviceId,
            msg.sender,
            _name,
            _serviceUrl,
            _pricePerCall,
            block.timestamp
        );

        return serviceId;
    }

    /**
     * @dev Update service information
     */
    function updateService(
        bytes32 _serviceId,
        string calldata _newServiceUrl,
        uint256 _newPrice
    ) external onlyServiceOwner(_serviceId) serviceExists(_serviceId) {
        services[_serviceId].serviceUrl = _newServiceUrl;
        services[_serviceId].pricePerCall = _newPrice;

        emit ServiceUpdated(_serviceId, _newServiceUrl, _newPrice, block.timestamp);
    }

    /**
     * @dev Deactivate a service
     */
    function deactivateService(bytes32 _serviceId) external onlyServiceOwner(_serviceId) serviceExists(_serviceId) {
        services[_serviceId].isActive = false;
        emit ServiceDeactivated(_serviceId, block.timestamp);
    }

    /**
     * @dev Reactivate a service
     */
    function reactivateService(bytes32 _serviceId) external onlyServiceOwner(_serviceId) serviceExists(_serviceId) {
        services[_serviceId].isActive = true;
        emit ServiceDeactivated(_serviceId, block.timestamp);
    }

    /**
     * @dev Update pricing model
     */
    function updatePricingModel(
        bytes32 _serviceId,
        PricingModel _newModel
    ) external onlyServiceOwner(_serviceId) serviceExists(_serviceId) {
        services[_serviceId].pricingModel = _newModel;
        emit PricingModelUpdated(_serviceId, _newModel);
    }

    /**
     * @dev Update service reputation (called by payment/execution contract)
     * Only callable by authorized contracts (in production, would use access control)
     */
    function updateReputation(bytes32 _serviceId, uint256 _rating) external serviceExists(_serviceId) {
        // In production, restrict to authorized payment contracts
        require(_rating <= 500, "Rating must be <= 500 (5.0 stars)");

        Service storage service = services[_serviceId];
        uint256 oldReputation = service.reputation;
        uint256 totalCalls = service.totalCalls;

        // Moving average: ((current * total) + new) / (total + 1)
        service.reputation = ((oldReputation * totalCalls) + _rating) / (totalCalls + 1);
        service.totalCalls++;

        emit ReputationUpdated(_serviceId, service.reputation, service.totalCalls);
    }

    /**
     * @dev Create a subscription for a service
     * @param _serviceId Service to subscribe to
     */
    function createSubscription(bytes32 _serviceId) external payable serviceExists(_serviceId) serviceActive(_serviceId) {
        Service storage service = services[_serviceId];
        require(service.pricingModel == PricingModel.SUBSCRIPTION, "Service is not subscription-based");
        require(msg.value >= service.subscriptionPrice, "Insufficient payment");

        uint256 expiresAt = block.timestamp + (service.subscriptionPeriod * 1 days);

        Subscription storage sub = subscriptions[_serviceId][msg.sender];
        sub.subscriber = msg.sender;
        sub.serviceId = _serviceId;
        sub.expiresAt = expiresAt;
        sub.isActive = true;

        // Track user subscription
        bool alreadySubscribed = false;
        for (uint i = 0; i < userSubscriptions[msg.sender].length; i++) {
            if (userSubscriptions[msg.sender][i] == _serviceId) {
                alreadySubscribed = true;
                break;
            }
        }
        if (!alreadySubscribed) {
            userSubscriptions[msg.sender].push(_serviceId);
        }

        emit SubscriptionCreated(_serviceId, msg.sender, expiresAt);
    }

    /**
     * @dev Renew an existing subscription
     */
    function renewSubscription(bytes32 _serviceId) external payable serviceExists(_serviceId) {
        Service storage service = services[_serviceId];
        require(service.pricingModel == PricingModel.SUBSCRIPTION, "Service is not subscription-based");
        require(msg.value >= service.subscriptionPrice, "Insufficient payment");

        Subscription storage sub = subscriptions[_serviceId][msg.sender];
        require(sub.isActive, "No active subscription");

        // Extend from current expiration or from now if expired
        uint256 newExpiry = block.timestamp + (service.subscriptionPeriod * 1 days);
        if (sub.expiresAt > block.timestamp) {
            newExpiry = sub.expiresAt + (service.subscriptionPeriod * 1 days);
        }

        sub.expiresAt = newExpiry;
        sub.isActive = true;

        emit SubscriptionRenewed(_serviceId, msg.sender, newExpiry);
    }

    /**
     * @dev Check if a subscription is active
     */
    function isSubscribed(bytes32 _serviceId, address _subscriber) external view returns (bool) {
        Subscription storage sub = subscriptions[_serviceId][_subscriber];
        return sub.isActive && sub.expiresAt > block.timestamp;
    }

    /**
     * @dev Get service details
     */
    function getService(bytes32 _serviceId) external view returns (Service memory) {
        return services[_serviceId];
    }

    /**
     * @dev Get services owned by an address
     */
    function getServicesByOwner(address _owner) external view returns (bytes32[] memory) {
        return userServices[_owner];
    }

    /**
     * @dev Get services subscribed by an address
     */
    function getSubscriptionsByUser(address _user) external view returns (bytes32[] memory) {
        return userSubscriptions[_user];
    }

    /**
     * @dev Get subscription details
     */
    function getSubscription(bytes32 _serviceId, address _subscriber) external view returns (Subscription memory) {
        return subscriptions[_serviceId][_subscriber];
    }

    /**
     * @dev Get total service count
     */
    function getTotalServices() external view returns (uint256) {
        return serviceCount;
    }

    /**
     * @dev Calculate service price based on pricing model
     */
    function calculateServicePrice(bytes32 _serviceId, bool _isSubscribed) external view returns (uint256) {
        Service memory service = services[_serviceId];

        if (service.pricingModel == PricingModel.SUBSCRIPTION) {
            if (_isSubscribed) {
                return 0; // Free for subscribers
            }
            return service.subscriptionPrice;
        }

        return service.pricePerCall;
    }
}
