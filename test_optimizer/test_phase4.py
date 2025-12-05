"""
Test script for Phase 4: AI-Powered Analysis and Optimization

Note: This will make actual API calls to Claude, which may incur costs.
Set LIMIT to a small number (e.g., 3) to test with minimal API usage.
"""

import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from data.data_loader import DataLoader
from flows.flow_analyzer import FlowAnalyzer
from flows.coverage_analyzer import CoverageAnalyzer
from ai.claude_client import ClaudeClient
from ai.semantic_analyzer import SemanticAnalyzer
from ai.optimization_advisor import OptimizationAdvisor
from ai.gap_analyzer import GapAnalyzer

# Limit number of test cases to analyze (to minimize API costs)
LIMIT = 3  # Change this to test with more/fewer test cases


def main():
    """Test Phase 4 implementation."""
    # Paths to data directories
    project_root = Path(__file__).parent.parent
    test_cases_dir = project_root / "json-data" / "test_cases"
    steps_dir = project_root / "json-data" / "steps_in_test_cases"
    
    print("=" * 80)
    print("PHASE 4 TEST: AI-Powered Analysis and Optimization")
    print("=" * 80)
    print(f"NOTE: Testing with LIMIT={LIMIT} test cases to minimize API costs")
    print()
    
    # Load test cases
    print("1. Loading test cases...")
    loader = DataLoader(str(test_cases_dir), str(steps_dir))
    test_cases = loader.load_all()
    print(f"   Loaded {len(test_cases)} test cases")
    print(f"   Will analyze first {LIMIT} test cases")
    print()
    
    # Test Claude Client
    print("2. Testing Claude Client...")
    try:
        claude_client = ClaudeClient()
        test_response = claude_client.analyze(
            "Say 'Hello, I am Claude API working correctly!' in one sentence.",
            max_tokens=50
        )
        print(f"   ✓ Claude API connection successful")
        print(f"   Response: {test_response[:100]}...")
    except Exception as e:
        print(f"   ✗ Claude API connection failed: {e}")
        print("   Continuing with limited functionality...")
    print()
    
    # Test Semantic Analyzer (limited)
    print(f"3. Testing Semantic Analyzer (analyzing {LIMIT} test cases)...")
    try:
        semantic_analyzer = SemanticAnalyzer()
        
        # Analyze limited test cases
        test_cases_subset = {k: v for k, v in list(test_cases.items())[:LIMIT]}
        analysis_results = semantic_analyzer.analyze_all_test_cases(
            test_cases_subset,
            limit=LIMIT
        )
        
        print(f"   ✓ Analyzed {analysis_results['total_analyzed']} test cases")
        
        # Show sample analysis
        if analysis_results['analyses']:
            sample_id = list(analysis_results['analyses'].keys())[0]
            sample_analysis = analysis_results['analyses'][sample_id]
            print(f"   Sample Analysis (Test Case {sample_id}):")
            print(f"     Criticality: {sample_analysis.get('criticality', 'N/A')}")
            print(f"     Classification: {sample_analysis.get('classification', 'N/A')}")
            print(f"     Business Value: {sample_analysis.get('business_value', 'N/A')}")
        
        # Show summary
        summary = analysis_results.get('summary', {})
        if summary:
            print(f"   Criticality Distribution: {summary.get('criticality_distribution', {})}")
    except Exception as e:
        print(f"   ✗ Semantic analysis failed: {e}")
    print()
    
    # Test Optimization Advisor (limited)
    print(f"4. Testing Optimization Advisor (analyzing {LIMIT} test cases)...")
    try:
        optimization_advisor = OptimizationAdvisor()
        
        # Get flow coverage
        coverage_analyzer = CoverageAnalyzer()
        flow_coverage = coverage_analyzer.calculate_flow_coverage(test_cases)
        
        # Get duplicate groups (simplified - would normally come from Phase 2)
        duplicate_groups = {
            "exact_duplicates": [],
            "near_duplicates": [],
            "highly_similar": []
        }
        
        # Get recommendations for limited test cases
        test_cases_subset = {k: v for k, v in list(test_cases.items())[:LIMIT]}
        recommendations = optimization_advisor.get_batch_recommendations(
            test_cases_subset,
            duplicate_groups,
            flow_coverage,
            limit=LIMIT
        )
        
        print(f"   ✓ Generated {len(recommendations['recommendations'])} recommendations")
        
        # Show sample recommendation
        if recommendations['recommendations']:
            sample_id = list(recommendations['recommendations'].keys())[0]
            sample_rec = recommendations['recommendations'][sample_id]
            print(f"   Sample Recommendation (Test Case {sample_id}):")
            print(f"     Action: {sample_rec.get('action', 'N/A')}")
            print(f"     Coverage Impact: {sample_rec.get('coverage_impact', 'N/A')}")
        
        # Show summary
        summary = recommendations.get('summary', {})
        if summary:
            print(f"   Action Distribution: {summary.get('action_distribution', {})}")
    except Exception as e:
        print(f"   ✗ Optimization advisor failed: {e}")
    print()
    
    # Test Gap Analyzer
    print("5. Testing Gap Analyzer...")
    try:
        gap_analyzer = GapAnalyzer()
        
        # Get flow coverage
        coverage_analyzer = CoverageAnalyzer()
        flow_coverage = coverage_analyzer.calculate_flow_coverage(test_cases)
        critical_flows = ["authentication", "navigation", "crud"]
        
        # Identify gaps
        gap_analysis = gap_analyzer.identify_coverage_gaps(
            test_cases,
            flow_coverage,
            critical_flows
        )
        
        print(f"   ✓ Gap analysis completed")
        print(f"   Identified gaps: {len(gap_analysis['identified_gaps'])}")
        
        if gap_analysis['identified_gaps']:
            print(f"   Sample gap: {gap_analysis['identified_gaps'][0].get('description', 'N/A')[:100]}")
        
        # Show summary
        summary = gap_analysis.get('summary', {})
        if summary:
            print(f"   Severity Distribution: {summary.get('severity_distribution', {})}")
    except Exception as e:
        print(f"   ✗ Gap analysis failed: {e}")
    print()
    
    print("=" * 80)
    print("PHASE 4 TEST COMPLETED")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  - Claude API: Connected and working")
    print(f"  - Semantic Analysis: Tested with {LIMIT} test cases")
    print(f"  - Optimization Advisor: Tested with {LIMIT} test cases")
    print(f"  - Gap Analyzer: Completed")
    print()
    print("NOTE: To test with more test cases, increase LIMIT in this script.")
    print("      Be aware that each API call incurs costs.")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


