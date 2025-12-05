"""
Module for extracting step sequences from test cases.
"""

from typing import List, Dict, Tuple
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase, TestStep


class SequenceExtractor:
    """Extracts sequences and patterns from test cases."""
    
    def extract_action_sequence(self, test_case: TestCase) -> List[str]:
        """
        Extract ordered sequence of action names from a test case.
        
        Args:
            test_case: The TestCase object
            
        Returns:
            List of action names in order (e.g., ["navigateTo", "click", "enter", "click"])
        """
        return test_case.get_action_sequence()
    
    def extract_element_sequence(self, test_case: TestCase) -> List[str]:
        """
        Extract ordered sequence of elements interacted with.
        
        Args:
            test_case: The TestCase object
            
        Returns:
            List of element identifiers in order
        """
        elements = []
        for step in sorted(test_case.steps, key=lambda s: s.position):
            if step.element:
                elements.append(step.element.lower().strip())
            elif step.locator:
                # Try to extract from locator
                if isinstance(step.locator, dict):
                    for key in ["label", "id", "name", "placeholder"]:
                        if key in step.locator:
                            elements.append(str(step.locator[key]).lower().strip())
                            break
        
        return elements
    
    def extract_flow_pattern(self, test_case: TestCase) -> List[str]:
        """
        Extract abstracted flow pattern (ignoring specific test data).
        
        Args:
            test_case: The TestCase object
            
        Returns:
            Abstracted flow pattern (e.g., ["navigateTo", "click", "enter", "click", "verify"])
        """
        pattern = []
        for step in sorted(test_case.steps, key=lambda s: s.position):
            action = step.action_name
            
            # Abstract common patterns
            if action == "navigateTo":
                pattern.append("navigateTo")
            elif action in ["click", "doubleClick", "rightClick"]:
                pattern.append("click")
            elif action in ["enter", "type", "fill", "input"]:
                pattern.append("enter")
            elif action in ["select", "selectOption", "choose"]:
                pattern.append("select")
            elif action in ["verify", "assert", "check", "validate"]:
                pattern.append("verify")
            elif action in ["wait", "waitFor", "pause"]:
                pattern.append("wait")
            else:
                pattern.append(action)
        
        return pattern
    
    def extract_action_signature(self, test_case: TestCase) -> str:
        """
        Create a signature string from action sequence.
        
        Args:
            test_case: The TestCase object
            
        Returns:
            Signature string (e.g., "navigateTo->click->enter->click")
        """
        sequence = self.extract_action_sequence(test_case)
        return "->".join(sequence)
    
    def extract_step_details(self, test_case: TestCase) -> List[Dict]:
        """
        Extract detailed step information for comparison.
        
        Args:
            test_case: The TestCase object
            
        Returns:
            List of step detail dictionaries
        """
        step_details = []
        for step in sorted(test_case.steps, key=lambda s: s.position):
            detail = {
                "position": step.position,
                "action_name": step.action_name,
                "action": step.action,
                "element": step.element,
                "description": step.description,
                "has_locator": step.locator is not None,
                "has_test_data": step.test_data is not None
            }
            step_details.append(detail)
        
        return step_details
    
    def extract_common_patterns(self, test_cases: Dict[int, TestCase]) -> Dict[str, List[int]]:
        """
        Identify common flow patterns across test cases.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Dictionary mapping pattern signatures to list of test case IDs
        """
        patterns = {}
        
        for test_case_id, test_case in test_cases.items():
            signature = self.extract_action_signature(test_case)
            
            if signature not in patterns:
                patterns[signature] = []
            patterns[signature].append(test_case_id)
        
        return patterns
    
    def compare_sequences(self, seq1: List[str], seq2: List[str]) -> Tuple[float, int]:
        """
        Compare two sequences and return similarity metrics.
        
        Args:
            seq1: First sequence
            seq2: Second sequence
            
        Returns:
            Tuple of (similarity_score, common_length)
            similarity_score: 0.0 to 1.0 (1.0 = identical)
            common_length: Length of longest common subsequence
        """
        if not seq1 and not seq2:
            return 1.0, 0
        if not seq1 or not seq2:
            return 0.0, 0
        
        # Calculate longest common subsequence length
        lcs_length = self._longest_common_subsequence(seq1, seq2)
        
        # Calculate similarity score
        max_len = max(len(seq1), len(seq2))
        similarity = lcs_length / max_len if max_len > 0 else 0.0
        
        return similarity, lcs_length
    
    def _longest_common_subsequence(self, seq1: List[str], seq2: List[str]) -> int:
        """
        Calculate the length of the longest common subsequence.
        
        Args:
            seq1: First sequence
            seq2: Second sequence
            
        Returns:
            Length of LCS
        """
        m, n = len(seq1), len(seq2)
        
        # Create a 2D table to store LCS lengths
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        # Fill the table
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1] == seq2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        
        return dp[m][n]

