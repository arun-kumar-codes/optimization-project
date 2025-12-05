"""
Module for calculating similarity between test cases using multiple algorithms.
"""

from typing import Dict, Tuple, List
from Levenshtein import distance as levenshtein_distance
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from analysis.sequence_extractor import SequenceExtractor


class SimilarityAnalyzer:
    """Analyzes similarity between test cases using multiple techniques."""
    
    def __init__(self):
        self.sequence_extractor = SequenceExtractor()
    
    def calculate_sequence_similarity(
        self, 
        test_case1: TestCase, 
        test_case2: TestCase
    ) -> float:
        """
        Calculate similarity based on action sequences using Levenshtein distance.
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            
        Returns:
            Similarity score from 0.0 to 1.0 (1.0 = identical)
        """
        seq1 = self.sequence_extractor.extract_action_sequence(test_case1)
        seq2 = self.sequence_extractor.extract_action_sequence(test_case2)
        
        if not seq1 and not seq2:
            return 1.0
        if not seq1 or not seq2:
            return 0.0
        
        # Convert sequences to strings for Levenshtein
        str1 = " ".join(seq1)
        str2 = " ".join(seq2)
        
        # Calculate Levenshtein distance
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 1.0
        
        distance = levenshtein_distance(str1, str2)
        similarity = 1.0 - (distance / max_len)
        
        return max(0.0, similarity)
    
    def calculate_lcs_similarity(
        self, 
        test_case1: TestCase, 
        test_case2: TestCase
    ) -> Tuple[float, int]:
        """
        Calculate similarity using Longest Common Subsequence (LCS).
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            
        Returns:
            Tuple of (similarity_score, lcs_length)
        """
        seq1 = self.sequence_extractor.extract_action_sequence(test_case1)
        seq2 = self.sequence_extractor.extract_action_sequence(test_case2)
        
        similarity, lcs_length = self.sequence_extractor.compare_sequences(seq1, seq2)
        return similarity, lcs_length
    
    def calculate_step_level_similarity(
        self, 
        test_case1: TestCase, 
        test_case2: TestCase
    ) -> float:
        """
        Calculate similarity by comparing individual steps.
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            
        Returns:
            Similarity score from 0.0 to 1.0
        """
        steps1 = sorted(test_case1.steps, key=lambda s: s.position)
        steps2 = sorted(test_case2.steps, key=lambda s: s.position)
        
        if not steps1 and not steps2:
            return 1.0
        if not steps1 or not steps2:
            return 0.0
        
        # Compare steps pairwise
        max_steps = max(len(steps1), len(steps2))
        matches = 0
        
        for i in range(min(len(steps1), len(steps2))):
            step1 = steps1[i]
            step2 = steps2[i]
            
            # Compare action name
            if step1.action_name == step2.action_name:
                matches += 0.4
            
            # Compare element
            if step1.element and step2.element:
                if step1.element.lower() == step2.element.lower():
                    matches += 0.3
            elif not step1.element and not step2.element:
                matches += 0.3
            
            # Compare description (fuzzy)
            if step1.description and step2.description:
                desc_sim = self._fuzzy_string_similarity(
                    step1.description, 
                    step2.description
                )
                matches += desc_sim * 0.3
        
        similarity = matches / max_steps if max_steps > 0 else 0.0
        return min(1.0, similarity)
    
    def calculate_flow_pattern_similarity(
        self, 
        test_case1: TestCase, 
        test_case2: TestCase
    ) -> float:
        """
        Calculate similarity based on abstracted flow patterns.
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            
        Returns:
            Similarity score from 0.0 to 1.0
        """
        pattern1 = self.sequence_extractor.extract_flow_pattern(test_case1)
        pattern2 = self.sequence_extractor.extract_flow_pattern(test_case2)
        
        similarity, _ = self.sequence_extractor.compare_sequences(pattern1, pattern2)
        return similarity
    
    def calculate_comprehensive_similarity(
        self, 
        test_case1: TestCase, 
        test_case2: TestCase,
        weights: Dict[str, float] = None
    ) -> Dict[str, float]:
        """
        Calculate comprehensive similarity using multiple methods.
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            weights: Optional weights for different similarity methods
            
        Returns:
            Dictionary with similarity scores for each method and overall score
        """
        if weights is None:
            weights = {
                "sequence": 0.3,
                "lcs": 0.3,
                "step_level": 0.2,
                "flow_pattern": 0.2
            }
        
        # Calculate individual similarities
        seq_sim = self.calculate_sequence_similarity(test_case1, test_case2)
        lcs_sim, _ = self.calculate_lcs_similarity(test_case1, test_case2)
        step_sim = self.calculate_step_level_similarity(test_case1, test_case2)
        flow_sim = self.calculate_flow_pattern_similarity(test_case1, test_case2)
        
        # Calculate weighted overall similarity
        overall = (
            seq_sim * weights["sequence"] +
            lcs_sim * weights["lcs"] +
            step_sim * weights["step_level"] +
            flow_sim * weights["flow_pattern"]
        )
        
        return {
            "overall": overall,
            "sequence_similarity": seq_sim,
            "lcs_similarity": lcs_sim,
            "step_level_similarity": step_sim,
            "flow_pattern_similarity": flow_sim
        }
    
    def _fuzzy_string_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate fuzzy string similarity using Levenshtein distance.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score from 0.0 to 1.0
        """
        if not str1 and not str2:
            return 1.0
        if not str1 or not str2:
            return 0.0
        
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()
        
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 1.0
        
        distance = levenshtein_distance(str1, str2)
        similarity = 1.0 - (distance / max_len)
        
        return max(0.0, similarity)
    
    def find_similar_test_cases(
        self, 
        test_cases: Dict[int, TestCase],
        threshold: float = 0.75
    ) -> List[Tuple[int, int, float]]:
        """
        Find pairs of similar test cases above a threshold.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            threshold: Minimum similarity score to consider (0.0 to 1.0)
            
        Returns:
            List of tuples (test_case_id1, test_case_id2, similarity_score)
        """
        similar_pairs = []
        test_case_ids = list(test_cases.keys())
        
        # Compare all pairs
        for i in range(len(test_case_ids)):
            for j in range(i + 1, len(test_case_ids)):
                id1 = test_case_ids[i]
                id2 = test_case_ids[j]
                
                similarity_result = self.calculate_comprehensive_similarity(
                    test_cases[id1],
                    test_cases[id2]
                )
                
                overall_sim = similarity_result["overall"]
                
                if overall_sim >= threshold:
                    similar_pairs.append((id1, id2, overall_sim))
        
        # Sort by similarity (highest first)
        similar_pairs.sort(key=lambda x: x[2], reverse=True)
        
        return similar_pairs

