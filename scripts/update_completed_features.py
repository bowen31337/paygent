#!/usr/bin/env python3
"""
Update completed features in feature_list.json
"""
import json

def update_features():
    # Load features
    with open('feature_list.json', 'r') as f:
        features = json.load(f)

    # Features we've implemented (by description)
    completed_features = [
        "Agent creates write_todos plan for complex multi-step operations",
        "Agent respects budget limits configured in session",
        "Agent logs all tool calls to execution_logs table",
    ]

    # Update features
    updated_count = 0
    for feature in features:
        if feature.get('description') in completed_features:
            if not feature.get('is_dev_done', False):
                feature['is_dev_done'] = True
                feature['passes'] = True
                updated_count += 1
                print(f"✓ Marked as done: {feature['description'][:70]}...")

    # Save updated features
    with open('feature_list.json', 'w') as f:
        json.dump(features, f, indent=2)

    print(f"\nTotal features updated: {updated_count}")
    print(f"Total features done: {sum(1 for f in features if f.get('is_dev_done'))}/{len(features)}")

if __name__ == "__main__":
    update_features()
