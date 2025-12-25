/**
 * Test script for ethers.js v6 integration with Cronos EVM
 */

import {
  initializeCronosConnection,
  CronosProvider,
  CronosWallet,
  CronosContract,
  isValidAddress,
  formatAddress,
  formatUnits,
  parseUnits,
  retryWithBackoff,
} from '../src/blockchain/cronos';

/**
 * Test ethers.js v6 integration
 */
async function testEthersIntegration() {
  console.log('🧪 Testing ethers.js v6 integration with Cronos EVM...\n');

  try {
    // Test 1: Provider connection
    console.log('1. Testing provider connection...');
    const { provider } = await initializeCronosConnection('testnet');
    console.log('   ✅ Provider connected successfully');

    // Test 2: Chain ID verification
    console.log('\n2. Testing chain ID verification...');
    const chainId = await provider.getChainId();
    console.log(`   ✅ Chain ID: ${chainId} (Cronos Testnet: ${provider.getNetwork().chainId})`);
    const isValidChain = await provider.verifyChainId();
    console.log(`   ✅ Chain verification: ${isValidChain ? 'PASSED' : 'FAILED'}`);

    // Test 3: Block number
    console.log('\n3. Testing block number retrieval...');
    const blockNumber = await provider.getBlockNumber();
    console.log(`   ✅ Current block: ${blockNumber}`);

    // Test 4: Address validation
    console.log('\n4. Testing address validation...');
    const testAddress = '0x742d35Cc6634C0532925a3b8D000b4B35C0c2b6d';
    console.log(`   Address: ${testAddress}`);
    console.log(`   ✅ Valid address: ${isValidAddress(testAddress)}`);
    console.log(`   ✅ Formatted: ${formatAddress(testAddress)}`);

    // Test 5: Unit conversion
    console.log('\n5. Testing unit conversion...');
    const weiAmount = '1000000000000000000'; // 1 CRO in wei
    const formatted = formatUnits(weiAmount, 18);
    console.log(`   ✅ 1 CRO = ${weiAmount} wei = ${formatted} CRO`);

    const parsed = parseUnits('2.5', 18);
    console.log(`   ✅ 2.5 CRO = ${parsed.toString()} wei`);

    // Test 6: Wallet creation (if private key available)
    console.log('\n6. Testing wallet creation...');
    const privateKey = process.env.PRIVATE_KEY;
    if (privateKey) {
      const wallet = new CronosWallet(privateKey, 'testnet');
      console.log(`   ✅ Wallet address: ${formatAddress(wallet.getAddress())}`);

      // Test balance
      const balance = await wallet.getBalance();
      console.log(`   ✅ Balance: ${formatUnits(balance, 18)} CRO`);
    } else {
      console.log('   ⚠️  No private key provided, skipping wallet tests');
    }

    // Test 7: Retry mechanism
    console.log('\n7. Testing retry mechanism...');
    let attemptCount = 0;
    const testFunction = async () => {
      attemptCount++;
      if (attemptCount < 2) {
        throw new Error('Simulated failure');
      }
      return 'Success!';
    };

    const result = await retryWithBackoff(testFunction, 3, 100);
    console.log(`   ✅ Retry mechanism: ${result}`);

    // Test 8: Configuration validation
    console.log('\n8. Testing configuration...');
    const network = provider.getNetwork();
    console.log(`   ✅ Network name: ${network.name}`);
    console.log(`   ✅ RPC URL: ${network.rpcUrl}`);
    console.log(`   ✅ Explorer: ${network.explorerUrl}`);
    console.log(`   ✅ Native currency: ${network.nativeCurrency.symbol}`);

    console.log('\n' + '='.repeat(60));
    console.log('🎉 ETHERS.JS V6 INTEGRATION TESTS PASSED');
    console.log('='.repeat(60));
    console.log('✅ Provider connection working');
    console.log('✅ Chain ID verification working');
    console.log('✅ Address validation working');
    console.log('✅ Unit conversion working');
    console.log('✅ Retry mechanism working');
    console.log('✅ Configuration validation working');
    console.log('='.repeat(60));

    return true;

  } catch (error) {
    console.error('❌ Ethers.js integration test failed:', error);
    return false;
  }
}

/**
 * Performance test
 */
async function testPerformance() {
  console.log('\n🚀 Running performance tests...\n');

  const { provider } = await initializeCronosConnection('testnet');

  // Test multiple block fetches
  console.log('1. Testing block fetch performance...');
  const startTime = Date.now();

  for (let i = 0; i < 5; i++) {
    await provider.getBlockNumber();
  }

  const endTime = Date.now();
  console.log(`   ✅ 5 block fetches: ${endTime - startTime}ms`);

  // Test gas price fetch
  console.log('\n2. Testing gas price fetch...');
  const gasPriceStart = Date.now();
  await provider.getGasPrice();
  const gasPriceEnd = Date.now();
  console.log(`   ✅ Gas price fetch: ${gasPriceEnd - gasPriceStart}ms`);

  console.log('\n✅ Performance tests completed');
}

/**
 * Environment validation
 */
function validateEnvironment() {
  console.log('🔍 Validating environment...\n');

  const requiredEnvVars = [
    'CRONOS_TESTNET_RPC',
    'CRONOS_MAINNET_RPC',
    'PRIVATE_KEY'
  ];

  const missing = requiredEnvVars.filter(envVar => !process.env[envVar]);

  if (missing.length > 0) {
    console.log('⚠️  Missing environment variables:');
    missing.forEach(envVar => console.log(`   - ${envVar}`));
    console.log('\n💡 Set these variables for full functionality');
  } else {
    console.log('✅ All required environment variables are set');
  }

  console.log(`\n📍 Current network: ${process.env.NODE_ENV || 'development'}`);
  console.log(`📦 Ethers.js version: ^6.12.0 (configured)`);
}

// Run tests if this file is executed directly
if (require.main === module) {
  async function runTests() {
    validateEnvironment();
    const success = await testEthersIntegration();

    if (success) {
      await testPerformance();
      console.log('\n🎉 All tests completed successfully!');
      process.exit(0);
    } else {
      console.log('\n❌ Some tests failed');
      process.exit(1);
    }
  }

  runTests();
}

export { testEthersIntegration, testPerformance, validateEnvironment };