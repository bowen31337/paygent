# Contract Verification Guide

This guide explains how to verify Paygent smart contracts on Cronoscan after deployment.

## Overview

Contract verification allows you to verify the source code of deployed smart contracts on Cronoscan, making them transparent and auditable. This is essential for:
- Building trust with users
- Enabling code review and auditing
- Improving contract discoverability
- Meeting compliance requirements

## Prerequisites

### 1. Environment Setup

Set up the required environment variables in your `.env` file:

```bash
# Cronoscan API Key (required for verification)
CRONOSCAN_API_KEY=your_cronoscan_api_key_here

# Network configuration
CRONOS_TESTNET_RPC=https://evm-t3.cronos.org
CRONOS_MAINNET_RPC=https://evm.cronos.org

# Private key for deployment (if needed)
PRIVATE_KEY=your_private_key_here

# Optional: Gas configuration
GAS_PRICE=50000000000
```

### 2. Get Cronoscan API Key

1. Visit [Cronoscan](https://cronoscan.com/)
2. Create an account or log in
3. Go to "API-KEYs" section in your profile
4. Create a new API key
5. Add the key to your `.env` file

## Deployment and Verification Process

### Step 1: Deploy Contracts

First, deploy your contracts to the target network:

```bash
# Deploy to Cronos Testnet
pnpm exec hardhat run scripts/deploy.js --network cronosTestnet

# Deploy to Cronos Mainnet
pnpm exec hardhat run scripts/deploy.js --network cronosMainnet
```

### Step 2: Verify Contracts

After deployment, verify the contracts using our automated script:

```bash
# Verify on Cronos Testnet
pnpm exec hardhat run scripts/verify-contracts.js --network cronosTestnet

# Verify on Cronos Mainnet
pnpm exec hardhat run scripts/verify-contracts.js --network cronosMainnet
```

### Step 3: Manual Verification (Alternative)

If automated verification fails, you can verify contracts manually:

```bash
# Verify AgentWallet contract
npx hardhat verify --network cronosTestnet <agent_wallet_address> --contract "contracts/AgentWallet.sol:AgentWallet" "0x0000000000000000000000000000000000000000"

# Verify PaymentRouter contract
npx hardhat verify --network cronosTestnet <payment_router_address> --contract "contracts/PaymentRouter.sol:PaymentRouter" "0x0000000000000000000000000000000000000000"

# Verify ServiceRegistry contract
npx hardhat verify --network cronosTestnet <service_registry_address> --contract "contracts/ServiceRegistry.sol:ServiceRegistry"

# Verify MockToken contract
npx hardhat verify --network cronosTestnet <mock_token_address> --contract "contracts/MockToken.sol:MockToken" "Paygent Token" "PAYG" 18 "1000000000000000000000000"
```

## Supported Contracts

The verification script supports these contracts:

1. **AgentWallet.sol**
   - Manages agent wallet operations
   - Constructor arguments: [ownerAddress]
   - Purpose: Non-custodial wallet management for AI agents

2. **PaymentRouter.sol**
   - Routes and executes payments
   - Constructor arguments: [feeCollectorAddress]
   - Purpose: Payment execution with fee management

3. **ServiceRegistry.sol**
   - Registry for service discovery
   - Constructor arguments: None
   - Purpose: MCP-compatible service registry

4. **MockToken.sol**
   - ERC-20 token for testing
   - Constructor arguments: [name, symbol, decimals, initialSupply]
   - Purpose: Test token for development and testing

## Verification Status

### ✅ Verified Contracts
- All contracts compile successfully with Solidity 0.8.20
- Optimizer enabled with 200 runs
- Compatible with Cronos EVM

### ⚠️ Important Notes

1. **Timing**: Contract verification may take a few minutes after deployment
2. **API Limits**: Cronoscan has rate limits for API calls
3. **Constructor Arguments**: Must match exactly what was used during deployment
4. **Network Selection**: Verify on the correct network (testnet vs mainnet)

## Troubleshooting

### Common Issues

1. **"Contract source code not verified"**
   - Wait 5-10 minutes after deployment
   - Retry verification
   - Check that the contract address is correct

2. **"API key not found"**
   - Verify CRONOSCAN_API_KEY is set in your environment
   - Check that the API key is valid

3. **"Constructor arguments mismatch"**
   - Ensure constructor arguments match deployment exactly
   - For addresses, use the exact format used during deployment

4. **"Contract already verified"**
   - Contract was already verified successfully
   - No action needed

### Manual Verification Steps

If the automated script fails:

1. **Gather Information**:
   - Contract address
   - Contract file path
   - Constructor arguments used during deployment

2. **Use Hardhat Verify**:
   ```bash
   npx hardhat verify --network <network> <contract_address> --contract "<contract_path>" <constructor_args>
   ```

3. **Verify on Cronoscan Website**:
   - Go to Cronoscan
   - Navigate to your contract
   - Click "Verify and Publish"
   - Fill in the verification form

## Best Practices

### 1. **Environment Management**
- Use separate API keys for testnet and mainnet
- Store API keys securely
- Use environment files for sensitive information

### 2. **Version Control**
- Keep deployment files in version control
- Document deployment addresses
- Track verification status

### 3. **Testing**
- Always verify on testnet first
- Test with mock contracts before mainnet
- Verify contract functionality after verification

### 4. **Documentation**
- Document deployment addresses
- Keep verification reports
- Update README with verified contract addresses

## Integration with CI/CD

You can integrate contract verification into your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
name: Deploy and Verify Contracts

on:
  push:
    branches: [main]

jobs:
  deploy-and-verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm install
      - run: pnpm install
      - run: pnpm exec hardhat run scripts/deploy.js --network cronosTestnet
        env:
          CRONOSCAN_API_KEY: ${{ secrets.CRONOSCAN_API_KEY }}
          PRIVATE_KEY: ${{ secrets.PRIVATE_KEY }}
      - run: pnpm exec hardhat run scripts/verify-contracts.js --network cronosTestnet
        env:
          CRONOSCAN_API_KEY: ${{ secrets.CRONOSCAN_API_KEY }}
```

## Verification Reports

The verification script generates detailed reports:

- **Location**: `contracts/deployments/verification/`
- **Format**: JSON with timestamp
- **Contents**:
  - Verified contracts list
  - Failed verification attempts
  - Network and timestamp information
  - Explorer URLs for verified contracts

Example report structure:
```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "network": "cronosTestnet",
  "chainId": 338,
  "verifiedContracts": [
    {
      "name": "AgentWallet",
      "address": "0x...",
      "explorerUrl": "https://testnet.cronoscan.com/address/0x..."
    }
  ],
  "failedVerifications": [],
  "summary": {
    "total": 4,
    "verified": 4,
    "failed": 0
  }
}
```

## Support

For issues with contract verification:

1. Check the Cronoscan documentation
2. Verify your environment variables
3. Ensure contracts are deployed successfully
4. Check the verification logs in `contracts/deployments/verification/`

For Paygent-specific issues, consult the project documentation or create an issue in the repository.