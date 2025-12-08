"""
Module for identifying common prefixes and suffixes in test cases.
Used for multi-test-case merging strategy.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase, TestStep
from analysis.sequence_extractor import SequenceExtractor


class PrefixAnalyzer:
    """Identifies common prefixes and suffixes for merging test cases."""
    
    def __init__(self):
        """Initialize prefix analyzer."""
        self.sequence_extractor = SequenceExtractor()
    
    def identify_common_prefix(
        self,
        test_cases: List[TestCase]
    ) -> List[TestStep]:
        """
        Identify common prefix steps shared by all test cases.
        
        Args:
            test_cases: List of TestCase objects
            
        Returns:
            List of common prefix steps (in order)
        """
        if not test_cases or len(test_cases) == 0:
            return []
        
        if len(test_cases) == 1:
            return sorted(test_cases[0].steps, key=lambda s: s.position)
        
        # Get step sequences for all test cases
        step_sequences = []
        for test_case in test_cases:
            steps = sorted(test_case.steps, key=lambda s: s.position)
            step_sequences.append(steps)
        
        # Find longest common prefix
        common_prefix = []
        min_length = min(len(seq) for seq in step_sequences)
        
        for i in range(min_length):
            steps_at_i = [seq[i] for seq in step_sequences]
            
            first_step = steps_at_i[0]
            if all(self._steps_equivalent(first_step, step) for step in steps_at_i[1:]):
                common_prefix.append(first_step)
            else:
                break
        
        return common_prefix
    
    def find_longest_common_prefix(
        self,
        test_cases: List[TestCase]
    ) -> List[str]:
        """
        Find longest common prefix as action sequence.
        
        Args:
            test_cases: List of TestCase objects
            
        Returns:
            List of action names in common prefix
        """
        common_prefix_steps = self.identify_common_prefix(test_cases)
        return [step.action_name for step in common_prefix_steps]
    
    def extract_prefix_steps(
        self,
        test_case: TestCase,
        prefix_length: int
    ) -> List[TestStep]:
        """
        Extract prefix steps from a test case.
        
        Args:
            test_case: The TestCase object
            prefix_length: Number of steps to extract from start
            
        Returns:
            List of prefix steps
        """
        steps = sorted(test_case.steps, key=lambda s: s.position)
        return steps[:prefix_length]
    
    def identify_common_suffix(
        self,
        test_cases: List[TestCase]
    ) -> List[TestStep]:
        """
        Identify common suffix steps shared by all test cases.
        
        Args:
            test_cases: List of TestCase objects
            
        Returns:
            List of common suffix steps (in order)
        """
        if not test_cases or len(test_cases) == 0:
            return []
        
        if len(test_cases) == 1:
            steps = sorted(test_cases[0].steps, key=lambda s: s.position)
            return steps
        
        # Get step sequences for all test cases
        step_sequences = []
        for test_case in test_cases:
            steps = sorted(test_case.steps, key=lambda s: s.position)
            step_sequences.append(steps)
        
        common_suffix = []
        min_length = min(len(seq) for seq in step_sequences)
        
        for i in range(1, min_length + 1):
            steps_at_i = [seq[-i] for seq in step_sequences]
            
            first_step = steps_at_i[0]
            if all(self._steps_equivalent(first_step, step) for step in steps_at_i[1:]):
                common_suffix.insert(0, first_step) 
            else:
                break
        
        return common_suffix
    
    def find_merge_points(
        self,
        test_cases: List[TestCase]
    ) -> Dict:
        """
        Find merge points: prefix, unique middle sections, and suffix.
        
        Args:
            test_cases: List of TestCase objects
            
        Returns:
            Dictionary with prefix, unique_middles, and suffix
        """
        if not test_cases:
            return {
                "prefix": [],
                "unique_middles": [],
                "suffix": [],
                "prefix_length": 0,
                "suffix_length": 0
            }
        
        # Find common prefix
        common_prefix_steps = self.identify_common_prefix(test_cases)
        prefix_length = len(common_prefix_steps)
        
        # Find common suffix
        common_suffix_steps = self.identify_common_suffix(test_cases)
        suffix_length = len(common_suffix_steps)
        
        unique_middles = []
        for test_case in test_cases:
            steps = sorted(test_case.steps, key=lambda s: s.position)
            
            middle_start = prefix_length
            middle_end = len(steps) - suffix_length if suffix_length > 0 else len(steps)
            
            middle_steps = steps[middle_start:middle_end]
            unique_middles.append({
                "test_case_id": test_case.id,
                "steps": middle_steps,
                "action_sequence": [step.action_name for step in middle_steps]
            })
        
        return {
            "prefix": common_prefix_steps,
            "unique_middles": unique_middles,
            "suffix": common_suffix_steps,
            "prefix_length": prefix_length,
            "suffix_length": suffix_length,
            "prefix_actions": [step.action_name for step in common_prefix_steps],
            "suffix_actions": [step.action_name for step in common_suffix_steps]
        }
    
    def _steps_equivalent(
        self,
        step1: TestStep,
        step2: TestStep
    ) -> bool:
        """
        Check if two steps are equivalent (same signature).
        
        Args:
            step1: First test step
            step2: Second test step
            
        Returns:
            True if steps are equivalent
        """
        # Compare action names
        if step1.action_name != step2.action_name:
            return False
        
        if step1.element and step2.element:
            if step1.element.lower().strip() != step2.element.lower().strip():
                return False
        
        if step1.action_name == "navigateto":
            url1 = self._extract_url_from_step(step1)
            url2 = self._extract_url_from_step(step2)
            if url1 and url2:
                url1_normalized = self._normalize_url(url1)
                url2_normalized = self._normalize_url(url2)
                return url1_normalized == url2_normalized
        
        
        return True
    
    def _extract_url_from_step(
        self,
        step: TestStep
    ) -> Optional[str]:
        """Extract URL from a navigation step."""
        if step.test_data and ("http://" in step.test_data or "https://" in step.test_data):
            return step.test_data
        
        text = f"{step.action} {step.description or ''}"
        import re
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        match = re.search(url_pattern, text)
        if match:
            return match.group(0)
        
        return None
    
    def _normalize_url(
        self,
        url: str
    ) -> str:
        """Normalize URL for comparison (remove query params, fragments)."""
        from urllib.parse import urlparse, urlunparse
        
        try:
            parsed = urlparse(url)
            # Keep only scheme, netloc, and path
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                '',  # params
                '',  # query
                ''   # fragment
            ))
            return normalized.rstrip('/')
        except Exception:
            return url
    
    def find_mergeable_groups(
        self,
        test_cases: Dict[int, TestCase],
        min_prefix_length: int = 2,
        min_group_size: int = 3
    ) -> List[Dict]:
        """
        Find groups of test cases that can be merged based on common prefixes.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            min_prefix_length: Minimum common prefix length to consider
            min_group_size: Minimum group size to consider for merging
            
        Returns:
            List of mergeable groups
        """
        mergeable_groups = []
        test_case_list = list(test_cases.values())
        processed = set()
        
        # Try to find groups starting from each test case
        for i, test_case1 in enumerate(test_case_list):
            if test_case1.id in processed:
                continue
            
            # Find test cases with common prefix
            group = [test_case1]
            prefix_steps = self.identify_common_prefix([test_case1])
            
            for j, test_case2 in enumerate(test_case_list[i+1:], start=i+1):
                if test_case2.id in processed:
                    continue
                
                # Check if they share a common prefix
                common_prefix = self.identify_common_prefix([test_case1, test_case2])
                
                if len(common_prefix) >= min_prefix_length:
                    group.append(test_case2)
                    prefix_steps = common_prefix
            
            if len(group) >= min_group_size and len(prefix_steps) >= min_prefix_length:
                mergeable_groups.append({
                    "test_case_ids": [tc.id for tc in group],
                    "test_cases": group,
                    "common_prefix": prefix_steps,
                    "prefix_length": len(prefix_steps),
                    "prefix_actions": [step.action_name for step in prefix_steps],
                    "group_size": len(group)
                })
                
                for tc in group:
                    processed.add(tc.id)
        
        mergeable_groups.sort(key=lambda g: (g["group_size"], g["prefix_length"]), reverse=True)
        
        return mergeable_groups
    
    def get_prefix_statistics(
        self,
        test_cases: List[TestCase]
    ) -> Dict:
        """
        Get statistics about prefixes in test cases.
        
        Args:
            test_cases: List of TestCase objects
            
        Returns:
            Statistics dictionary
        """
        if not test_cases:
            return {
                "total": 0,
                "common_prefix_length": 0,
                "common_suffix_length": 0
            }
        
        common_prefix = self.identify_common_prefix(test_cases)
        common_suffix = self.identify_common_suffix(test_cases)
        
        return {
            "total": len(test_cases),
            "common_prefix_length": len(common_prefix),
            "common_suffix_length": len(common_suffix),
            "common_prefix_actions": [step.action_name for step in common_prefix],
            "common_suffix_actions": [step.action_name for step in common_suffix]
        }

