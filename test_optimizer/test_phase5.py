"""
Test script for Phase 5: Test Suite Optimization
"""

import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from data.data_loader import DataLoader
from analysis.duplicate_detector import DuplicateDetector
from flows.coverage_analyzer import CoverageAnalyzer
from optimization.optimization_engine import OptimizationEngine
from optimization.coverage_validator import CoverageValidator
from optimization.test_case_merger import TestCaseMerger
from optimization.optimization_report import OptimizationReportGenerator


def main():
    """Test Phase 5 implementation."""
    # Paths to data directories
    project_root = Path(__file__).parent.parent
    test_cases_dir = project_root / "json-data" / "test_cases"
    steps_dir = project_root / "json-data" / "steps_in_test_cases"
    
    print("=" * 80)
    print("PHASE 5 TEST: Test Suite Optimization")
    print("=" * 80)
    print()
    
    # Load test cases
    print("1. Loading test cases...")
    loader = DataLoader(str(test_cases_dir), str(steps_dir))
    test_cases = loader.load_all()
    print(f"   Loaded {len(test_cases)} test cases")
    print()
    
    # Test Optimization Engine
    print("2. Testing Optimization Engine...")
    optimization_engine = OptimizationEngine(
        min_coverage_percentage=0.90
    )
    
    # Run optimization
    optimization_result = optimization_engine.optimize_test_suite(test_cases)
    
    print(f"   Original test cases: {optimization_result['original_test_cases']}")
    print(f"   Optimized test cases: {optimization_result['optimized_test_cases']}")
    print(f"   Reduction: {optimization_result['reduction']} ({optimization_result['reduction_percentage']:.1f}%)")
    print(f"   Test cases kept: {len(optimization_result['test_cases_kept'])}")
    print(f"   Test cases removed: {len(optimization_result['test_cases_removed'])}")
    print()
    
    # Show coverage comparison
    coverage_before = optimization_result['coverage']['before']
    coverage_after = optimization_result['coverage']['after']
    print(f"   Coverage Before: {coverage_before['coverage_percentage']:.1f}%")
    print(f"   Coverage After: {coverage_after['coverage_percentage']:.1f}%")
    print(f"   Coverage Delta: {coverage_after['coverage_percentage'] - coverage_before['coverage_percentage']:+.1f}%")
    print()
    
    # Show time savings
    time_savings = optimization_result['time_savings']
    print(f"   Time Saved: {time_savings['time_saved_seconds']:.1f} seconds ({time_savings['time_saved_percentage']:.1f}%)")
    print()
    
    # Test Coverage Validator
    print("3. Testing Coverage Validator...")
    coverage_validator = CoverageValidator(min_coverage_percentage=0.90)
    
    # Get optimized test cases
    optimized_test_cases = {
        tid: test_cases[tid] 
        for tid in optimization_result['test_cases_kept']
    }
    
    validation_result = coverage_validator.validate_optimization(
        test_cases,
        optimized_test_cases
    )
    
    print(f"   Validation Status: {'✓ PASSED' if validation_result['is_valid'] else '✗ FAILED'}")
    print(f"   Coverage Maintained: {'✓ Yes' if validation_result['coverage_maintained'] else '✗ No'}")
    print(f"   All Critical Flows Covered: {'✓ Yes' if validation_result['all_critical_covered'] else '✗ No'}")
    
    if validation_result['lost_flows']:
        print(f"   Lost Flows: {', '.join(validation_result['lost_flows'])}")
    if validation_result['lost_critical_flows']:
        print(f"   Lost Critical Flows: {', '.join(validation_result['lost_critical_flows'])}")
    if validation_result['warnings']:
        print(f"   Warnings: {len(validation_result['warnings'])}")
        for warning in validation_result['warnings'][:3]:
            print(f"     - {warning}")
    print()
    
    # Test Test Case Merger
    print("4. Testing Test Case Merger...")
    test_case_merger = TestCaseMerger(merge_threshold=0.70)
    
    merge_candidates = test_case_merger.identify_merge_candidates(test_cases)
    print(f"   Merge candidates found: {len(merge_candidates)}")
    
    if merge_candidates:
        print(f"   Top merge candidate:")
        top_candidate = merge_candidates[0]
        print(f"     Test Case {top_candidate['test_case_1']} + {top_candidate['test_case_2']}")
        print(f"     Similarity: {top_candidate['similarity']:.1%}")
        print(f"     Can Merge: {'✓ Yes' if top_candidate['can_merge'] else '✗ No'}")
        print(f"     Recommendation: {top_candidate['recommendation']}")
    print()
    
    # Test Optimization Report Generator
    print("5. Testing Optimization Report Generator...")
    report_generator = OptimizationReportGenerator()
    
    report = report_generator.generate_report(
        optimization_result,
        test_cases,
        optimized_test_cases
    )
    
    print(f"   Report generated successfully")
    print(f"   Summary:")
    print(f"     Optimization Successful: {report['summary']['optimization_successful']}")
    print(f"     Test Cases Reduced: {report['summary']['test_cases_reduced']}")
    print(f"     Coverage Maintained: {report['summary']['coverage_maintained']}")
    print()
    
    # Generate human-readable report
    human_report = report_generator.generate_human_readable_report(report)
    print("6. Human-Readable Report Preview:")
    print("-" * 80)
    print(human_report[:500] + "..." if len(human_report) > 500 else human_report)
    print()
    
    print("=" * 80)
    print("PHASE 5 TEST COMPLETED")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  - {len(test_cases)} original test cases")
    print(f"  - {len(optimized_test_cases)} optimized test cases")
    print(f"  - {optimization_result['reduction']} test cases removed ({optimization_result['reduction_percentage']:.1f}%)")
    print(f"  - Coverage: {coverage_after['coverage_percentage']:.1f}% (maintained)")
    print(f"  - Time saved: {time_savings['time_saved_seconds']:.1f} seconds")
    print(f"  - Validation: {'✓ PASSED' if validation_result['is_valid'] else '✗ FAILED'}")
    
    return validation_result['is_valid']


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


