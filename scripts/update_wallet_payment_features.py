#!/usr/bin/env python3
"""
Script to mark wallet and payment features as complete.
"""
import json
from pathlib import Path

# Load feature list
feature_file = Path("feature_list.json")
features = json.loads(feature_file.read_text())

# Features to mark as complete (wallet, payments, logs, approvals)
feature_indices = {
    # Wallet features (24-28)
    24: "GET /api/v1/wallet/balance returns token balances",
    25: "Wallet balance supports multiple token queries", 
    26: "GET /api/v1/wallet/allowance returns daily spending allowance",
    27: "POST /api/v1/wallet/transfer executes token transfer",
    28: "GET /api/v1/wallet/transactions returns transaction history",
    
    # Payment features (30-34)
    30: "GET /api/v1/payments/history returns payment history",
    31: "Payment history supports filtering by status",
    32: "Payment history supports date range filtering",
    33: "GET /api/v1/payments/{payment_id} returns payment details",
    34: "POST /api/v1/payments/x402 executes x402 payment flow",
    35: "GET /api/v1/payments/stats returns payment statistics",
    
    # Logs features (39-42)
    39: "GET /api/v1/logs returns execution logs",
    40: "Execution logs support filtering by session_id",
    41: "GET /api/v1/logs/{log_id} returns specific execution log",
    42: "GET /api/v1/logs/{session_id}/summary returns session summary",
    
    # Approvals features (44-50)
    44: "GET /api/v1/approvals/pending lists pending approval requests",
    45: "POST /api/v1/approvals/{request_id}/approve resumes agent execution",
    46: "POST /api/v1/approvals/{request_id}/reject stops agent execution",
    47: "POST /api/v1/approvals/{request_id}/edit allows modifying args before approval",
}

# Update features
updated_count = 0
for idx, description in feature_indices.items():
    if idx < len(features):
        if features[idx]["description"] == description:
            if not features[idx].get("is_dev_done"):
                features[idx]["is_dev_done"] = True
                updated_count += 1
                print(f"✓ Marked as dev done: {description}")

# Save updated feature list
feature_file.write_text(json.dumps(features, indent=2))
print(f"\nUpdated {updated_count} features")

# Calculate stats
total = len(features)
dev_done = sum(1 for f in features if f.get("is_dev_done"))
qa_passed = sum(1 for f in features if f.get("passes"))

print(f"\nProgress: {dev_done}/{total} features complete ({dev_done/total*100:.1f}%)")
print(f"QA Passed: {qa_passed}/{total} features ({qa_passed/total*100:.1f}%)")
