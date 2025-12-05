"""
Test script for Phase 1: Data Extraction and Preprocessing
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from data.data_loader import DataLoader
from data.validator import DataValidator


def main():
    """Test Phase 1 implementation."""
    # Paths to data directories (relative to project root)
    project_root = Path(__file__).parent.parent
    test_cases_dir = project_root / "json-data" / "test_cases"
    steps_dir = project_root / "json-data" / "steps_in_test_cases"
    
    print("=" * 80)
    print("PHASE 1 TEST: Data Extraction and Preprocessing")
    print("=" * 80)
    print()
    
    # Initialize data loader
    print("1. Initializing Data Loader...")
    loader = DataLoader(str(test_cases_dir), str(steps_dir))
    print(f"   Test cases directory: {test_cases_dir}")
    print(f"   Steps directory: {steps_dir}")
    print()
    
    # Load all test cases
    print("2. Loading all test cases...")
    test_cases = loader.load_all()
    print(f"   Loaded {len(test_cases)} test cases")
    
    # Show load summary
    summary = loader.get_load_summary()
    print(f"   Total steps loaded: {summary['total_steps_loaded']}")
    if summary['load_errors'] > 0:
        print(f"   Load errors: {summary['load_errors']}")
        for test_id, error in summary['error_details']:
            print(f"     - Test Case {test_id}: {error}")
    print()
    
    # Validate test cases
    print("3. Validating test cases...")
    validator = DataValidator()
    validation_result = validator.validate_all(test_cases)
    
    print(f"   Valid test cases: {validation_result['valid_test_cases']}")
    print(f"   Invalid test cases: {validation_result['invalid_test_cases']}")
    print(f"   Total errors: {validation_result['total_errors']}")
    print(f"   Total warnings: {validation_result['total_warnings']}")
    print()
    
    # Show sample test case
    if test_cases:
        print("4. Sample Test Case:")
        sample_id = list(test_cases.keys())[0]
        sample_tc = test_cases[sample_id]
        print(f"   ID: {sample_tc.id}")
        print(f"   Name: {sample_tc.name}")
        print(f"   Status: {sample_tc.status}")
        print(f"   Priority: {sample_tc.priority}")
        print(f"   Steps: {len(sample_tc.steps)}")
        print(f"   Duration: {sample_tc.duration}ms" if sample_tc.duration else "   Duration: N/A")
        print(f"   Pass Count: {sample_tc.pass_count}" if sample_tc.pass_count else "   Pass Count: N/A")
        print(f"   Fail Count: {sample_tc.fail_count}" if sample_tc.fail_count else "   Fail Count: N/A")
        
        if sample_tc.steps:
            print(f"   First 3 steps:")
            for i, step in enumerate(sample_tc.steps[:3], 1):
                print(f"     {i}. Position {step.position}: {step.action_name} - {step.action[:50]}")
        print()
    
    # Generate validation report
    print("5. Validation Report:")
    print("-" * 80)
    report = validator.generate_validation_report(validation_result)
    print(report)
    
    print()
    print("=" * 80)
    print("PHASE 1 TEST COMPLETED")
    print("=" * 80)
    
    return len(test_cases) > 0 and validation_result['invalid_test_cases'] == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

