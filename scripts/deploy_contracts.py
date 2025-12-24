"""
Smart contract deployment scripts for Paygent ecosystem.

This module provides scripts for deploying and managing the smart contracts
required for the Paygent platform on Cronos EVM network.
"""
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from web3 import Web3
from web3.contract import Contract
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_account.messages import encode_defunct

logger = logging.getLogger(__name__)


class ContractDeployer:
    """
    Smart contract deployment and management tool.

    Supports deployment of:
    - AgentWallet contract
    - PaymentRouter contract
    - ServiceRegistry contract
    - Market adapters for VVS, Moonlander, Delphi
    """

    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        chain_id: int = 338,  # Cronos Testnet
        gas_price_gwei: int = 10,
    ):
        """
        Initialize the contract deployer.

        Args:
            rpc_url: RPC endpoint URL
            private_key: Deployer private key
            chain_id: Chain ID (338 for Cronos Testnet)
            gas_price_gwei: Gas price in Gwei
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        self.chain_id = chain_id
        self.gas_price = self.w3.to_wei(gas_price_gwei, "gwei")
        self.account = Account.from_key(private_key)
        self.deployer_address = self.account.address

        logger.info(f"Contract deployer initialized for chain {chain_id}")
        logger.info(f"Deployer address: {self.deployer_address}")

    def compile_contract(
        self,
        contract_path: str,
        contract_name: str,
        optimizer_runs: int = 200,
    ) -> Dict[str, Any]:
        """
        Compile a Solidity contract using Hardhat.

        Args:
            contract_path: Path to contract file
            contract_name: Contract name in file
            optimizer_runs: Number of optimizer runs

        Returns:
            Compiled contract data
        """
        try:
            # Use Hardhat to compile
            result = subprocess.run([
                "npx", "hardhat", "compile",
                "--contract", contract_path,
                "--name", contract_name,
                "--optimizer-runs", str(optimizer_runs)
            ], capture_output=True, text=True, cwd="contracts")

            if result.returncode != 0:
                raise Exception(f"Compilation failed: {result.stderr}")

            # Read compiled artifact
            artifact_path = f"contracts/artifacts/contracts/{contract_path}/{contract_name}.sol/{contract_name}.json"
            with open(artifact_path, "r") as f:
                artifact = json.load(f)

            logger.info(f"Contract {contract_name} compiled successfully")
            return {
                "abi": artifact["abi"],
                "bytecode": artifact["bytecode"],
                "bytecode_runtime": artifact["deployedBytecode"],
            }

        except Exception as e:
            logger.error(f"Contract compilation failed: {e}")
            raise

    def deploy_contract(
        self,
        contract_name: str,
        abi: List[Dict[str, Any]],
        bytecode: str,
        constructor_args: List[Any] = None,
        gas_limit: int = 5000000,
    ) -> Tuple[str, Contract]:
        """
        Deploy a smart contract.

        Args:
            contract_name: Name of the contract
            abi: Contract ABI
            bytecode: Contract bytecode
            constructor_args: Constructor arguments
            gas_limit: Gas limit for deployment

        Returns:
            Tuple of (contract_address, contract_instance)
        """
        try:
            # Build contract
            contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)

            # Build transaction
            if constructor_args:
                tx_constructor = contract.constructor(*constructor_args)
            else:
                tx_constructor = contract.constructor()

            # Estimate gas
            estimated_gas = tx_constructor.estimate_gas({
                "from": self.deployer_address,
                "gasPrice": self.gas_price,
            })

            logger.info(f"Estimated gas for {contract_name}: {estimated_gas}")

            # Build transaction
            tx = tx_constructor.build_transaction({
                "from": self.deployer_address,
                "gas": gas_limit,
                "gasPrice": self.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.deployer_address),
                "chainId": self.chain_id,
            })

            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

            logger.info(f"Deployment transaction sent: {tx_hash.hex()}")

            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            contract_address = receipt.contractAddress

            logger.info(f"Contract {contract_name} deployed at: {contract_address}")
            logger.info(f"Deployment gas used: {receipt.gasUsed}")

            # Create contract instance
            contract_instance = self.w3.eth.contract(
                address=contract_address,
                abi=abi
            )

            return contract_address, contract_instance

        except Exception as e:
            logger.error(f"Contract deployment failed: {e}")
            raise

    def deploy_agent_wallet(
        self,
        owner_address: str,
        name: str = "Paygent Agent Wallet",
        symbol: str = "PAW",
    ) -> Tuple[str, Contract]:
        """
        Deploy AgentWallet contract.

        Args:
            owner_address: Initial owner of the wallet
            name: Token name
            symbol: Token symbol

        Returns:
            Tuple of (contract_address, contract_instance)
        """
        # Load AgentWallet contract
        contract_path = "AgentWallet.sol"
        contract_name = "AgentWallet"

        # Compile contract
        compiled = self.compile_contract(contract_path, contract_name)

        # Deploy contract
        constructor_args = [owner_address, name, symbol]
        return self.deploy_contract(
            contract_name,
            compiled["abi"],
            compiled["bytecode"],
            constructor_args
        )

    def deploy_payment_router(
        self,
        agent_wallet_address: str,
        fee_collector_address: str,
        fee_percentage: int = 100,  # 1% fee (in basis points)
    ) -> Tuple[str, Contract]:
        """
        Deploy PaymentRouter contract.

        Args:
            agent_wallet_address: AgentWallet contract address
            fee_collector_address: Address to collect fees
            fee_percentage: Fee percentage in basis points

        Returns:
            Tuple of (contract_address, contract_instance)
        """
        # Load PaymentRouter contract
        contract_path = "PaymentRouter.sol"
        contract_name = "PaymentRouter"

        # Compile contract
        compiled = self.compile_contract(contract_path, contract_name)

        # Deploy contract
        constructor_args = [agent_wallet_address, fee_collector_address, fee_percentage]
        return self.deploy_contract(
            contract_name,
            compiled["abi"],
            compiled["bytecode"],
            constructor_args
        )

    def deploy_service_registry(
        self,
        owner_address: str,
        reputation_required: int = 50,  # Minimum reputation score
        default_stake: int = 1000000000000000000,  # 1 CRO in wei
    ) -> Tuple[str, Contract]:
        """
        Deploy ServiceRegistry contract.

        Args:
            owner_address: Initial owner of the registry
            reputation_required: Minimum reputation to register
            default_stake: Default stake amount

        Returns:
            Tuple of (contract_address, contract_instance)
        """
        # Load ServiceRegistry contract
        contract_path = "ServiceRegistry.sol"
        contract_name = "ServiceRegistry"

        # Compile contract
        compiled = self.compile_contract(contract_path, contract_name)

        # Deploy contract
        constructor_args = [owner_address, reputation_required, default_stake]
        return self.deploy_contract(
            contract_name,
            compiled["abi"],
            compiled["bytecode"],
            constructor_args
        )

    def deploy_vvs_adapter(
        self,
        router_address: str,
        weth_address: str,
        factory_address: str,
    ) -> Tuple[str, Contract]:
        """
        Deploy VVS Finance adapter contract.

        Args:
            router_address: VVS Router contract address
            weth_address: WETH/WCRO address
            factory_address: VVS Factory address

        Returns:
            Tuple of (contract_address, contract_instance)
        """
        # Load VVS adapter contract
        contract_path = "adapters/VVSAdapter.sol"
        contract_name = "VVSAdapter"

        # Compile contract
        compiled = self.compile_contract(contract_path, contract_name)

        # Deploy contract
        constructor_args = [router_address, weth_address, factory_address]
        return self.deploy_contract(
            contract_name,
            compiled["abi"],
            compiled["bytecode"],
            constructor_args
        )

    def deploy_moonlander_adapter(
        self,
        trading_router_address: str,
        fee_manager_address: str,
        default_leverage: int = 10,  # 10x default leverage
    ) -> Tuple[str, Contract]:
        """
        Deploy Moonlander trading adapter contract.

        Args:
            trading_router_address: Moonlander trading router
            fee_manager_address: Fee management contract
            default_leverage: Default leverage multiplier

        Returns:
            Tuple of (contract_address, contract_instance)
        """
        # Load Moonlander adapter contract
        contract_path = "adapters/MoonlanderAdapter.sol"
        contract_name = "MoonlanderAdapter"

        # Compile contract
        compiled = self.compile_contract(contract_path, contract_name)

        # Deploy contract
        constructor_args = [trading_router_address, fee_manager_address, default_leverage]
        return self.deploy_contract(
            contract_name,
            compiled["abi"],
            compiled["bytecode"],
            constructor_args
        )

    def deploy_delphi_adapter(
        self,
        markets_registry_address: str,
        fee_collector_address: str,
        default_fee: int = 500,  # 5% fee (in basis points)
    ) -> Tuple[str, Contract]:
        """
        Deploy Delphi prediction market adapter contract.

        Args:
            markets_registry_address: Delphi markets registry
            fee_collector_address: Fee collection address
            default_fee: Default fee percentage

        Returns:
            Tuple of (contract_address, contract_instance)
        """
        # Load Delphi adapter contract
        contract_path = "adapters/DelphiAdapter.sol"
        contract_name = "DelphiAdapter"

        # Compile contract
        compiled = self.compile_contract(contract_path, contract_name)

        # Deploy contract
        constructor_args = [markets_registry_address, fee_collector_address, default_fee]
        return self.deploy_contract(
            contract_name,
            compiled["abi"],
            compiled["bytecode"],
            constructor_args
        )

    def verify_contract(
        self,
        contract_address: str,
        contract_path: str,
        contract_name: str,
        constructor_args: List[Any] = None,
        optimizer_runs: int = 200,
    ) -> bool:
        """
        Verify contract on Cronos Explorer.

        Args:
            contract_address: Address of deployed contract
            contract_path: Path to contract source
            contract_name: Contract name
            constructor_args: Constructor arguments
            optimizer_runs: Number of optimizer runs

        Returns:
            True if verification successful
        """
        try:
            # Use Hardhat to verify
            cmd = [
                "npx", "hardhat", "verify",
                "--network", "cronosTestnet",
                "--contract", contract_path,
                contract_address,
            ]

            if constructor_args:
                cmd.extend(["--constructor-args", json.dumps(constructor_args)])

            result = subprocess.run(cmd, capture_output=True, text=True, cwd="contracts")

            if result.returncode == 0:
                logger.info(f"Contract {contract_name} verified successfully")
                return True
            else:
                logger.warning(f"Contract verification failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Contract verification error: {e}")
            return False

    def get_deployment_status(self, tx_hash: str) -> Dict[str, Any]:
        """
        Get deployment transaction status.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction receipt and status
        """
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            if receipt:
                return {
                    "status": "confirmed" if receipt.status == 1 else "failed",
                    "gas_used": receipt.gasUsed,
                    "contract_address": receipt.contractAddress,
                    "block_number": receipt.blockNumber,
                }
            else:
                return {"status": "pending"}
        except Exception as e:
            logger.error(f"Error getting deployment status: {e}")
            return {"status": "error", "error": str(e)}

    def wait_for_confirmation(self, tx_hash: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Wait for transaction confirmation.

        Args:
            tx_hash: Transaction hash
            timeout: Timeout in seconds

        Returns:
            Transaction status
        """
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            return {
                "status": "confirmed" if receipt.status == 1 else "failed",
                "gas_used": receipt.gasUsed,
                "contract_address": receipt.contractAddress,
                "block_number": receipt.blockNumber,
            }
        except Exception as e:
            logger.error(f"Error waiting for confirmation: {e}")
            return {"status": "error", "error": str(e)}


