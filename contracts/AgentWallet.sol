// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title AgentWallet
 * @dev ERC-20 token contract for agent wallet functionality
 * Manages agent funds and provides basic token operations
 */
contract AgentWallet {
    string public name;
    string public symbol;
    uint8 public decimals;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    address public owner;
    mapping(address => bool) public isAgent;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event AgentAdded(address indexed agent);
    event AgentRemoved(address indexed agent);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    modifier onlyAgent() {
        require(isAgent[msg.sender], "Only registered agents can call this function");
        _;
    }

    constructor(
        address _owner,
        string memory _name,
        string memory _symbol
    ) {
        owner = _owner;
        name = _name;
        symbol = _symbol;
        decimals = 18;
        totalSupply = 0;

        // Grant owner agent permissions
        isAgent[_owner] = true;
        emit AgentAdded(_owner);
    }

    function addAgent(address agent) external onlyOwner {
        require(!isAgent[agent], "Agent already exists");
        isAgent[agent] = true;
        emit AgentAdded(agent);
    }

    function removeAgent(address agent) external onlyOwner {
        require(isAgent[agent], "Agent does not exist");
        isAgent[agent] = false;
        emit AgentRemoved(agent);
    }

    function mint(address to, uint256 amount) external onlyAgent {
        balanceOf[to] += amount;
        totalSupply += amount;
        emit Transfer(address(0), to, amount);
    }

    function burn(uint256 amount) external {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        balanceOf[msg.sender] -= amount;
        totalSupply -= amount;
        emit Transfer(msg.sender, address(0), amount);
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");

        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        allowance[from][msg.sender] -= amount;
        emit Transfer(from, to, amount);
        return true;
    }
}