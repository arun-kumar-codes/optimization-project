"""
Module for calculating execution priority for test cases.
"""

import sys
from pathlib import Path
from typing import Dict, List
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from flows.flow_analyzer import FlowAnalyzer
from flows.coverage_analyzer import CoverageAnalyzer


class PriorityCalculator:
    """Calculates execution priority for test cases."""
    
    def __init__(self):
        self.flow_analyzer = FlowAnalyzer()
        self.coverage_analyzer = CoverageAnalyzer()
    
    def calculate_priorities(
        self,
        test_cases: Dict[int, TestCase]
    ) -> Dict[int, float]:
        """
        Calculate priority scores for all test cases.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Dictionary mapping test case ID to priority score (0-100)
        """
        priorities = {}
        
        # Calculate coverage scores first (needs all test cases)
        coverage_scores = {}
        for test_id, test_case in test_cases.items():
            score = self.coverage_analyzer.calculate_test_case_coverage_score(test_case)
            coverage_scores[test_id] = score
        
        # Calculate priorities
        for test_id, test_case in test_cases.items():
            priority_score = self._calculate_priority_score(
                test_case,
                coverage_scores[test_id]
            )
            priorities[test_id] = priority_score
        
        return priorities
    
    def _calculate_priority_score(
        self,
        test_case: TestCase,
        coverage_score: float
    ) -> float:
        """
        Calculate priority score for a single test case.
        
        Args:
            test_case: The TestCase object
            coverage_score: Coverage score from coverage analyzer
            
        Returns:
            Priority score from 0 to 100
        """
        score = 0.0
        
        
        if test_case.priority is not None:
            
            priority_score = max(0, (6 - test_case.priority) * 20) if test_case.priority > 0 else 50
            score += priority_score * 0.3
        else:
            score += 50 * 0.3 
        
        if test_case.pass_count is not None and test_case.fail_count is not None:
            total = test_case.pass_count + test_case.fail_count
            if total > 0:
                pass_rate = (test_case.pass_count / total) * 100
                score += pass_rate * 0.25
            else:
                score += 50 * 0.25  
        else:
            score += 50 * 0.25  
        
        flows = self.flow_analyzer.identify_flow_type(test_case)
        critical_flows = ["authentication", "navigation", "crud"]
        critical_flow_count = sum(1 for flow in flows if flow in critical_flows)
        flow_score = min(critical_flow_count / 3.0, 1.0) * 100  
        score += flow_score * 0.20
        
        if test_case.duration is not None:
            
            time_score = max(0, 100 - (test_case.duration / 3000)) 
            score += time_score * 0.15
        else:
            score += 50 * 0.15 
        
        score += coverage_score * 100 * 0.10
        
        return min(100.0, max(0.0, score))
    
    def categorize_priorities(
        self,
        priorities: Dict[int, float]
    ) -> Dict[str, List[int]]:
        """
        Categorize test cases by priority level.
        
        Args:
            priorities: Dictionary of test case ID to priority score
            
        Returns:
            Dictionary with categories and test case IDs
        """
        categories = {
            "smoke": [],      # 80-100: Critical, fast tests
            "high": [],       # 60-79: High priority
            "medium": [],     # 40-59: Medium priority
            "low": []         # 0-39: Low priority
        }
        
        for test_id, score in priorities.items():
            if score >= 80:
                categories["smoke"].append(test_id)
            elif score >= 60:
                categories["high"].append(test_id)
            elif score >= 40:
                categories["medium"].append(test_id)
            else:
                categories["low"].append(test_id)
        
        return categories

