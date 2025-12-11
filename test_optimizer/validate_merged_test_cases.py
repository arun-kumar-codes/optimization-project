#!/usr/bin/env python3
"""
Script to validate all merged test cases before pushing to API.
Checks flow correctness, step consistency, and execution-breaking issues.
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data.data_loader import DataLoader
from validation.merged_test_case_validator import MergedTestCaseValidator


def load_merged_test_cases(output_dir: Path):
    """Load merged test cases from output directory."""
    test_cases_dir = output_dir / "test_cases"
    steps_dir = output_dir / "steps_in_test_cases"
    
    loader = DataLoader(
        test_cases_dir=str(test_cases_dir),
        steps_dir=str(steps_dir)
    )
    return loader.load_all()


def identify_merged_test_cases(test_cases: dict) -> list:
    """Identify which test cases are merged (by name patterns or ID ranges)."""
    merged = []
    for tc_id, tc in test_cases.items():
        # Merged test cases have IDs > 10000 or names containing "Merged" or "Consolidated"
        name_lower = (tc.name or "").lower()
        is_merged_by_name = "merged" in name_lower or "consolidated" in name_lower
        is_merged_by_id = tc_id > 10000  # Merged test cases get IDs in 10000+ range
        
        if is_merged_by_name or is_merged_by_id:
            merged.append(tc_id)
    return merged


def load_source_test_cases(merged_tc: dict, original_test_cases: dict) -> list:
    """Load source test cases for a merged test case."""
    source_ids = []
    
    # Try to extract from raw_data first
    if merged_tc.raw_data and isinstance(merged_tc.raw_data, dict):
        source_ids = merged_tc.raw_data.get("source_test_cases", [])
        if not source_ids and "merged_from" in merged_tc.raw_data:
            merged_from = merged_tc.raw_data.get("merged_from", [])
            if merged_from and isinstance(merged_from[0], dict):
                source_ids = [m.get("id") for m in merged_from if isinstance(m, dict) and "id" in m]
    
    # If not in raw_data, try to extract from description
    if not source_ids and merged_tc.description:
        import re
        # Look for patterns like "(ID: 1)", "(ID: 11)", etc.
        id_matches = re.findall(r'\(ID:\s*(\d+)\)', merged_tc.description)
        if id_matches:
            source_ids = [int(id_str) for id_str in id_matches]
    
    # If still not found, try to extract from name
    if not source_ids and merged_tc.name:
        import re
        # Look for patterns like "TC[1, 37, 38]" or "1+37+38"
        name = merged_tc.name
        # Try "TC[...]" pattern
        tc_pattern = re.search(r'TC\[([\d,\s]+)\]', name)
        if tc_pattern:
            source_ids = [int(x.strip()) for x in tc_pattern.group(1).split(',')]
        else:
            # Try "+" separated pattern
            plus_pattern = re.search(r'(\d+)\+(\d+)', name)
            if plus_pattern:
                source_ids = [int(plus_pattern.group(1)), int(plus_pattern.group(2))]
    
    source_test_cases = []
    for sid in source_ids:
        if sid in original_test_cases:
            source_test_cases.append(original_test_cases[sid])
    
    return source_test_cases


def main():
    """Main validation function."""
    print("="*80)
    print("COMPREHENSIVE VALIDATION OF MERGED TEST CASES")
    print("="*80)
    
    # Try to load original test cases (may not exist if running on output only)
    print("\n[1/4] Loading original test cases...")
    original_test_cases = {}
    
    # Try multiple possible locations
    possible_input_dirs = [
        "json-data/input",
        "../json-data/input",
        "json-data",
    ]
    
    for input_base in possible_input_dirs:
        input_tc_dir = Path(input_base) / "test_cases"
        input_steps_dir = Path(input_base) / "steps_in_test_cases"
        if input_tc_dir.exists() and input_steps_dir.exists():
            try:
                original_loader = DataLoader(
                    test_cases_dir=str(input_tc_dir),
                    steps_dir=str(input_steps_dir)
                )
                original_test_cases = original_loader.load_all()
                print(f"    ✓ Loaded {len(original_test_cases)} original test cases from {input_base}")
                break
            except Exception as e:
                print(f"    ⚠ Could not load from {input_base}: {e}")
                continue
    
    if not original_test_cases:
        print(f"    ⚠ No original test cases found - will validate merged test cases standalone")
    
    # Load optimized/merged test cases
    print("\n[2/4] Loading optimized test cases...")
    output_dir = Path("json-data/output")
    optimized_test_cases = load_merged_test_cases(output_dir)
    print(f"    ✓ Loaded {len(optimized_test_cases)} optimized test cases")
    
    # Identify merged test cases
    print("\n[3/4] Identifying merged test cases...")
    merged_ids = identify_merged_test_cases(optimized_test_cases)
    print(f"    ✓ Found {len(merged_ids)} merged test cases: {merged_ids}")
    
    if not merged_ids:
        print("\n    ⚠️  No merged test cases found. Nothing to validate.")
        return
    
    # Validate each merged test case
    print("\n[4/4] Validating merged test cases...")
    print("="*80)
    
    validator = MergedTestCaseValidator()
    all_passed = True
    results = {}
    
    for merged_id in merged_ids:
        merged_tc = optimized_test_cases[merged_id]
        source_tcs = load_source_test_cases(merged_tc, original_test_cases)
        
        if not source_tcs:
            print(f"\n⚠️  TC {merged_id}: Could not load source test cases")
            print(f"  Will perform standalone validation (without source comparison)")
            # Perform standalone validation
            result = validator.validate_merged_test_case_standalone(merged_tc)
            results[merged_id] = result
            if result["passed"]:
                print(f"  ✓ PASSED (standalone) - {result['summary']}")
            else:
                print(f"  ❌ FAILED (standalone) - {result['summary']}")
                all_passed = False
            continue
        
        print(f"\nValidating TC {merged_id} (merged from {len(source_tcs)} test cases)...")
        print(f"  Name: {merged_tc.name[:60]}...")
        print(f"  Steps: {len(merged_tc.steps)}")
        
        result = validator.validate_merged_test_case(merged_tc, source_tcs)
        results[merged_id] = result
        
        if result["passed"]:
            print(f"  ✓ PASSED - {result['summary']}")
        else:
            print(f"  ❌ FAILED - {result['summary']}")
            all_passed = False
            
            # Print issues
            if result.get("issues"):
                print(f"  Issues:")
                for issue in result["issues"][:5]:  # First 5 issues
                    print(f"    - {issue}")
            
            # Print validation details
            for check_name, check_result in result.items():
                if isinstance(check_result, dict) and not check_result.get("passed", True):
                    print(f"  ❌ {check_name}: {check_result.get('issue', 'Failed')}")
        
        # Print warnings
        if result.get("warnings"):
            print(f"  Warnings:")
            for warning in result["warnings"][:3]:  # First 3 warnings
                print(f"    ⚠️  {warning}")
    
    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    passed_count = sum(1 for r in results.values() if r["passed"])
    failed_count = len(results) - passed_count
    
    print(f"Total merged test cases validated: {len(results)}")
    print(f"✓ Passed: {passed_count}")
    print(f"❌ Failed: {failed_count}")
    
    if all_passed:
        print("\n✅ ALL MERGED TEST CASES PASSED VALIDATION")
        print("   Ready to push to ContextQA API")
        return 0
    else:
        print("\n❌ SOME MERGED TEST CASES FAILED VALIDATION")
        print("   Please fix issues before pushing to API")
        
        # Print failed test cases
        print("\nFailed test cases:")
        for merged_id, result in results.items():
            if not result["passed"]:
                print(f"  - TC {merged_id}: {result['summary']}")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())