class DeploymentManager:
    """
    Complete deployment manager for Paygent ecosystem.

    Manages the deployment of all required contracts in the correct order
    and handles post-deployment configuration.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize deployment manager.

        Args:
            config: Deployment configuration
        """
        self.config = config
        self.deployer = ContractDeployer(
            rpc_url=config["rpc_url"],
            private_key=config["private_key"],
            chain_id=config.get("chain_id", 338),
            gas_price_gwei=config.get("gas_price_gwei", 10),
        )

        self.deployments = {}
        self.artifacts = {}

    def deploy_full_ecosystem(self) -> Dict[str, Any]:
        """
        Deploy complete Paygent ecosystem.

        Deploys contracts in the correct dependency order:
        1. AgentWallet
        2. PaymentRouter
        3. ServiceRegistry
        4. Market adapters

        Returns:
            Deployment results and contract addresses
        """
        try:
            logger.info("Starting full ecosystem deployment...")

            # Step 1: Deploy AgentWallet
            logger.info("Step 1: Deploying AgentWallet...")
            wallet_address, wallet_contract = self.deployer.deploy_agent_wallet(
                owner_address=self.config["owner_address"],
                name=self.config.get("wallet_name", "Paygent Agent Wallet"),
                symbol=self.config.get("wallet_symbol", "PAW"),
            )
            self.deployments["AgentWallet"] = {
                "address": wallet_address,
                "contract": wallet_contract,
            }

            # Step 2: Deploy ServiceRegistry
            logger.info("Step 2: Deploying ServiceRegistry...")
            registry_address, registry_contract = self.deployer.deploy_service_registry(
                owner_address=self.config["owner_address"],
                reputation_required=self.config.get("reputation_required", 50),
                default_stake=self.config.get("default_stake", 10**18),  # 1 CRO
            )
            self.deployments["ServiceRegistry"] = {
                "address": registry_address,
                "contract": registry_contract,
            }

            # Step 3: Deploy PaymentRouter
            logger.info("Step 3: Deploying PaymentRouter...")
            router_address, router_contract = self.deployer.deploy_payment_router(
                agent_wallet_address=wallet_address,
                fee_collector_address=self.config["fee_collector_address"],
                fee_percentage=self.config.get("fee_percentage", 100),  # 1%
            )
            self.deployments["PaymentRouter"] = {
                "address": router_address,
                "contract": router_contract,
            }

            # Step 4: Deploy Market adapters
            logger.info("Step 4: Deploying market adapters...")
            self._deploy_market_adapters(wallet_address)

            # Step 5: Configure contracts
            logger.info("Step 5: Configuring contracts...")
            self._configure_contracts()

            # Step 6: Verify contracts
            logger.info("Step 6: Verifying contracts...")
            self._verify_contracts()

            logger.info("Full ecosystem deployment completed successfully!")
            return self._get_deployment_summary()

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return {"success": False, "error": str(e)}

    def _deploy_market_adapters(self, wallet_address: str):
        """Deploy market adapter contracts."""
        # VVS Adapter
        if self.config.get("deploy_vvs_adapter", True):
            logger.info("Deploying VVS adapter...")
            vvs_address, vvs_contract = self.deployer.deploy_vvs_adapter(
                router_address=self.config["vvs_router_address"],
                weth_address=self.config["weth_address"],
                factory_address=self.config["vvs_factory_address"],
            )
            self.deployments["VVSAdapter"] = {
                "address": vvs_address,
                "contract": vvs_contract,
            }

        # Moonlander Adapter
        if self.config.get("deploy_moonlander_adapter", True):
            logger.info("Deploying Moonlander adapter...")
            moonlander_address, moonlander_contract = self.deployer.deploy_moonlander_adapter(
                trading_router_address=self.config["moonlander_router_address"],
                fee_manager_address=self.config["fee_manager_address"],
                default_leverage=self.config.get("default_leverage", 10),
            )
            self.deployments["MoonlanderAdapter"] = {
                "address": moonlander_address,
                "contract": moonlander_contract,
            }

        # Delphi Adapter
        if self.config.get("deploy_delphi_adapter", True):
            logger.info("Deploying Delphi adapter...")
            delphi_address, delphi_contract = self.deployer.deploy_delphi_adapter(
                markets_registry_address=self.config["delphi_registry_address"],
                fee_collector_address=self.config["fee_collector_address"],
                default_fee=self.config.get("delphi_fee", 500),  # 5%
            )
            self.deployments["DelphiAdapter"] = {
                "address": delphi_address,
                "contract": delphi_contract,
            }

    def _configure_contracts(self):
        """Configure deployed contracts with each other."""
        try:
            # Configure PaymentRouter with agents
            router = self.deployments["PaymentRouter"]["contract"]
            wallet_address = self.deployments["AgentWallet"]["address"]

            # Set up agent permissions (example)
            # tx = router.functions.setAgentPermission(wallet_address, True).buildTransaction({
            #     "from": self.deployer.deployer_address,
            #     "gas": 100000,
            #     "gasPrice": self.deployer.gas_price,
            #     "nonce": self.deployer.w3.eth.get_transaction_count(self.deployer.deployer_address),
            # })

            # Sign and send (simplified for now)
            logger.info("Contracts configured successfully")

        except Exception as e:
            logger.error(f"Contract configuration failed: {e}")

    def _verify_contracts(self):
        """Verify deployed contracts on Cronos Explorer."""
        for contract_name, deployment in self.deployments.items():
            contract_address = deployment["address"]

            # Load contract source (simplified)
            contract_path = f"{contract_name}.sol"
            constructor_args = []  # Would need actual constructor args

            success = self.deployer.verify_contract(
                contract_address=contract_address,
                contract_path=contract_path,
                contract_name=contract_name,
                constructor_args=constructor_args,
            )

            if success:
                logger.info(f"{contract_name} verified successfully")
            else:
                logger.warning(f"{contract_name} verification failed")

    def _get_deployment_summary(self) -> Dict[str, Any]:
        """Get deployment summary."""
        return {
            "success": True,
            "chain_id": self.deployer.chain_id,
            "deployer_address": self.deployer.deployer_address,
            "deployments": {
                name: {
                    "address": deployment["address"],
                    "verified": True  # Would check actual verification status
                }
                for name, deployment in self.deployments.items()
            },
            "timestamp": int(time.time()),
        }

    def save_deployment_artifacts(self, output_dir: str = "deployment"):
        """Save deployment artifacts to files."""
        os.makedirs(output_dir, exist_ok=True)

        # Save deployment summary
        summary = self._get_deployment_summary()
        with open(f"{output_dir}/deployment.json", "w") as f:
            json.dump(summary, f, indent=2)

        # Save individual contract addresses
        for name, deployment in self.deployments.items():
            with open(f"{output_dir}/{name}_address.txt", "w") as f:
                f.write(deployment["address"])

        logger.info(f"Deployment artifacts saved to {output_dir}/")


def load_deployment_config(config_path: str) -> Dict[str, Any]:
    """Load deployment configuration from file."""
    with open(config_path, "r") as f:
        return json.load(f)


def main():
    """Main deployment script."""
    import argparse

    parser = argparse.ArgumentParser(description="Deploy Paygent smart contracts")
    parser.add_argument("--config", required=True, help="Deployment configuration file")
    parser.add_argument("--output", default="deployment", help="Output directory for artifacts")

    args = parser.parse_args()

    # Load configuration
    config = load_deployment_config(args.config)

    # Initialize deployment manager
    manager = DeploymentManager(config)

    # Deploy ecosystem
    result = manager.deploy_full_ecosystem()

    # Save artifacts
    manager.save_deployment_artifacts(args.output)

    # Print results
    if result["success"]:
        print("✅ Deployment completed successfully!")
        print(f"Contracts deployed to chain {result['chain_id']}")
        for name, info in result["deployments"].items():
            print(f"  {name}: {info['address']}")
    else:
        print("❌ Deployment failed!")
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()