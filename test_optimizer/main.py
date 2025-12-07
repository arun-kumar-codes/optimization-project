#!/usr/bin/env python3
"""
Main orchestrator for Test Case Optimization System.

This script runs all phases of the optimization process and generates output files.
"""

import sys
import argparse
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Get the directory where this script is located (test_optimizer folder)
SCRIPT_DIR = Path(__file__).parent.resolve()

from data.data_loader import DataLoader
from data.validator import DataValidator
from analysis.duplicate_detector import DuplicateDetector
from analysis.step_uniqueness_analyzer import StepUniquenessAnalyzer
from flows.coverage_analyzer import CoverageAnalyzer
from flows.flow_classifier import FlowClassifier
from optimization.optimization_engine import OptimizationEngine
from optimization.coverage_validator import CoverageValidator
from optimization.step_coverage_tracker import StepCoverageTracker
from optimization.optimized_test_case_generator import OptimizedTestCaseGenerator
from optimization.optimization_report import OptimizationReportGenerator
from execution.execution_plan import ExecutionPlanGenerator
from output.output_generator import OutputGenerator
from output.output_validator import OutputValidator


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Test Case Optimization System - Optimize test suites while maintaining coverage"
    )
    # Default paths relative to test_optimizer folder (where json-data now resides)
    default_test_cases = str(SCRIPT_DIR / "json-data" / "test_cases")
    default_steps = str(SCRIPT_DIR / "json-data" / "steps_in_test_cases")
    default_output = str(SCRIPT_DIR / "json-data" / "output")
    
    parser.add_argument(
        "--input-test-cases",
        type=str,
        default=default_test_cases,
        help="Path to test cases directory (default: json-data/test_cases inside test_optimizer folder)"
    )
    parser.add_argument(
        "--input-steps",
        type=str,
        default=default_steps,
        help="Path to steps directory (default: json-data/steps_in_test_cases inside test_optimizer folder)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=default_output,
        help=f"Path to output directory (default: {default_output})"
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=0.90,
        help="Minimum coverage percentage to maintain (default: 0.90 = 90%%)"
    )
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Skip ALL AI analysis (Phase 2b semantic duplicates + Phase 4) to save API costs"
    )
    parser.add_argument(
        "--skip-phase4",
        action="store_true",
        help="Skip Phase 4 AI (optimization recommendations) only - keeps Phase 2b semantic duplicates"
    )
    parser.add_argument(
        "--ai-limit",
        type=int,
        default=None,
        help="Limit number of test cases for Phase 4 AI analysis (to save costs)"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("TEST CASE OPTIMIZATION SYSTEM")
    print("=" * 80)
    print()
    
    # Phase 1: Data Loading
    print("PHASE 1: Loading Test Cases...")
    loader = DataLoader(args.input_test_cases, args.input_steps)
    test_cases = loader.load_all()
    print(f"✓ Loaded {len(test_cases)} test cases")
    
    # Validate data
    validator = DataValidator()
    validation_result = validator.validate_all(test_cases)
    if validation_result["invalid_test_cases"] > 0:
        print(f"⚠ Warning: {validation_result['invalid_test_cases']} invalid test cases found")
    print()
    
    # Phase 2: Step-Level Analysis
    print("PHASE 2: Analyzing Step-Level Uniqueness and Coverage...")
    step_uniqueness_analyzer = StepUniquenessAnalyzer()
    step_coverage_tracker = StepCoverageTracker()
    
    # Build step coverage map
    coverage_map = step_coverage_tracker.build_step_coverage_map(test_cases)
    step_coverage = step_coverage_tracker.calculate_step_coverage(test_cases)
    print(f"✓ Identified {len(coverage_map)} unique steps")
    print(f"✓ Step coverage: {step_coverage['coverage_percentage']:.1f}%")
    print()
    
    # Phase 2b: Duplicate Detection (Algorithmic + AI Semantic)
    print("PHASE 2b: Detecting Duplicates...")
    duplicate_detector = DuplicateDetector()
    
    # Enable AI semantic detection if AI is available
    ai_semantic_analyzer = None
    use_ai_semantic = False
    if not args.skip_ai:
        try:
            from ai.semantic_analyzer import SemanticAnalyzer
            ai_semantic_analyzer = SemanticAnalyzer()
            use_ai_semantic = True
            duplicate_detector.use_ai_semantic = True
            duplicate_detector.ai_semantic_analyzer = ai_semantic_analyzer
            print("  Using AI for semantic duplicate detection...")
        except Exception as e:
            print(f"  Warning: AI semantic detection unavailable: {e}")
            print("  Using only algorithmic duplicate detection...")
    
    duplicate_groups = duplicate_detector.detect_duplicates(test_cases, use_ai_semantic=use_ai_semantic)
    print(f"✓ Found {duplicate_groups['total_groups']} duplicate groups")
    print(f"  - Exact duplicates: {len(duplicate_groups['exact_duplicates'])}")
    print(f"  - Near duplicates: {len(duplicate_groups['near_duplicates'])}")
    print(f"  - Highly similar: {len(duplicate_groups['highly_similar'])}")
    if use_ai_semantic and duplicate_groups.get('ai_semantic_pairs_found', 0) > 0:
        print(f"  - AI semantic duplicates found: {duplicate_groups['ai_semantic_pairs_found']}")
    print()
    
    # Phase 3: Flow Analysis
    print("PHASE 3: Analyzing User Flows...")
    coverage_analyzer = CoverageAnalyzer()
    flow_coverage = coverage_analyzer.calculate_flow_coverage(test_cases)
    critical_coverage = coverage_analyzer.identify_critical_flow_coverage(test_cases)
    flow_classifier = FlowClassifier()
    flow_classifications = flow_classifier.classify_all_test_cases(test_cases)
    print(f"✓ Identified {flow_coverage['total_unique_flows']} unique flows")
    print(f"✓ Coverage: {flow_coverage['coverage_percentage']:.1f}%")
    print(f"✓ All critical flows covered: {critical_coverage['all_critical_covered']}")
    print()
    
    # Phase 4: AI Analysis (optional - disabled by default for performance)
    ai_recommendations = None
    phase4_enabled = False
    
    # Check if Phase 4 should be enabled
    try:
        from config.ai_config import AIConfig
        phase4_enabled = AIConfig.PHASE4_ENABLED
    except ImportError:
        pass
    
    # Override with command line flags
    if args.skip_ai:
        phase4_enabled = False
    elif args.skip_phase4:
        phase4_enabled = False
    
    if phase4_enabled and not args.skip_ai:
        print("PHASE 4: AI-Powered Analysis (Optimization Recommendations)...")
        try:
            from ai.optimization_advisor import OptimizationAdvisor
            
            optimization_advisor = OptimizationAdvisor()
            
            # Analyze limited test cases if specified
            test_cases_for_ai = test_cases
            if args.ai_limit:
                test_cases_for_ai = {k: v for k, v in list(test_cases.items())[:args.ai_limit]}
                print(f"  Analyzing {args.ai_limit} test cases (limited to save costs)...")
            
            # Get AI recommendations
            ai_recommendations = optimization_advisor.get_batch_recommendations(
                test_cases_for_ai,
                duplicate_groups,
                flow_coverage,
                limit=args.ai_limit
            )
            print(f"✓ AI analysis completed")
            print()
        except Exception as e:
            print(f"⚠ AI analysis failed: {e}")
            print("  Continuing without AI recommendations...")
            print()
    else:
        if args.skip_phase4:
            print("PHASE 4: Skipped (--skip-phase4 flag - optimization recommendations disabled)")
        elif args.skip_ai:
            print("PHASE 4: Skipped (--skip-ai flag)")
        else:
            print("PHASE 4: Skipped (disabled by default for performance - use --enable-phase4 or set AI_PHASE4_ENABLED=true)")
        print()
    
    # Phase 5: Optimization (Iterative with Merging)
    print("PHASE 5: Optimizing Test Suite (Iterative with Merging)...")
    optimization_engine = OptimizationEngine(
        min_coverage_percentage=args.min_coverage,
        min_step_coverage_percentage=0.95
    )
    optimization_result = optimization_engine.optimize_test_suite(
        test_cases,
        ai_recommendations["recommendations"] if ai_recommendations else None,
        use_iterative=True  # Use iterative optimization
    )
    
    # Get optimized test cases (includes kept + merged)
    optimized_test_cases = {
        tid: test_cases[tid] 
        for tid in optimization_result["test_cases_kept"]
        if tid in test_cases
    }
    
    # Add merged test cases (they have new IDs and are TestCase objects)
    if "merged_test_cases_dict" in optimization_result:
        optimized_test_cases.update(optimization_result["merged_test_cases_dict"])
    
    print(f"✓ Optimization completed")
    print(f"  Original: {optimization_result['original_test_cases']} test cases")
    print(f"  Optimized: {optimization_result['optimized_test_cases']} test cases")
    print(f"  Reduction: {optimization_result['reduction']} ({optimization_result['reduction_percentage']:.1f}%)")
    print(f"  Merged: {len(optimization_result.get('test_cases_merged', {}))} test cases merged")
    print(f"  Flow Coverage: {optimization_result['coverage']['after']['coverage_percentage']:.1f}%")
    print(f"  Step Coverage: {optimization_result['coverage']['after']['step_coverage']['coverage_percentage']:.1f}%")
    print()
    
    # Comprehensive Validation
    print("PHASE 5b: Comprehensive Validation...")
    coverage_validator = CoverageValidator(
        min_coverage_percentage=args.min_coverage,
        min_step_coverage_percentage=0.95
    )
    
    # Get final optimized test cases (including merged)
    final_optimized_test_cases = optimized_test_cases.copy()
    # Note: Merged test cases need to be added here from optimization_result
    # They should be included in the optimized_test_cases dict
    
    # Run comprehensive validation
    comprehensive_validation = coverage_validator.comprehensive_validation(
        test_cases,
        final_optimized_test_cases
    )
    
    # Generate validation report
    validation_report = coverage_validator.generate_validation_report(comprehensive_validation)
    print(validation_report)
    print()
    
    if not comprehensive_validation["overall_valid"]:
        print("⚠ Warning: Comprehensive validation found issues!")
        for error in comprehensive_validation["errors"]:
            print(f"  ✗ {error}")
        for warning in comprehensive_validation["warnings"]:
            print(f"  ⚠ {warning}")
    else:
        print("✓ Comprehensive validation passed - all coverage maintained")
    print()
    
    # Generate optimization report
    report_generator = OptimizationReportGenerator()
    optimization_report = report_generator.generate_report(
        optimization_result,
        test_cases,
        optimized_test_cases
    )
    
    # Phase 6: Execution Ordering
    print("PHASE 6: Generating Execution Plan...")
    plan_generator = ExecutionPlanGenerator()
    execution_plan = plan_generator.generate_execution_plan(optimized_test_cases)
    print(f"✓ Execution plan generated")
    print(f"  Estimated time: {execution_plan['summary']['total_execution_time_minutes']:.1f} minutes")
    print(f"  Smoke tests: {execution_plan['summary']['smoke_tests']}")
    print()
    
    # Phase 7: Finalize Optimized Test Cases
    print("PHASE 7: Finalizing Optimized Test Cases...")
    # optimized_test_cases already includes kept + merged test cases
    final_optimized_test_cases = optimized_test_cases
    
    print(f"✓ Final optimized test cases: {len(final_optimized_test_cases)}")
    print(f"  - Kept: {len(optimization_result['test_cases_kept'])}")
    print(f"  - Merged: {len(optimization_result.get('test_cases_merged', {}))}")
    print()
    
    # Phase 8: Output Generation
    print("PHASE 8: Generating Output Files...")
    # Pass original data directory for metadata preservation
    original_data_dir = str(Path(args.input_test_cases).parent)
    output_generator = OutputGenerator(args.output_dir, original_data_dir=original_data_dir)
    
    # Generate optimized test case files (same format as input, with all metadata)
    output_generator.generate_optimized_test_case_files(final_optimized_test_cases, test_cases)
    output_generator.generate_optimized_step_files(final_optimized_test_cases, test_cases)
    
    # Generate separated admin/user files
    output_generator.generate_admin_user_separated_files(optimized_test_cases, optimization_result)
    
    # Generate summary files
    # Removed: generate_optimization_summary (not needed in output)
    # Removed: generate_duplicate_analysis (not needed in output)
    output_generator.generate_execution_order(execution_plan)
    # Removed: generate_user_flows (not needed in output)
    # Removed: generate_recommendations (not needed in output)
    
    print(f"✓ All output files generated in: {args.output_dir}")
    print()
    
    # Validate outputs
    print("Validating Output Files...")
    output_validator = OutputValidator(args.output_dir)
    all_output_ids = list(final_optimized_test_cases.keys())
    validation_results = output_validator.validate_all_outputs(all_output_ids)
    
    if validation_results["all_valid"]:
        print("✓ All output files validated successfully")
    else:
        print("⚠ Some output files have issues:")
        for result_type, result in validation_results.items():
            if result_type != "all_valid" and isinstance(result, dict) and not result.get("valid", True):
                print(f"  {result_type}: {len(result.get('issues', []))} issues")
    print()
    
    # Final summary
    print("=" * 80)
    print("OPTIMIZATION COMPLETE")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  Original Test Cases: {optimization_result['original_test_cases']}")
    print(f"  Optimized Test Cases: {optimization_result['optimized_test_cases']}")
    print(f"  Reduction: {optimization_result['reduction']} ({optimization_result['reduction_percentage']:.1f}%)")
    print(f"  Merged Test Cases: {len(optimization_result.get('test_cases_merged', {}))}")
    print(f"  Flow Coverage: {optimization_result['coverage']['after']['coverage_percentage']:.1f}%")
    print(f"  Step Coverage: {optimization_result['coverage']['after']['step_coverage']['coverage_percentage']:.1f}%")
    print(f"  Time Saved: {optimization_result['time_savings']['time_saved_seconds']:.1f} seconds")
    print(f"  Comprehensive Validation: {'✓ PASSED' if comprehensive_validation['overall_valid'] else '✗ FAILED'}")
    print()
    print(f"Output Files Location: {args.output_dir}")
    print("  - test_cases/ - Optimized test case files (same format as input)")
    print("  - steps_in_test_cases/ - Optimized step files (same format as input)")
    print("  - admin_optimized_tests.json - Admin test case IDs")
    print("  - user_optimized_tests.json - User test case IDs")
    print("  - execution_order.json - Execution plan")
    print()
    
    return 0 if validation_results["all_valid"] else 1


if __name__ == "__main__":
    sys.exit(main())

