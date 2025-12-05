"""
Test script for Phase 2: Similarity Analysis and Duplicate Detection
"""

import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from data.data_loader import DataLoader
from analysis.sequence_extractor import SequenceExtractor
from analysis.similarity_analyzer import SimilarityAnalyzer
from analysis.duplicate_detector import DuplicateDetector
from analysis.similarity_matrix import SimilarityMatrixGenerator


def main():
    """Test Phase 2 implementation."""
    # Paths to data directories
    project_root = Path(__file__).parent.parent
    test_cases_dir = project_root / "json-data" / "test_cases"
    steps_dir = project_root / "json-data" / "steps_in_test_cases"
    
    print("=" * 80)
    print("PHASE 2 TEST: Similarity Analysis and Duplicate Detection")
    print("=" * 80)
    print()
    
    # Load test cases
    print("1. Loading test cases...")
    loader = DataLoader(str(test_cases_dir), str(steps_dir))
    test_cases = loader.load_all()
    print(f"   Loaded {len(test_cases)} test cases")
    print()
    
    # Test Sequence Extractor
    print("2. Testing Sequence Extractor...")
    extractor = SequenceExtractor()
    
    # Get a sample test case
    sample_id = list(test_cases.keys())[0]
    sample_tc = test_cases[sample_id]
    
    action_seq = extractor.extract_action_sequence(sample_tc)
    print(f"   Sample Test Case {sample_id} action sequence:")
    print(f"   {action_seq[:10]}..." if len(action_seq) > 10 else f"   {action_seq}")
    
    flow_pattern = extractor.extract_flow_pattern(sample_tc)
    print(f"   Flow pattern: {flow_pattern[:10]}..." if len(flow_pattern) > 10 else f"   Flow pattern: {flow_pattern}")
    print()
    
    # Test Similarity Analyzer
    print("3. Testing Similarity Analyzer...")
    analyzer = SimilarityAnalyzer()
    
    # Compare first two test cases
    test_ids = sorted(test_cases.keys())[:2]
    if len(test_ids) == 2:
        tc1 = test_cases[test_ids[0]]
        tc2 = test_cases[test_ids[1]]
        
        similarity_result = analyzer.calculate_comprehensive_similarity(tc1, tc2)
        print(f"   Comparing Test Case {test_ids[0]} vs {test_ids[1]}:")
        print(f"   Overall Similarity: {similarity_result['overall']:.2%}")
        print(f"   Sequence Similarity: {similarity_result['sequence_similarity']:.2%}")
        print(f"   LCS Similarity: {similarity_result['lcs_similarity']:.2%}")
        print(f"   Step-level Similarity: {similarity_result['step_level_similarity']:.2%}")
        print(f"   Flow Pattern Similarity: {similarity_result['flow_pattern_similarity']:.2%}")
    print()
    
    # Test Duplicate Detector
    print("4. Testing Duplicate Detector...")
    detector = DuplicateDetector(
        exact_threshold=1.0,
        near_duplicate_threshold=0.90,
        highly_similar_threshold=0.75
    )
    
    duplicates = detector.detect_duplicates(test_cases)
    
    print(f"   Total duplicate groups found: {duplicates['total_groups']}")
    print(f"   Exact duplicates: {len(duplicates['exact_duplicates'])}")
    print(f"   Near duplicates (>90%): {len(duplicates['near_duplicates'])}")
    print(f"   Highly similar (>75%): {len(duplicates['highly_similar'])}")
    print()
    
    # Show some duplicate groups
    if duplicates['near_duplicates']:
        print("   Sample Near Duplicate Group:")
        group = duplicates['near_duplicates'][0]
        print(f"     Test Cases: {group['test_case_ids']}")
        print(f"     Similarity: {group['max_similarity']:.2%}")
        print(f"     Keep: {group['recommended_keep']}")
        print(f"     Remove: {group['recommended_remove']}")
        print(f"     Reason: {group['reason']}")
    elif duplicates['highly_similar']:
        print("   Sample Highly Similar Group:")
        group = duplicates['highly_similar'][0]
        print(f"     Test Cases: {group['test_case_ids']}")
        print(f"     Similarity: {group['max_similarity']:.2%}")
        print(f"     Keep: {group['recommended_keep']}")
        print(f"     Remove: {group['recommended_remove']}")
    print()
    
    # Test Similarity Matrix
    print("5. Testing Similarity Matrix Generator...")
    print("   Generating similarity matrix (this may take a moment)...")
    matrix_gen = SimilarityMatrixGenerator()
    
    # Generate matrix for first 10 test cases (to save time)
    test_cases_subset = {k: v for k, v in list(test_cases.items())[:10]}
    matrix = matrix_gen.generate_matrix(test_cases_subset)
    
    summary = matrix_gen.generate_matrix_summary(matrix)
    print(f"   Matrix generated for {len(test_cases_subset)} test cases")
    print(f"   Average similarity: {summary['average_similarity']:.2%}")
    print(f"   High similarity pairs (>75%): {summary['high_similarity_count']}")
    print(f"   Medium similarity pairs (50-75%): {summary['medium_similarity_count']}")
    print(f"   Low similarity pairs (<50%): {summary['low_similarity_count']}")
    
    if summary['most_similar_pair']:
        pair = summary['most_similar_pair']
        print(f"   Most similar pair: {pair[0]} vs {pair[1]} ({pair[2]:.2%})")
    print()
    
    # Find top similar pairs
    top_pairs = matrix_gen.find_most_similar_pairs(matrix, top_n=5)
    if top_pairs:
        print("   Top 5 Most Similar Pairs:")
        for i, (id1, id2, sim) in enumerate(top_pairs, 1):
            print(f"     {i}. Test Case {id1} vs {id2}: {sim:.2%}")
    print()
    
    print("=" * 80)
    print("PHASE 2 TEST COMPLETED")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  - {len(test_cases)} test cases analyzed")
    print(f"  - {duplicates['total_groups']} duplicate groups identified")
    print(f"  - {len(duplicates['near_duplicates']) + len(duplicates['highly_similar'])} groups with actionable duplicates")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

