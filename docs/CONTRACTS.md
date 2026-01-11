# Smart Contract Deployment

This directory contains the smart contract deployment infrastructure for the Paygent ecosystem.

## Overview

The deployment system provides:
- **ContractDeployer**: Core deployment and management functionality
- **DeploymentManager**: Complete ecosystem deployment orchestration
- **Solidity Contracts**: All required smart contracts
- **Configuration Management**: Environment-specific deployment configs

## Contracts

### Core Contracts

1. **AgentWallet.sol**
   - ERC-20 token for agent wallet functionality
   - Manages agent funds and permissions
   - Supports minting and burning by authorized agents

2. **PaymentRouter.sol**
   - Handles x402 payment routing and fee distribution
   - Manages payment execution and fee collection
   - Supports batch payments and agent permissions

3. **ServiceRegistry.sol**
   - Registry for MCP-compatible services
   - Manages service reputation and staking
   - Handles service discovery and verification

### Adapter Contracts

4. **VVSAdapter.sol**
   - Integration with VVS Finance DEX
   - Supports token swaps and liquidity operations
   - Provides price estimation and reserve queries

5. **MoonlanderAdapter.sol**
   - Integration with Moonlander perpetual trading
   - Manages position opening/closing and risk controls
   - Supports stop-loss and take-profit orders

6. **DelphiAdapter.sol**
   - Integration with Delphi prediction markets
   - Handles bet placement and winnings claims
   - Manages market outcomes and odds

## Deployment

### Prerequisites

- Python 3.11+
- Node.js with Hardhat
- Cronos Testnet RPC endpoint
- Deployer private key with sufficient funds

### Configuration

Create `.env` file with:
```bash
DEPLOYER_PRIVATE_KEY=your_private_key
OWNER_ADDRESS=your_owner_address
FEE_COLLECTOR_ADDRESS=fee_collector_address
```

### Deploy Commands

```bash
# Deploy full ecosystem
python scripts/deploy_contracts.py --config scripts/deployment_config.json

# Deploy specific contracts (via Hardhat)
cd contracts
npx hardhat run scripts/deploy.js --network cronosTestnet
```

### Contract Addresses

After deployment, contract addresses are saved to:
- `deployment/deployment.json` - Complete deployment summary
- `deployment/{ContractName}_address.txt` - Individual addresses

## Usage

### Basic Deployment

```python
from scripts.deploy_contracts import DeploymentManager

# Load configuration
config = {
    "rpc_url": "https://evm-t3.cronos.org",
    "private_key": "your_private_key",
    "owner_address": "your_address",
    # ... other config
}

# Deploy ecosystem
manager = DeploymentManager(config)
result = manager.deploy_full_ecosystem()

# Save artifacts
manager.save_deployment_artifacts()
```

### Individual Contract Deployment

```python
from scripts.deploy_contracts import ContractDeployer

deployer = ContractDeployer(
    rpc_url="https://evm-t3.cronos.org",
    private_key="your_private_key"
)

# Deploy AgentWallet
wallet_address, wallet_contract = deployer.deploy_agent_wallet(
    owner_address="owner_address",
    name="Paygent Agent Wallet",
    symbol="PAW"
)
```

## Contract Interactions

### AgentWallet
```solidity
// Mint tokens to address
walletContract.mint(recipient, amount);

// Check balance
uint256 balance = walletContract.balanceOf(address);
```

### PaymentRouter
```solidity
// Execute payment
routerContract.executePayment(recipient, amount);

// Get payment details
(uint256 fee, uint256 net) = routerContract.getPaymentDetails(amount);
```

### ServiceRegistry
```solidity
// Register service
bytes32 serviceId = registryContract.registerService(
    "Service Name",
    "Service Description",
    "https://api.example.com",
    "pay-per-call",
    100,
    "USDC",
    true
);

// Update reputation
registryContract.updateReputation(serviceId, 5);
```

## Security Considerations

- **Private Keys**: Never commit private keys to version control
- **Contract Verification**: Always verify contracts on Cronos Explorer
- **Testing**: Test deployments on testnet before mainnet
- **Access Control**: Use proper role-based access control
- **Audit**: Consider professional security audit for production

## Troubleshooting

### Common Issues

1. **Insufficient Gas**: Increase gas limit in deployment config
2. **Contract Verification Failures**: Check constructor arguments
3. **Network Timeouts**: Verify RPC endpoint connectivity
4. **Permission Errors**: Ensure deployer has sufficient permissions

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration

### Backend Integration

The deployment artifacts can be integrated with the backend:
```python
# Load deployment addresses
with open("deployment/deployment.json", "r") as f:
    deployment = json.load(f)

# Initialize contracts
wallet_address = deployment["deployments"]["AgentWallet"]["address"]
```

### Frontend Integration

Frontend applications can use the deployment addresses:
```javascript
// Load contract addresses
const deployment = require("./deployment/deployment.json");

// Initialize web3 contracts
const walletContract = new web3.eth.Contract(abi, deployment.deployments.AgentWallet.address);
```

## Updates and Maintenance

### Contract Upgrades

1. Update Solidity source files
2. Re-deploy with new addresses
3. Update configuration files
4. Update frontend/backend integrations

### Configuration Updates

Update `deployment_config.json` for different environments:
- Testnet vs Mainnet
- Different fee structures
- Alternative contract addresses

## Monitoring

### Deployment Status

Check deployment status:
```bash
# View deployment artifacts
ls deployment/

# Check contract verification
npx hardhat verify --network cronosTestnet <contract_address>
```

### Contract Health

Monitor contract health:
- Transaction success rates
- Gas usage patterns
- Balance monitoring
- Event emission verification

## Support

For issues with contract deployment or integration:
1. Check the troubleshooting section
2. Verify configuration files
3. Test on testnet first
4. Review contract verification status