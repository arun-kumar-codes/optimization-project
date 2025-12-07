"""
Module for generating similarity matrices between test cases.
"""

from typing import Dict, List
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from analysis.similarity_analyzer import SimilarityAnalyzer


class SimilarityMatrixGenerator:
    """Generates similarity matrices for test case analysis."""
    
    def __init__(self):
        self.similarity_analyzer = SimilarityAnalyzer()
    
    def generate_matrix(
        self, 
        test_cases: Dict[int, TestCase]
    ) -> Dict[int, Dict[int, float]]:
        """
        Generate a similarity matrix for all test cases.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Nested dictionary: {test_case_id1: {test_case_id2: similarity_score, ...}, ...}
        """
        matrix = {}
        test_case_ids = sorted(test_cases.keys())
        
        for i, id1 in enumerate(test_case_ids):
            matrix[id1] = {}
            
            for j, id2 in enumerate(test_case_ids):
                if id1 == id2:
                    # Same test case = 100% similar
                    matrix[id1][id2] = 1.0
                elif id2 in matrix and id1 in matrix[id2]:
                    
                    matrix[id1][id2] = matrix[id2][id1]
                else:
                    # Calculate similarity
                    result = self.similarity_analyzer.calculate_comprehensive_similarity(
                        test_cases[id1],
                        test_cases[id2]
                    )
                    matrix[id1][id2] = result["overall"]
        
        return matrix
    
    def generate_matrix_summary(
        self, 
        matrix: Dict[int, Dict[int, float]]
    ) -> Dict:
        """
        Generate summary statistics from similarity matrix.
        
        Args:
            matrix: Similarity matrix
            
        Returns:
            Dictionary with summary statistics
        """
        all_similarities = []
        high_similarities = []  
        medium_similarities = []  
        low_similarities = [] 
        
        for id1, similarities in matrix.items():
            for id2, sim_score in similarities.items():
                if id1 != id2:  
                    all_similarities.append(sim_score)
                    if sim_score > 0.75:
                        high_similarities.append((id1, id2, sim_score))
                    elif sim_score >= 0.5:
                        medium_similarities.append((id1, id2, sim_score))
                    else:
                        low_similarities.append((id1, id2, sim_score))
        
        return {
            "total_comparisons": len(all_similarities),
            "average_similarity": sum(all_similarities) / len(all_similarities) if all_similarities else 0.0,
            "max_similarity": max(all_similarities) if all_similarities else 0.0,
            "min_similarity": min(all_similarities) if all_similarities else 0.0,
            "high_similarity_count": len(high_similarities),
            "medium_similarity_count": len(medium_similarities),
            "low_similarity_count": len(low_similarities),
            "high_similarity_pairs": sorted(high_similarities, key=lambda x: x[2], reverse=True)[:20], 
            "most_similar_pair": max(high_similarities, key=lambda x: x[2]) if high_similarities else None
        }
    
    def export_matrix_to_json(
        self, 
        matrix: Dict[int, Dict[int, float]],
        output_path: str
    ):
        """
        Export similarity matrix to JSON file.
        
        Args:
            matrix: Similarity matrix
            output_path: Path to output JSON file
        """
        test_case_ids = sorted(matrix.keys())
        
        export_data = {
            "test_case_ids": test_case_ids,
            "matrix": {}
        }
        
        for id1 in test_case_ids:
            export_data["matrix"][str(id1)] = {}
            for id2 in test_case_ids:
                export_data["matrix"][str(id1)][str(id2)] = round(matrix[id1][id2], 4)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
    
    def find_most_similar_pairs(
        self, 
        matrix: Dict[int, Dict[int, float]],
        top_n: int = 10
    ) -> List[tuple]:
        """
        Find the most similar pairs of test cases.
        
        Args:
            matrix: Similarity matrix
            top_n: Number of top pairs to return
            
        Returns:
            List of tuples (id1, id2, similarity) sorted by similarity
        """
        pairs = []
        
        for id1, similarities in matrix.items():
            for id2, sim_score in similarities.items():
                if id1 < id2: 
                    pairs.append((id1, id2, sim_score))
        
        pairs.sort(key=lambda x: x[2], reverse=True)
        
        return pairs[:top_n]
    
    def get_test_case_similarities(
        self, 
        matrix: Dict[int, Dict[int, float]],
        test_case_id: int
    ) -> List[tuple]:
        """
        Get all similarities for a specific test case.
        
        Args:
            matrix: Similarity matrix
            test_case_id: Test case ID to analyze
            
        Returns:
            List of tuples (other_test_case_id, similarity) sorted by similarity
        """
        if test_case_id not in matrix:
            return []
        
        similarities = []
        for other_id, sim_score in matrix[test_case_id].items():
            if other_id != test_case_id:
                similarities.append((other_id, sim_score))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities

