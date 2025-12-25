/**
 * Ethers.js v6 Integration for Cronos EVM
 *
 * This module provides ethers.js v6 integration for connecting to the Cronos EVM
 * blockchain, interacting with smart contracts, and managing blockchain operations.
 */

import { ethers } from 'ethers';

/**
 * Cronos network configuration
 */
export interface CronosNetworkConfig {
  name: string;
  chainId: number;
  rpcUrl: string;
  explorerUrl: string;
  nativeCurrency: {
    name: string;
    symbol: string;
    decimals: number;
  };
}

/**
 * Cronos network configurations
 */
export const CRONOS_NETWORKS = {
  testnet: {
    name: 'Cronos Testnet',
    chainId: 338,
    rpcUrl: process.env.CRONOS_TESTNET_RPC || 'https://evm-t3.cronos.org',
    explorerUrl: 'https://testnet.cronoscan.com',
    nativeCurrency: {
      name: 'Cronos',
      symbol: 'CRO',
      decimals: 18,
    },
  },
  mainnet: {
    name: 'Cronos Mainnet',
    chainId: 25,
    rpcUrl: process.env.CRONOS_MAINNET_RPC || 'https://evm.cronos.org',
    explorerUrl: 'https://cronoscan.com',
    nativeCurrency: {
      name: 'Cronos',
      symbol: 'CRO',
      decimals: 18,
    },
  },
} as const;

/**
 * Ethers.js v6 Cronos Provider
 */
export class CronosProvider {
  private provider: ethers.Provider;
  private network: CronosNetworkConfig;

  constructor(network: 'testnet' | 'mainnet' = 'testnet') {
    this.network = CRONOS_NETWORKS[network];
    this.provider = new ethers.JsonRpcProvider(this.network.rpcUrl);
  }

  /**
   * Get the provider instance
   */
  getProvider(): ethers.Provider {
    return this.provider;
  }

  /**
   * Get network configuration
   */
  getNetwork(): CronosNetworkConfig {
    return this.network;
  }

  /**
   * Get chain ID
   */
  async getChainId(): Promise<number> {
    const network = await this.provider.getNetwork();
    return network.chainId;
  }

  /**
   * Verify chain ID matches expected Cronos chain
   */
  async verifyChainId(): Promise<boolean> {
    const currentChainId = await this.getChainId();
    return currentChainId === this.network.chainId;
  }

  /**
   * Get block number
   */
  async getBlockNumber(): Promise<number> {
    return await this.provider.getBlockNumber();
  }

  /**
   * Get balance of an address
   */
  async getBalance(address: string): Promise<ethers.BigNumber> {
    return await this.provider.getBalance(address);
  }

  /**
   * Get transaction by hash
   */
  async getTransaction(txHash: string): Promise<ethers.TransactionResponse | null> {
    return await this.provider.getTransaction(txHash);
  }

  /**
   * Wait for transaction confirmation
   */
  async waitForTransaction(
    txHash: string,
    confirmations: number = 1
  ): Promise<ethers.TransactionReceipt> {
    return await this.provider.waitForTransaction(txHash, confirmations);
  }

  /**
   * Estimate gas for a transaction
   */
  async estimateGas(transaction: ethers.TransactionRequest): Promise<ethers.BigNumber> {
    return await this.provider.estimateGas(transaction);
  }

  /**
   * Get gas price
   */
  async getGasPrice(): Promise<ethers.BigNumber> {
    return await this.provider.getFeeData().then(feeData => feeData.gasPrice!);
  }
}

/**
 * Cronos Wallet (Signer)
 */
export class CronosWallet {
  private wallet: ethers.Wallet;
  private provider: CronosProvider;

  constructor(privateKey: string, network: 'testnet' | 'mainnet' = 'testnet') {
    this.provider = new CronosProvider(network);
    this.wallet = new ethers.Wallet(privateKey, this.provider.getProvider());
  }

  /**
   * Get wallet address
   */
  getAddress(): string {
    return this.wallet.address;
  }

  /**
   * Get wallet instance
   */
  getWallet(): ethers.Wallet {
    return this.wallet;
  }

  /**
   * Get provider
   */
  getProvider(): CronosProvider {
    return this.provider;
  }

  /**
   * Get balance
   */
  async getBalance(): Promise<ethers.BigNumber> {
    return await this.provider.getBalance(this.wallet.address);
  }

  /**
   * Send transaction
   */
  async sendTransaction(transaction: ethers.TransactionRequest): Promise<ethers.TransactionResponse> {
    return await this.wallet.sendTransaction(transaction);
  }

  /**
   * Sign message
   */
  async signMessage(message: string | Uint8Array): Promise<string> {
    return await this.wallet.signMessage(message);
  }

  /**
   * Sign typed data (EIP-712)
   */
  async signTypedData(
    domain: ethers.TypedDataDomain,
    types: Record<string, Array<ethers.TypedDataField>>,
    value: Record<string, any>
  ): Promise<string> {
    return await this.wallet.signTypedData(domain, types, value);
  }
}

/**
 * Smart Contract Interaction
 */
export class CronosContract {
  private contract: ethers.Contract;
  private provider: CronosProvider;

  constructor(
    address: string,
    abi: ethers.Interface | ethers.InterfaceAbi,
    wallet?: CronosWallet
  ) {
    this.provider = wallet?.getProvider() || new CronosProvider();
    const signerOrProvider = wallet ? wallet.getWallet() : this.provider.getProvider();
    this.contract = new ethers.Contract(address, abi, signerOrProvider);
  }

  /**
   * Get contract instance
   */
  getContract(): ethers.Contract {
    return this.contract;
  }

  /**
   * Get contract address
   */
  getAddress(): string {
    return this.contract.target as string;
  }

  /**
   * Call read-only function
   */
  async callReadOnlyFunction<T = any>(methodName: string, ...args: any[]): Promise<T> {
    const method = this.contract[methodName] as (...args: any[]) => Promise<T>;
    return await method(...args);
  }

  /**
   * Send transaction to contract
   */
  async sendTransaction(
    methodName: string,
    ...args: any[]
  ): Promise<ethers.TransactionResponse> {
    const method = this.contract[methodName] as (...args: any[]) => Promise<ethers.TransactionResponse>;
    return await method(...args);
  }

  /**
   * Estimate gas for contract call
   */
  async estimateGas(methodName: string, ...args: any[]): Promise<ethers.BigNumber> {
    const method = this.contract.estimateGas[methodName] as (...args: any[]) => Promise<ethers.BigNumber>;
    return await method(...args);
  }

  /**
   * Add event listener
   */
  addEventListener(eventName: string, listener: (...args: any[]) => void): void {
    this.contract.on(eventName, listener);
  }

  /**
   * Remove event listener
   */
  removeEventListener(eventName: string, listener?: (...args: any[]) => void): void {
    if (listener) {
      this.contract.off(eventName, listener);
    } else {
      this.contract.removeAllListeners(eventName);
    }
  }
}

/**
 * Utility functions
 */

/**
 * Validate address format
 */
export function isValidAddress(address: string): boolean {
  try {
    return ethers.isAddress(address);
  } catch {
    return false;
  }
}

/**
 * Format address with ellipsis
 */
export function formatAddress(address: string): string {
  if (!isValidAddress(address)) {
    return address;
  }
  return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
}

/**
 * Convert from wei to human readable format
 */
export function formatUnits(amount: string | number | bigint, decimals: number = 18): string {
  return ethers.formatUnits(amount, decimals);
}

/**
 * Convert to wei from human readable format
 */
export function parseUnits(amount: string | number, decimals: number = 18): ethers.BigNumber {
  return ethers.parseUnits(amount.toString(), decimals);
}

/**
 * Wait for a specified amount of time
 */
export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Retry function with exponential backoff
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> {
  let lastError: Error;

  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      if (i === maxRetries) {
        throw lastError;
      }

      const delay = baseDelay * Math.pow(2, i);
      console.log(`Attempt ${i + 1} failed, retrying in ${delay}ms...`);
      await sleep(delay);
    }
  }

  throw lastError!;
}

/**
 * Initialize Cronos connection
 */
export async function initializeCronosConnection(
  network: 'testnet' | 'mainnet' = 'testnet',
  privateKey?: string
): Promise<{
  provider: CronosProvider;
  wallet?: CronosWallet;
}> {
  const provider = new CronosProvider(network);

  // Verify connection
  try {
    const chainId = await provider.verifyChainId();
    if (!chainId) {
      throw new Error(`Invalid chain ID. Expected ${provider.getNetwork().chainId}`);
    }

    console.log(`✅ Connected to ${provider.getNetwork().name}`);
    console.log(`📍 Chain ID: ${provider.getNetwork().chainId}`);
    console.log(`🌐 RPC URL: ${provider.getNetwork().rpcUrl}`);

    let wallet: CronosWallet | undefined;

    if (privateKey) {
      wallet = new CronosWallet(privateKey, network);
      const address = wallet.getAddress();
      const balance = await wallet.getBalance();

      console.log(`👛 Wallet: ${formatAddress(address)}`);
      console.log(`💰 Balance: ${formatUnits(balance, 18)} ${provider.getNetwork().nativeCurrency.symbol}`);

      return { provider, wallet };
    }

    return { provider };
  } catch (error) {
    console.error('❌ Failed to initialize Cronos connection:', error);
    throw error;
  }
}

export default {
  CronosProvider,
  CronosWallet,
  CronosContract,
  initializeCronosConnection,
  isValidAddress,
  formatAddress,
  formatUnits,
  parseUnits,
  sleep,
  retryWithBackoff,
};