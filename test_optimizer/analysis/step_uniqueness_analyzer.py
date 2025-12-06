"""
Module for analyzing step-level uniqueness between test cases.
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from Levenshtein import distance as levenshtein_distance
import hashlib
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase, TestStep
from data.normalizers import (
    normalize_action_name,
    normalize_element_identifier,
    clean_description
)


class StepUniquenessAnalyzer:
    """Analyzes step-level uniqueness between test cases."""
    
    def __init__(self, fuzzy_threshold: float = 0.85):
        """
        Initialize step uniqueness analyzer.
        
        Args:
            fuzzy_threshold: Similarity threshold for fuzzy matching (0.0 to 1.0)
        """
        self.fuzzy_threshold = fuzzy_threshold
    
    def identify_unique_steps(
        self, 
        test_case1: TestCase, 
        test_case2: TestCase
    ) -> Dict:
        """
        Identify unique steps in each test case compared to the other.
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            
        Returns:
            Dictionary with unique steps for each test case
        """
        steps1 = sorted(test_case1.steps, key=lambda s: s.position)
        steps2 = sorted(test_case2.steps, key=lambda s: s.position)
        
        # Build step signatures for comparison
        signatures1 = {self._get_step_signature(step): step for step in steps1}
        signatures2 = {self._get_step_signature(step): step for step in steps2}
        
        # Find exact matches
        exact_matches = set(signatures1.keys()) & set(signatures2.keys())
        
        # Find unique steps (exact)
        unique_in_1_exact = {
            sig: step for sig, step in signatures1.items() 
            if sig not in exact_matches
        }
        unique_in_2_exact = {
            sig: step for sig, step in signatures2.items() 
            if sig not in exact_matches
        }
        
        # Find fuzzy matches (similar but not identical)
        unique_in_1_fuzzy = []
        unique_in_2_fuzzy = []
        
        for sig1, step1 in unique_in_1_exact.items():
            has_fuzzy_match = False
            for sig2, step2 in unique_in_2_exact.items():
                similarity = self._calculate_step_similarity(step1, step2)
                if similarity >= self.fuzzy_threshold:
                    has_fuzzy_match = True
                    break
            if not has_fuzzy_match:
                unique_in_1_fuzzy.append(step1)
        
        for sig2, step2 in unique_in_2_exact.items():
            has_fuzzy_match = False
            for sig1, step1 in unique_in_1_exact.items():
                similarity = self._calculate_step_similarity(step1, step2)
                if similarity >= self.fuzzy_threshold:
                    has_fuzzy_match = True
                    break
            if not has_fuzzy_match:
                unique_in_2_fuzzy.append(step2)
        
        return {
            "test_case_1_id": test_case1.id,
            "test_case_2_id": test_case2.id,
            "exact_matches": len(exact_matches),
            "unique_in_test_case_1": {
                "exact": list(unique_in_1_exact.values()),
                "fuzzy": unique_in_1_fuzzy,
                "total": len(unique_in_1_exact) + len(unique_in_1_fuzzy)
            },
            "unique_in_test_case_2": {
                "exact": list(unique_in_2_exact.values()),
                "fuzzy": unique_in_2_fuzzy,
                "total": len(unique_in_2_exact) + len(unique_in_2_fuzzy)
            },
            "total_unique_steps": len(unique_in_1_exact) + len(unique_in_2_exact) + len(unique_in_1_fuzzy) + len(unique_in_2_fuzzy)
        }
    
    def calculate_step_uniqueness_score(
        self, 
        test_case: TestCase, 
        all_test_cases: Dict[int, TestCase]
    ) -> float:
        """
        Calculate how unique a test case is compared to all others.
        
        Args:
            test_case: The test case to analyze
            all_test_cases: Dictionary of all test cases
            
        Returns:
            Uniqueness score from 0.0 to 1.0 (higher = more unique)
        """
        if len(all_test_cases) <= 1:
            return 1.0
        
        test_case_steps = sorted(test_case.steps, key=lambda s: s.position)
        test_case_signatures = {self._get_step_signature(step) for step in test_case_steps}
        
        if not test_case_signatures:
            return 0.0
        
        # Count how many steps are unique (not found in other test cases)
        unique_count = 0
        total_steps = len(test_case_steps)
        
        for step in test_case_steps:
            step_sig = self._get_step_signature(step)
            is_unique = True
            
            # Check if this step exists in other test cases
            for other_id, other_test_case in all_test_cases.items():
                if other_id == test_case.id:
                    continue
                
                other_steps = sorted(other_test_case.steps, key=lambda s: s.position)
                for other_step in other_steps:
                    other_sig = self._get_step_signature(other_step)
                    
                    # Check exact match
                    if step_sig == other_sig:
                        is_unique = False
                        break
                    
                    # Check fuzzy match
                    similarity = self._calculate_step_similarity(step, other_step)
                    if similarity >= self.fuzzy_threshold:
                        is_unique = False
                        break
                
                if not is_unique:
                    break
            
            if is_unique:
                unique_count += 1
        
        uniqueness_score = unique_count / total_steps if total_steps > 0 else 0.0
        return uniqueness_score
    
    def check_step_coverage(
        self, 
        unique_steps: List[TestStep], 
        other_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Check if unique steps are covered by other test cases.
        
        Args:
            unique_steps: List of unique steps to check
            other_test_cases: Dictionary of other test cases to check against
            
        Returns:
            Dictionary with coverage information
        """
        covered_steps = []
        uncovered_steps = []
        
        for step in unique_steps:
            step_sig = self._get_step_signature(step)
            is_covered = False
            covering_test_cases = []
            
            for test_id, test_case in other_test_cases.items():
                test_steps = sorted(test_case.steps, key=lambda s: s.position)
                for test_step in test_steps:
                    test_sig = self._get_step_signature(test_step)
                    
                    # Check exact match
                    if step_sig == test_sig:
                        is_covered = True
                        covering_test_cases.append(test_id)
                        break
                    
                    # Check fuzzy match
                    similarity = self._calculate_step_similarity(step, test_step)
                    if similarity >= self.fuzzy_threshold:
                        is_covered = True
                        covering_test_cases.append(test_id)
                        break
                
                if is_covered:
                    break
            
            if is_covered:
                covered_steps.append({
                    "step": step,
                    "covering_test_cases": covering_test_cases
                })
            else:
                uncovered_steps.append(step)
        
        return {
            "total_unique_steps": len(unique_steps),
            "covered_steps": covered_steps,
            "uncovered_steps": uncovered_steps,
            "coverage_percentage": (len(covered_steps) / len(unique_steps) * 100) if unique_steps else 0.0,
            "all_covered": len(uncovered_steps) == 0
        }
    
    def generate_uniqueness_report(
        self, 
        test_case_id: int, 
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Generate comprehensive uniqueness report for a test case.
        
        Args:
            test_case_id: ID of test case to analyze
            test_cases: Dictionary of all test cases
            
        Returns:
            Comprehensive uniqueness report
        """
        if test_case_id not in test_cases:
            return {
                "error": f"Test case {test_case_id} not found"
            }
        
        test_case = test_cases[test_case_id]
        other_test_cases = {tid: tc for tid, tc in test_cases.items() if tid != test_case_id}
        
        # Calculate uniqueness score
        uniqueness_score = self.calculate_step_uniqueness_score(test_case, test_cases)
        
        # Identify unique steps
        test_case_steps = sorted(test_case.steps, key=lambda s: s.position)
        unique_steps = []
        
        for step in test_case_steps:
            step_sig = self._get_step_signature(step)
            is_unique = True
            
            for other_id, other_test_case in other_test_cases.items():
                other_steps = sorted(other_test_case.steps, key=lambda s: s.position)
                for other_step in other_steps:
                    other_sig = self._get_step_signature(other_step)
                    
                    if step_sig == other_sig:
                        is_unique = False
                        break
                    
                    similarity = self._calculate_step_similarity(step, other_step)
                    if similarity >= self.fuzzy_threshold:
                        is_unique = False
                        break
                
                if not is_unique:
                    break
            
            if is_unique:
                unique_steps.append(step)
        
        # Check coverage of unique steps
        coverage_info = self.check_step_coverage(unique_steps, other_test_cases)
        
        return {
            "test_case_id": test_case_id,
            "test_case_name": test_case.name,
            "total_steps": len(test_case_steps),
            "unique_steps_count": len(unique_steps),
            "uniqueness_score": uniqueness_score,
            "unique_steps": [
                {
                    "position": step.position,
                    "action_name": step.action_name,
                    "element": step.element,
                    "description": step.description
                }
                for step in unique_steps
            ],
            "coverage_info": coverage_info,
            "recommendation": self._generate_recommendation(uniqueness_score, coverage_info)
        }
    
    def _get_step_signature(self, step: TestStep) -> str:
        """
        Generate a signature for a step for comparison.
        
        Args:
            step: The TestStep object
            
        Returns:
            Step signature string
        """
        # Normalize components
        action = normalize_action_name(step.action_name) if step.action_name else ""
        element = normalize_element_identifier(step.element) if step.element else ""
        description = clean_description(step.description) or ""
        if description:
            description = description.lower().strip()
        test_data = str(step.test_data).lower().strip() if step.test_data else ""
        
        # Create signature
        signature_parts = [action, element, description, test_data]
        signature_str = "|".join(signature_parts)
        
        # Hash for consistent comparison
        return hashlib.md5(signature_str.encode()).hexdigest()
    
    def _calculate_step_similarity(self, step1: TestStep, step2: TestStep) -> float:
        """
        Calculate similarity between two steps using fuzzy matching.
        
        Args:
            step1: First step
            step2: Second step
            
        Returns:
            Similarity score from 0.0 to 1.0
        """
        # Compare action names
        action1 = normalize_action_name(step1.action_name) if step1.action_name else ""
        action2 = normalize_action_name(step2.action_name) if step2.action_name else ""
        action_sim = self._fuzzy_string_similarity(action1, action2)
        
        # Compare elements
        element1 = normalize_element_identifier(step1.element) or ""
        element2 = normalize_element_identifier(step2.element) or ""
        element_sim = self._fuzzy_string_similarity(element1, element2)
        
        # Compare descriptions
        desc1 = step1.description.lower().strip() if step1.description else ""
        desc2 = step2.description.lower().strip() if step2.description else ""
        desc_sim = self._fuzzy_string_similarity(desc1, desc2)
        
        # Weighted similarity
        similarity = (
            action_sim * 0.4 +  # Action is most important
            element_sim * 0.3 +  # Element is important
            desc_sim * 0.3       # Description provides context
        )
        
        return similarity
    
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
    
    def _generate_recommendation(
        self, 
        uniqueness_score: float, 
        coverage_info: Dict
    ) -> str:
        """
        Generate recommendation based on uniqueness and coverage.
        
        Args:
            uniqueness_score: Uniqueness score
            coverage_info: Coverage information
            
        Returns:
            Recommendation string
        """
        if uniqueness_score >= 0.7:
            return "Keep: Test case has many unique steps"
        elif uniqueness_score >= 0.4:
            if coverage_info["all_covered"]:
                return "Consider removing: Unique steps are covered elsewhere"
            else:
                return "Keep: Has unique steps not covered elsewhere"
        else:
            if coverage_info["all_covered"]:
                return "Safe to remove: Low uniqueness and steps covered elsewhere"
            else:
                return "Review: Low uniqueness but some steps not covered elsewhere"

