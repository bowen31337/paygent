#!/usr/bin/env python3
"""
Test script for Real VVS Finance interactions on Cronos Testnet.
WARNING: This script will execute REAL transactions if configured.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from decimal import Decimal

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import dotenv
dotenv.load_dotenv()

from src.connectors.vvs import VVSFinanceConnector
from src.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_vvs_real")

async def main():
    print("🚀 Starting Real VVS Finance Test (Testnet)")
    print("=" * 60)

    # Check configuration
    private_key = os.getenv("AGENT_WALLET_PRIVATE_KEY")
    if not private_key:
        print("❌ AGENT_WALLET_PRIVATE_KEY is missing in .env")
        print("   Please add your testnet wallet private key to .env")
        return

    # Initialize connector with explicit testnet usage
    print("Initializing VVS Connector...")
    connector = VVSFinanceConnector(use_mock=False, use_testnet=True)
    
    # 1. Test Connection
    w3 = connector._get_web3()
    if not w3 or not w3.is_connected():
        print("❌ Failed to connect to Cronos Testnet RPC")
        return
    
    chain_id = w3.eth.chain_id
    print(f"✅ Connected to Cronos Chain ID: {chain_id}")
    if chain_id != 338:
        print("⚠️ WARNING: Not connected to Cronos Testnet (Chain ID 338)")

    # 2. Check Wallet
    try:
        if private_key.startswith("0x"):
            private_key = private_key[2:]
        
        # Verify hex format
        try:
            int(private_key, 16)
        except ValueError:
            print("❌ AGENT_WALLET_PRIVATE_KEY is not a valid hexadecimal string")
            print(f"   Value found: {private_key[:4]}...{private_key[-4:] if len(private_key) > 8 else ''}")
            return

        account = w3.eth.account.from_key(private_key)
        address = account.address
        balance_wei = w3.eth.get_balance(address)
        balance_tcro = w3.from_wei(balance_wei, 'ether')
    except Exception as e:
        print(f"❌ Failed to load wallet: {e}")
        print("   Please ensure AGENT_WALLET_PRIVATE_KEY in .env is a valid hex string (with or without 0x prefix)")
        return
    
    print(f"Wallet Address: {address}")
    print(f"Balance: {balance_tcro} TCRO")
    
    if balance_tcro < 1:
        print("⚠️ Warning: Low TCRO balance. Swaps might fail due to gas.")

    # 3. Get Quote
    print("\n📊 getting quote for 1.0 TCRO -> USDC...")
    try:
        quote = connector.get_quote(
            from_token="CRO",
            to_token="USDC",
            amount=1.0,
            slippage_tolerance=1.0
        )
        print("Quote Received:")
        print(f"  Expected Out: {quote['expected_amount_out']} USDC")
        print(f"  Min Out: {quote['min_amount_out']} USDC")
        print(f"  Source: {quote.get('source')}")
        
        if quote.get('source') != 'on-chain':
            print("⚠️ Quote returned from MOCK source. RPC might be failing to call contract.")
    except Exception as e:
        print(f"❌ Get Quote Failed: {e}")
        return

    # 4. Build Swap Transaction
    print("\n🔄 Building Swap Transaction...")
    try:
        swap_result = connector.swap(
            from_token="CRO",
            to_token="USDC",
            amount=1.0,
            slippage_tolerance=1.0,
            recipient=address
        )
        
        if not swap_result.get("unsigned_tx"):
            print("❌ Failed to build swap transaction")
            return
            
        unsigned_tx = swap_result["unsigned_tx"]
        print("Transaction data built successfully.")
        
        # 5. Sign and Send (Interactive Confirmation)
        print("\n⚠️  READY TO EXECUTE ON-CHAIN TRANSACTION ⚠️")
        confirm = input(f"Send 1.0 TCRO swap tx? (yes/no): ")
        
        if confirm.lower() != "yes":
            print("Operation cancelled.")
            return

        print("Signing and sending transaction...")
        
        # Prepare transaction with gas
        tx = {
            'to': unsigned_tx['to'],
            'value': unsigned_tx['value'],
            'data': unsigned_tx['data'],
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(address),
            'chainId': chain_id
        }
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"✅ Transaction Sent!")
        print(f"Hash: {tx_hash.hex()}")
        print(f"Explorer: https://explorer.cronos.org/testnet/tx/{tx_hash.hex()}")
        
        print("\nWaiting for receipt...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:
            print("🎉 Swap Successful!")
        else:
            print("❌ Swap Failed (Reverted on chain)")

    except Exception as e:
        print(f"❌ Transaction Execution Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
