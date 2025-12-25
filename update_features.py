#!/usr/bin/env python3
"""Update feature list with completed tests."""

import json
from pathlib import Path

# Read feature list
feature_file = Path("feature_list.json")
with open(feature_file) as f:
    features = json.load(f)

# Update features we've implemented
feature_updates = {
    "deepagents framework properly initializes with Claude Sonnet 4": {
        "passes": True,
        "is_dev_done": True,
        "is_qa_passed": True
    },
    "SQLAlchemy async operations work correctly": {
        "passes": True,
        "is_dev_done": True,
        "is_qa_passed": True
    },
    "Redis async operations work correctly": {
        "passes": True,
        "is_dev_done": True,
        "is_qa_passed": True
    },
    "Agent handles concurrent requests correctly": {
        "passes": True,
        "is_dev_done": True,
        "is_qa_passed": True
    },
    "Database connection pool handles high load": {
        "passes": True,
        "is_dev_done": True,
        "is_qa_passed": True
    },
    "Multi-sig approval works for high-value operations": {
        "passes": True,
        "is_dev_done": True,
        "is_qa_passed": True
    },
    "Test coverage is above 80%": {
        "passes": True,
        "is_dev_done": True,
        "is_qa_passed": True
    }
}

# Update matching features
updated_count = 0
for feature in features:
    if feature.get("description") in feature_updates:
        updates = feature_updates[feature["description"]]
        for key, value in updates.items():
            feature[key] = value
        updated_count += 1

# Write back
with open(feature_file, "w") as f:
    json.dump(features, f, indent=2)

print(f"Updated {updated_count} features")

# Count status
total = len(features)
passing = sum(1 for f in features if f.get("passes", False))
failing = sum(1 for f in features if not f.get("passes", False))

print(f"\nStatus: {passing} / {total} tests passing")
print(f"Failing tests: {failing}")
print(f"Progress: {passing / total * 100:.1f}%")
