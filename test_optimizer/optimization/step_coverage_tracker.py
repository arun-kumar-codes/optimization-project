"""
Module for tracking step-level coverage across test cases.
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Optional
import hashlib
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase, TestStep
from data.normalizers import (
    normalize_action_name,
    normalize_element_identifier,
    clean_description
)


class StepCoverageTracker:
    """Tracks step-level coverage across test suite."""
    
    def __init__(self):
        """Initialize step coverage tracker."""
        self._coverage_map: Optional[Dict[str, List[int]]] = None
    
    def build_step_coverage_map(
        self, 
        test_cases: Dict[int, TestCase]
    ) -> Dict[str, List[int]]:
        """
        Build a map of step signatures to test cases that cover them.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Dictionary mapping step signature to list of test case IDs
        """
        coverage_map = {}
        
        for test_id, test_case in test_cases.items():
            steps = sorted(test_case.steps, key=lambda s: s.position)
            
            for step in steps:
                step_sig = self._get_step_signature(step)
                
                if step_sig not in coverage_map:
                    coverage_map[step_sig] = []
                
                if test_id not in coverage_map[step_sig]:
                    coverage_map[step_sig].append(test_id)
        
        self._coverage_map = coverage_map
        return coverage_map
    
    def calculate_step_coverage(
        self, 
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Calculate step coverage metrics.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Coverage metrics dictionary
        """
        # Build coverage map if not already built
        if self._coverage_map is None:
            self.build_step_coverage_map(test_cases)
        
        total_unique_steps = len(self._coverage_map) if self._coverage_map else 0
        covered_steps = total_unique_steps  # All steps in map are covered
        
        coverage_percentage = 100.0 if total_unique_steps > 0 else 0.0
        
        return {
            "total_unique_steps": total_unique_steps,
            "covered_steps": covered_steps,
            "uncovered_steps": 0,
            "coverage_percentage": coverage_percentage,
            "coverage_map": self._coverage_map
        }
    
    def get_steps_covered_by_test_case(
        self, 
        test_case_id: int, 
        test_cases: Dict[int, TestCase]
    ) -> Set[str]:
        """
        Get set of step signatures covered by a specific test case.
        
        Args:
            test_case_id: ID of test case
            test_cases: Dictionary of all test cases
            
        Returns:
            Set of step signatures
        """
        if test_case_id not in test_cases:
            return set()
        
        test_case = test_cases[test_case_id]
        steps = sorted(test_case.steps, key=lambda s: s.position)
        
        step_signatures = set()
        for step in steps:
            step_sig = self._get_step_signature(step)
            step_signatures.add(step_sig)
        
        return step_signatures
    
    def check_coverage_loss(
        self, 
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Check step coverage loss after optimization.
        
        Args:
            original_test_cases: Original test cases before optimization
            optimized_test_cases: Optimized test cases after optimization
            
        Returns:
            Coverage loss analysis dictionary
        """
        # Build coverage maps
        original_map = self.build_step_coverage_map(original_test_cases)
        optimized_map = self.build_step_coverage_map(optimized_test_cases)
        
        # Find lost steps
        original_steps = set(original_map.keys())
        optimized_steps = set(optimized_map.keys())
        lost_steps = original_steps - optimized_steps
        
        # Calculate metrics
        original_count = len(original_steps)
        optimized_count = len(optimized_steps)
        lost_count = len(lost_steps)
        
        coverage_delta = optimized_count - original_count
        coverage_percentage_after = (optimized_count / original_count * 100) if original_count > 0 else 0.0
        
        # Find which test cases covered the lost steps
        lost_step_details = []
        for step_sig in lost_steps:
            covering_test_cases = original_map.get(step_sig, [])
            lost_step_details.append({
                "step_signature": step_sig,
                "was_covered_by": covering_test_cases
            })
        
        return {
            "original_step_count": original_count,
            "optimized_step_count": optimized_count,
            "lost_step_count": lost_count,
            "coverage_delta": coverage_delta,
            "coverage_percentage_after": coverage_percentage_after,
            "lost_steps": lost_step_details,
            "coverage_maintained": len(lost_steps) == 0
        }
    
    def validate_step_coverage_maintained(
        self, 
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase],
        threshold: float = 0.95
    ) -> Dict:
        """
        Validate that step coverage is maintained above threshold.
        
        Args:
            original_test_cases: Original test cases
            optimized_test_cases: Optimized test cases
            threshold: Minimum coverage percentage to maintain (0.0 to 1.0)
            
        Returns:
            Validation result dictionary
        """
        coverage_loss = self.check_coverage_loss(original_test_cases, optimized_test_cases)
        
        original_count = coverage_loss["original_step_count"]
        optimized_count = coverage_loss["optimized_step_count"]
        
        if original_count == 0:
            coverage_percentage = 1.0
        else:
            coverage_percentage = optimized_count / original_count
        
        is_maintained = coverage_percentage >= threshold
        
        return {
            "is_maintained": is_maintained,
            "coverage_percentage": coverage_percentage * 100,
            "threshold": threshold * 100,
            "original_steps": original_count,
            "optimized_steps": optimized_count,
            "lost_steps": coverage_loss["lost_step_count"],
            "message": (
                f"Coverage maintained: {coverage_percentage * 100:.1f}% "
                f"(threshold: {threshold * 100:.1f}%)"
                if is_maintained
                else f"Coverage dropped: {coverage_percentage * 100:.1f}% "
                     f"(threshold: {threshold * 100:.1f}%)"
            )
        }
    
    def get_step_coverage_info(
        self, 
        step_signature: str, 
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Get information about which test cases cover a specific step.
        
        Args:
            step_signature: Step signature to check
            test_cases: Dictionary of all test cases
            
        Returns:
            Coverage information dictionary
        """
        if self._coverage_map is None:
            self.build_step_coverage_map(test_cases)
        
        covering_test_cases = self._coverage_map.get(step_signature, [])
        
        return {
            "step_signature": step_signature,
            "covering_test_cases": covering_test_cases,
            "coverage_count": len(covering_test_cases),
            "is_covered": len(covering_test_cases) > 0
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
        element = normalize_element_identifier(step.element) or ""
        description = clean_description(step.description) or ""
        if description:
            description = description.lower().strip()
        test_data = str(step.test_data).lower().strip() if step.test_data else ""
        
        # Create signature
        signature_parts = [action, element, description, test_data]
        signature_str = "|".join(signature_parts)
        
        # Hash for consistent comparison
        return hashlib.md5(signature_str.encode()).hexdigest()


