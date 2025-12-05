"""
Test script for Phase 3: User Flow Modeling
"""

import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from data.data_loader import DataLoader
from flows.flow_analyzer import FlowAnalyzer
from flows.flow_graph import FlowGraphBuilder
from flows.coverage_analyzer import CoverageAnalyzer
from flows.flow_classifier import FlowClassifier


def main():
    """Test Phase 3 implementation."""
    # Paths to data directories
    project_root = Path(__file__).parent.parent
    test_cases_dir = project_root / "json-data" / "test_cases"
    steps_dir = project_root / "json-data" / "steps_in_test_cases"
    
    print("=" * 80)
    print("PHASE 3 TEST: User Flow Modeling")
    print("=" * 80)
    print()
    
    # Load test cases
    print("1. Loading test cases...")
    loader = DataLoader(str(test_cases_dir), str(steps_dir))
    test_cases = loader.load_all()
    print(f"   Loaded {len(test_cases)} test cases")
    print()
    
    # Test Flow Analyzer
    print("2. Testing Flow Analyzer...")
    flow_analyzer = FlowAnalyzer()
    
    # Analyze a sample test case
    sample_id = list(test_cases.keys())[0]
    sample_tc = test_cases[sample_id]
    
    flow_types = flow_analyzer.identify_flow_type(sample_tc)
    print(f"   Sample Test Case {sample_id} flow types: {flow_types}")
    
    boundaries = flow_analyzer.extract_flow_boundaries(sample_tc)
    print(f"   Flow boundaries: {boundaries}")
    
    transitions = flow_analyzer.extract_page_transitions(sample_tc)
    print(f"   Page transitions: {len(transitions)}")
    if transitions:
        print(f"   First transition: {transitions[0]}")
    print()
    
    # Test Flow Graph Builder
    print("3. Testing Flow Graph Builder...")
    graph_builder = FlowGraphBuilder()
    graph = graph_builder.build_graph(test_cases)
    
    print(f"   Graph nodes (pages): {graph.number_of_nodes()}")
    print(f"   Graph edges (transitions): {graph.number_of_edges()}")
    
    coverage_info = graph_builder.find_flow_coverage(graph)
    print(f"   High frequency pages: {coverage_info['high_frequency_pages']}")
    print(f"   High frequency transitions: {coverage_info['high_frequency_transitions']}")
    
    critical_paths = graph_builder.identify_critical_paths(graph, top_n=5)
    if critical_paths:
        print(f"   Top critical path: {critical_paths[0]['from']} -> {critical_paths[0]['to']} (weight: {critical_paths[0]['weight']})")
    print()
    
    # Test Coverage Analyzer
    print("4. Testing Coverage Analyzer...")
    coverage_analyzer = CoverageAnalyzer()
    
    flow_coverage = coverage_analyzer.calculate_flow_coverage(test_cases)
    print(f"   Total unique flows: {flow_coverage['total_unique_flows']}")
    print(f"   Covered flows: {flow_coverage['covered_flows']}")
    print(f"   Coverage percentage: {flow_coverage['coverage_percentage']:.1f}%")
    print(f"   Flows: {flow_coverage['all_flows']}")
    
    critical_coverage = coverage_analyzer.identify_critical_flow_coverage(test_cases)
    print(f"   All critical flows covered: {critical_coverage['all_critical_covered']}")
    for flow, info in critical_coverage['coverage'].items():
        status = "✓" if info['covered'] else "✗"
        print(f"   {status} {flow}: {info['test_case_count']} test cases")
    
    gaps = coverage_analyzer.find_coverage_gaps(test_cases)
    print(f"   Coverage gaps found: {len(gaps)}")
    if gaps:
        print(f"   First gap: {gaps[0]['type']} - {gaps[0]['description']}")
    print()
    
    # Test Flow Classifier
    print("5. Testing Flow Classifier...")
    classifier = FlowClassifier()
    
    classification = classifier.classify_test_case(sample_tc)
    print(f"   Sample Test Case {sample_id} classification:")
    print(f"     Primary flow: {classification['primary_flow']}")
    print(f"     Primary category: {classification['primary_category']}")
    print(f"     Secondary flows: {classification['secondary_flows']}")
    print(f"     Multi-flow: {classification['is_multi_flow']}")
    
    all_classifications = classifier.classify_all_test_cases(test_cases)
    print(f"   Category distribution:")
    for category, count in all_classifications['summary']['categories'].items():
        print(f"     {category}: {count} test cases")
    print(f"   Multi-flow test cases: {all_classifications['summary']['multi_flow_count']}")
    print()
    
    # Generate comprehensive coverage report
    print("6. Generating Comprehensive Coverage Report...")
    report = coverage_analyzer.generate_coverage_report(test_cases)
    summary = report['summary']
    print(f"   Summary:")
    print(f"     Total test cases: {summary['total_test_cases']}")
    print(f"     Total flows: {summary['total_flows']}")
    print(f"     Coverage: {summary['coverage_percentage']:.1f}%")
    print(f"     All critical covered: {summary['all_critical_covered']}")
    print(f"     Total gaps: {summary['total_gaps']}")
    print()
    
    print("=" * 80)
    print("PHASE 3 TEST COMPLETED")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  - {len(test_cases)} test cases analyzed")
    print(f"  - {flow_coverage['total_unique_flows']} unique flows identified")
    print(f"  - {flow_coverage['coverage_percentage']:.1f}% flow coverage")
    print(f"  - {graph.number_of_nodes()} pages in flow graph")
    print(f"  - {graph.number_of_edges()} transitions in flow graph")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

