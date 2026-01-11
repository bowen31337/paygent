#!/usr/bin/env python3
"""
Test x402 Payment Flow on Cronos Testnet

This script demonstrates the complete x402 payment flow:
1. Simulate HTTP 402 Payment Required response
2. Parse payment requirements
3. Generate EIP-712 signature
4. Execute USDC transfer on-chain
5. Verify payment completion

Uses the tUSDC token deployed on Cronos testnet.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

load_dotenv()


# Cronos Testnet Configuration
CRONOS_TESTNET_RPC = "https://evm-t3.cronos.org"
CHAIN_ID = 338

# Load deployment config
DEPLOYMENT_PATH = Path(__file__).parent.parent / "contracts" / "deployments" / "vvs-testnet.json"


def load_deployment():
    """Load deployed contract addresses."""
    with open(DEPLOYMENT_PATH) as f:
        return json.load(f)


# ERC20 ABI (minimal for transfers)
ERC20_ABI = [
    {
        "name": "transfer",
        "type": "function",
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "outputs": [{"name": "", "type": "bool"}]
    },
    {
        "name": "balanceOf",
        "type": "function",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}]
    },
    {
        "name": "decimals",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint8"}]
    },
    {
        "name": "symbol",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "string"}]
    }
]


class X402PaymentFlow:
    """Demonstrates the x402 payment flow."""

    def __init__(self, private_key: str):
        """Initialize with private key."""
        self.w3 = Web3(Web3.HTTPProvider(CRONOS_TESTNET_RPC))
        self.account = Account.from_key(private_key)
        self.deployment = load_deployment()

        # Get tUSDC contract
        self.usdc_address = self.deployment["contracts"]["tUSDC"]
        self.usdc = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.usdc_address),
            abi=ERC20_ABI
        )

        print("=" * 70)
        print("x402 Payment Flow Test - Cronos Testnet")
        print("=" * 70)
        print(f"Wallet: {self.account.address}")
        print(f"tUSDC Contract: {self.usdc_address}")
        print(f"Chain ID: {CHAIN_ID}")
        print("")

    def step1_simulate_402_response(self, service_url: str, price: float):
        """
        Step 1: Simulate HTTP 402 Payment Required response.

        In production, this would come from an actual service.
        """
        print("Step 1: Simulating HTTP 402 Response")
        print("-" * 50)

        # Simulate service endpoint
        print(f"  Request: GET {service_url}")

        # Simulate 402 response
        response_402 = {
            "status_code": 402,
            "headers": {
                "X-Payment-Required": "true",
                "X-Payment-Amount": str(price),
                "X-Payment-Token": "USDC",
                "X-Payment-Network": "cronos-testnet",
                "X-Payment-Recipient": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",  # Demo recipient
            },
            "body": {
                "error": "payment_required",
                "message": "Please pay to access this resource",
                "payment": {
                    "amount": price,
                    "token": "USDC",
                    "recipient": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
                    "network": "cronos-testnet"
                }
            }
        }

        print(f"  Response: HTTP 402 Payment Required")
        print(f"  Amount: {price} USDC")
        print(f"  Recipient: {response_402['body']['payment']['recipient']}")
        print("")

        return response_402

    def step2_parse_payment_requirements(self, response_402: dict) -> dict:
        """
        Step 2: Parse payment requirements from 402 response.
        """
        print("Step 2: Parsing Payment Requirements")
        print("-" * 50)

        payment_info = response_402["body"]["payment"]

        print(f"  Amount: {payment_info['amount']} {payment_info['token']}")
        print(f"  Recipient: {payment_info['recipient']}")
        print(f"  Network: {payment_info['network']}")
        print("")

        return payment_info

    def step3_generate_eip712_signature(self, payment_info: dict) -> dict:
        """
        Step 3: Generate EIP-712 signature for payment authorization.
        """
        print("Step 3: Generating EIP-712 Signature")
        print("-" * 50)

        # EIP-712 domain
        domain = {
            "name": "PaygentPayment",
            "version": "1.0",
            "chainId": CHAIN_ID,
            "verifyingContract": "0x0000000000000000000000000000000000000000"  # Placeholder
        }

        # Payment message
        timestamp = int(time.time())
        nonce = timestamp  # Use timestamp as nonce for demo

        message = {
            "serviceUrl": "https://api.example.com/premium-data",
            "amount": int(payment_info["amount"] * 1e6),  # Convert to 6 decimals
            "token": payment_info["token"],
            "description": "Premium data access",
            "timestamp": timestamp,
            "nonce": nonce,
            "walletAddress": self.account.address
        }

        # EIP-712 types
        types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "Payment": [
                {"name": "serviceUrl", "type": "string"},
                {"name": "amount", "type": "uint256"},
                {"name": "token", "type": "string"},
                {"name": "description", "type": "string"},
                {"name": "timestamp", "type": "uint256"},
                {"name": "nonce", "type": "uint256"},
                {"name": "walletAddress", "type": "address"},
            ]
        }

        # Create typed data
        from eth_account.messages import encode_typed_data

        encoded_message = encode_typed_data(
            domain_data=domain,
            message_types={"Payment": types["Payment"]},
            message_data=message,
        )

        # Sign
        signed = self.account.sign_message(encoded_message)
        signature_hex = signed.signature.hex()
        if not signature_hex.startswith("0x"):
            signature_hex = "0x" + signature_hex

        print(f"  Signer: {self.account.address}")
        print(f"  Amount: {message['amount']} (raw)")
        print(f"  Timestamp: {timestamp}")
        print(f"  Nonce: {nonce}")
        print(f"  Signature: {signature_hex[:20]}...{signature_hex[-10:]}")
        print("")

        return {
            "domain": domain,
            "message": message,
            "signature": signature_hex,
            "signer": self.account.address
        }

    def step4_execute_payment(self, payment_info: dict) -> dict:
        """
        Step 4: Execute USDC transfer on-chain.
        """
        print("Step 4: Executing On-Chain Payment")
        print("-" * 50)

        # Check balance first
        balance = self.usdc.functions.balanceOf(self.account.address).call()
        balance_formatted = balance / 1e6
        print(f"  Current tUSDC balance: {balance_formatted:.6f}")

        amount_raw = int(payment_info["amount"] * 1e6)
        recipient = Web3.to_checksum_address(payment_info["recipient"])

        print(f"  Amount to transfer: {payment_info['amount']} tUSDC")
        print(f"  Recipient: {recipient}")

        if balance < amount_raw:
            print(f"  ERROR: Insufficient balance!")
            return {"success": False, "error": "insufficient_balance"}

        # Build transaction
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        gas_price = self.w3.eth.gas_price

        # Estimate gas
        tx = self.usdc.functions.transfer(recipient, amount_raw).build_transaction({
            'from': self.account.address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': gas_price,
            'chainId': CHAIN_ID
        })

        # Sign and send
        print(f"  Signing transaction...")
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)

        print(f"  Broadcasting transaction...")
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()
        print(f"  Transaction hash: {tx_hash_hex}")

        # Wait for confirmation
        print(f"  Waiting for confirmation...")
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status == 1:
            print(f"  Confirmed in block: {receipt.blockNumber}")
            print(f"  Gas used: {receipt.gasUsed}")
            print("")
            return {
                "success": True,
                "tx_hash": tx_hash_hex,
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed
            }
        else:
            print(f"  Transaction FAILED!")
            return {"success": False, "error": "transaction_failed"}

    def step5_verify_and_retry(self, payment_result: dict, signature_data: dict):
        """
        Step 5: Verify payment and retry request with proof.
        """
        print("Step 5: Verifying Payment & Retrying Request")
        print("-" * 50)

        if not payment_result["success"]:
            print("  Payment failed, cannot retry")
            return

        # In production, this would be sent as X-Payment-Proof header
        payment_proof = {
            "tx_hash": payment_result["tx_hash"],
            "signature": signature_data["signature"],
            "signer": signature_data["signer"],
            "amount": signature_data["message"]["amount"],
            "timestamp": signature_data["message"]["timestamp"]
        }

        print(f"  Payment Proof:")
        print(f"    tx_hash: {payment_proof['tx_hash']}")
        print(f"    signer: {payment_proof['signer']}")
        print(f"    amount: {payment_proof['amount']} (raw)")
        print("")

        # Simulate successful retry
        print(f"  Simulating retry with X-Payment-Proof header...")
        print(f"  Response: HTTP 200 OK")
        print(f"  Data: {{'premium_data': 'Access granted!'}}")
        print("")

        # Check new balance
        new_balance = self.usdc.functions.balanceOf(self.account.address).call()
        print(f"  New tUSDC balance: {new_balance / 1e6:.6f}")

    def run_full_flow(self, service_url: str, price: float):
        """Run the complete x402 flow."""
        # Step 1: Get 402 response
        response_402 = self.step1_simulate_402_response(service_url, price)

        # Step 2: Parse requirements
        payment_info = self.step2_parse_payment_requirements(response_402)

        # Step 3: Generate signature
        signature_data = self.step3_generate_eip712_signature(payment_info)

        # Step 4: Execute payment
        payment_result = self.step4_execute_payment(payment_info)

        # Step 5: Verify and retry
        self.step5_verify_and_retry(payment_result, signature_data)

        # Summary
        print("=" * 70)
        print("x402 PAYMENT FLOW COMPLETE")
        print("=" * 70)
        if payment_result["success"]:
            print(f"  Status: SUCCESS")
            print(f"  Amount: {price} tUSDC")
            print(f"  Transaction: https://explorer.cronos.org/testnet/tx/{payment_result['tx_hash']}")
        else:
            print(f"  Status: FAILED")
            print(f"  Error: {payment_result.get('error', 'unknown')}")
        print("=" * 70)

        return payment_result


def main():
    """Main entry point."""
    # Get private key from environment
    private_key = os.getenv("AGENT_WALLET_PRIVATE_KEY")
    if not private_key:
        print("ERROR: AGENT_WALLET_PRIVATE_KEY not set in .env")
        sys.exit(1)

    # Add 0x prefix if missing
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key

    # Create flow instance
    flow = X402PaymentFlow(private_key)

    # Run the x402 flow with 0.1 USDC payment
    result = flow.run_full_flow(
        service_url="https://api.example.com/premium-data",
        price=0.1  # 0.1 USDC
    )

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
