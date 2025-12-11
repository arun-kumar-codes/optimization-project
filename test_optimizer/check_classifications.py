#!/usr/bin/env python3
"""
Diagnostic script to check role and website classifications for test cases.
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data.data_loader import DataLoader
from analysis.role_classifier import RoleClassifier
from analysis.website_grouper import WebsiteGrouper

# Test case IDs to check
test_case_ids_to_check = [1, 6, 7, 8, 9, 10, 11, 15, 16, 18, 21, 29, 14330]

print("=" * 80)
print("ROLE AND WEBSITE CLASSIFICATION DIAGNOSTIC")
print("=" * 80)

# Load test cases
script_dir = Path(__file__).parent
test_cases_dir = script_dir / "json-data" / "test_cases"
steps_dir = script_dir / "json-data" / "steps_in_test_cases"

loader = DataLoader(str(test_cases_dir), str(steps_dir))
all_test_cases = loader.load_all()

# Filter to only the ones we want to check
test_cases = {tc_id: all_test_cases[tc_id] for tc_id in test_case_ids_to_check if tc_id in all_test_cases}

print(f"\n✓ Loaded {len(test_cases)}/{len(test_case_ids_to_check)} requested test cases")
for tc_id, tc in test_cases.items():
    print(f"  TC {tc_id}: {tc.name[:60]}")

if not test_cases:
    print("\n❌ No test cases loaded. Exiting.")
    sys.exit(1)

print(f"\n{'=' * 80}")
print(f"Loaded {len(test_cases)} test cases")
print("=" * 80)

# Classify roles
print("\n" + "=" * 80)
print("ROLE CLASSIFICATIONS")
print("=" * 80)

role_classifier = RoleClassifier()
role_classifications = role_classifier.classify_test_cases(test_cases)

for tc_id, tc in test_cases.items():
    role = role_classifications.get(tc_id, "unknown")
    confidence = role_classifier.get_role_confidence(tc)
    print(f"\nTC {tc_id:5d}: {tc.name[:50]:50s}")
    print(f"  Role: {role:8s} (admin: {confidence['admin_confidence']:.2f}, user: {confidence['user_confidence']:.2f})")
    if 'indicators' in confidence:
        indicators = confidence['indicators']
        print(f"  Admin indicators: {indicators.get('admin', {}).get('total', 0)}")
        print(f"  User indicators: {indicators.get('user', {}).get('total', 0)}")

# Extract websites
print("\n" + "=" * 80)
print("WEBSITE CLASSIFICATIONS")
print("=" * 80)

website_grouper = WebsiteGrouper()

for tc_id, tc in test_cases.items():
    website = website_grouper.extract_website(tc)
    # Get URLs from steps
    urls = website_grouper._extract_urls_from_steps(tc.steps)
    first_url = urls[0] if urls else "No URL found"
    print(f"\nTC {tc_id:5d}: {tc.name[:50]:50s}")
    print(f"  Website: {website}")
    print(f"  First URL: {first_url[:70]}")

# Group by role and website
print("\n" + "=" * 80)
print("GROUPING BY (ROLE, WEBSITE)")
print("=" * 80)

role_website_groups = website_grouper.group_by_role_and_website(
    test_cases,
    role_classifications
)

for (role, website), tc_ids in sorted(role_website_groups.items()):
    print(f"\nGroup: ({role}, {website})")
    print(f"  Test Cases: {tc_ids}")
    print(f"  Count: {len(tc_ids)}")
    if len(tc_ids) < 3:
        print(f"  ⚠️  TOO SMALL for multi-merge (needs 3+, has {len(tc_ids)})")
    else:
        print(f"  ✓ Large enough for multi-merge")

# Check mergeable groups
print("\n" + "=" * 80)
print("MERGEABLE GROUPS (within each role+website group)")
print("=" * 80)

from analysis.prefix_analyzer import PrefixAnalyzer
prefix_analyzer = PrefixAnalyzer()

for (role, website), tc_ids in sorted(role_website_groups.items()):
    if len(tc_ids) < 2:
        continue
    
    group_test_cases = {tid: test_cases[tid] for tid in tc_ids if tid in test_cases}
    
    print(f"\nGroup: ({role}, {website}) - {len(group_test_cases)} test cases")
    
    # Check with min_group_size=2 (for pairs)
    mergeable_groups = prefix_analyzer.find_mergeable_groups(
        group_test_cases,
        min_prefix_length=1,  # Lower threshold
        min_group_size=2,     # Allow pairs
        use_flexible_login=True
    )
    
    if mergeable_groups:
        for mg in mergeable_groups:
            print(f"  ✓ Mergeable group: TC {mg['test_case_ids']}")
            print(f"    Prefix: {mg['prefix_actions'][:5]}... ({mg['prefix_length']} steps)")
            print(f"    Has login pattern: {mg.get('has_login_pattern', False)}")
    else:
        print(f"  ✗ No mergeable groups found")
        # Check why - show prefix analysis
        if len(group_test_cases) >= 2:
            tc_list = list(group_test_cases.values())
            merge_points = prefix_analyzer.identify_flexible_merge_points(tc_list[:2])
            print(f"    First 2 test cases:")
            print(f"      Prefix length: {merge_points['prefix_length']}")
            print(f"      Has login: {merge_points.get('has_login', False)}")
            print(f"      Prefix actions: {merge_points.get('prefix_actions', [])[:5]}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print(f"\nTotal test cases analyzed: {len(test_cases)}")
print(f"Role groups: {len(set(role_classifications.values()))}")
print(f"Website groups: {len(set(website_grouper.extract_website(tc) for tc in test_cases.values()))}")
print(f"(Role, Website) groups: {len(role_website_groups)}")

print("\n" + "=" * 80)

