# Contract Deployment to Cronos Testnet

## Prerequisites

1. Install Node.js LTS (24.x recommended)
2. Install pnpm: `npm install -g pnpm`
3. Create `.env` file with:
   - `PRIVATE_KEY`: Your Cronos testnet wallet private key
   - `CRONOS_TESTNET_RPC`: `https://evm-t3.cronos.org`
   - `CRONOSCAN_API_KEY`: Optional, for contract verification

## Installation

```bash
cd contracts
pnpm install
```

## Compilation

```bash
pnpm exec hardhat compile
```

## Deployment to Testnet

```bash
pnpm exec hardhat run scripts/deploy.js --network cronosTestnet
```

## Deployment to Mainnet

```bash
pnpm exec hardhat run scripts/deploy.js --network cronosMainnet
```

## Contract Verification

After deployment, verify contracts on Cronoscan:

```bash
pnpm exec hardhat verify --network cronosTestnet <CONTRACT_ADDRESS> <CONSTRUCTOR_ARGS>
```

## Deployed Contracts

The deployment script deploys three contracts:

1. **AgentWallet.sol**
   - Owner: Deployer address
   - Daily Limit: 1000 wei (configurable)

2. **PaymentRouter.sol**
   - Fee Collector: Deployer address
   - Fee Percentage: 1% (100 basis points)

3. **ServiceRegistry.sol**
   - Owner: Deployer address
   - Reputation Required: 50
   - Default Stake: 10 CRO

## Environment Variables

```env
# Cronos Testnet Configuration
CRONOS_TESTNET_RPC=https://evm-t3.cronos.org
CRONOS_TESTNET_CHAIN_ID=338
PRIVATE_KEY=your-private-key-here

# Cronos Mainnet Configuration
CRONOS_MAINNET_RPC=https://evm.cronos.org
CRONOS_MAINNET_CHAIN_ID=25

# Verification
CRONOSCAN_API_KEY=your-cronoscan-api-key
```

## Deployment Addresses

After deployment, addresses are saved to `deployments/<network>.json`

## Testing

```bash
pnpm exec hardhat test
```

## Next Steps

1. Deploy to Cronos testnet using the commands above
2. Verify contracts on Cronoscan
3. Update backend configuration with deployed contract addresses
4. Test integration with the Paygent API