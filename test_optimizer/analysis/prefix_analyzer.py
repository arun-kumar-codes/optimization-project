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
        # Login pattern indicators
        self.login_keywords = ["login", "signin", "authenticate", "username", "password", "credentials"]
        self.login_actions = ["navigateto", "type", "enter", "click", "submit"]
        self.login_elements = ["username", "password", "login", "signin", "submit", "button"]
    
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
        min_group_size: int = 3,
        use_flexible_login: bool = True
    ) -> List[Dict]:
        """
        Find groups of test cases that can be merged based on common prefixes.
        
        ENHANCED: Now supports flexible login pattern matching.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            min_prefix_length: Minimum common prefix length to consider (or login pattern)
            min_group_size: Minimum group size to consider for merging
            use_flexible_login: If True, use flexible login pattern detection
            
        Returns:
            List of mergeable groups
        """
        mergeable_groups = []
        test_case_list = list(test_cases.values())
        processed = set()
        
        # ENHANCED: Try to find groups by checking all test cases together first
        # This handles mixed login scenarios better (some have login, some don't)
        if use_flexible_login and len(test_case_list) >= min_group_size:
            # Try to merge all test cases in the group at once
            merge_points = self.identify_flexible_merge_points(test_case_list)
            prefix_steps = merge_points["prefix"]
            has_login_pattern = merge_points.get("has_login", False)
            mixed_login = merge_points.get("mixed_login", False)
            
            # If we have a login pattern (even with mixed login), all can merge
            if has_login_pattern and len(prefix_steps) >= 1:
                return [{
                    "test_case_ids": [tc.id for tc in test_case_list],
                    "test_cases": test_case_list,
                    "common_prefix": prefix_steps,
                    "prefix_length": len(prefix_steps),
                    "prefix_actions": [step.action_name for step in prefix_steps],
                    "group_size": len(test_case_list),
                    "has_login_pattern": has_login_pattern,
                    "mixed_login": mixed_login
                }]
        
        # Fallback: Try to find groups starting from each test case
        for i, test_case1 in enumerate(test_case_list):
            if test_case1.id in processed:
                continue
            
            # Find test cases that can be merged with this one
            group = [test_case1]
            
            # Try flexible merge points first
            if use_flexible_login:
                merge_points = self.identify_flexible_merge_points([test_case1])
                prefix_steps = merge_points["prefix"]
                has_login_pattern = merge_points.get("has_login", False)
            else:
                prefix_steps = self.identify_common_prefix([test_case1])
                has_login_pattern = False
            
            for j, test_case2 in enumerate(test_case_list[i+1:], start=i+1):
                if test_case2.id in processed:
                    continue
                
                # Check if they can be merged (flexible or exact)
                can_merge = False
                new_prefix_steps = []
                
                if use_flexible_login:
                    # Try flexible merge with both test cases
                    merge_points = self.identify_flexible_merge_points([test_case1, test_case2])
                    new_prefix_steps = merge_points["prefix"]
                    has_login_pattern = merge_points.get("has_login", False)
                    
                    # Can merge if:
                    # 1. Has login pattern (even if different lengths) - handles mixed login
                    # 2. Or has common prefix >= min_prefix_length
                    if has_login_pattern and len(new_prefix_steps) >= 1:
                        can_merge = True
                    elif len(new_prefix_steps) >= min_prefix_length:
                        can_merge = True
                else:
                    # Standard exact prefix matching
                    new_prefix_steps = self.identify_common_prefix([test_case1, test_case2])
                    if len(new_prefix_steps) >= min_prefix_length:
                        can_merge = True
                
                if can_merge:
                    group.append(test_case2)
                    prefix_steps = new_prefix_steps
            
            # Check if group meets minimum requirements
            prefix_length = len(prefix_steps)
            meets_min_prefix = (has_login_pattern and prefix_length >= 1) or (prefix_length >= min_prefix_length)
            
            if len(group) >= min_group_size and meets_min_prefix:
                mergeable_groups.append({
                    "test_case_ids": [tc.id for tc in group],
                    "test_cases": group,
                    "common_prefix": prefix_steps,
                    "prefix_length": prefix_length,
                    "prefix_actions": [step.action_name for step in prefix_steps],
                    "group_size": len(group),
                    "has_login_pattern": has_login_pattern
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
    
    def _is_login_step(self, step: TestStep) -> bool:
        """
        Check if a step is part of a login pattern.
        
        Args:
            step: TestStep object
            
        Returns:
            True if step appears to be part of login flow
        """
        action_lower = step.action_name.lower()
        element_lower = (step.element or "").lower()
        desc_lower = (step.description or "").lower()
        test_data_lower = (str(step.test_data) if step.test_data else "").lower()
        
        # Check if action is login-related
        if action_lower == "navigateto":
            # Check if navigating to login page
            url = self._extract_url_from_step(step)
            if url:
                url_lower = url.lower()
                if any(kw in url_lower for kw in ["login", "signin", "auth", "authenticate"]):
                    return True
        
        # Check if typing/entering username or password
        if action_lower in ["type", "enter", "fill", "input"]:
            if any(kw in element_lower or kw in desc_lower or kw in test_data_lower 
                   for kw in self.login_keywords):
                return True
        
        # Check if clicking login button
        if action_lower in ["click", "doubleclick"]:
            if any(kw in element_lower or kw in desc_lower 
                   for kw in self.login_elements):
                return True
        
        return False
    
    def _detect_login_section(self, test_case: TestCase) -> Tuple[int, int]:
        """
        Detect the login section boundaries in a test case.
        
        Args:
            test_case: TestCase object
            
        Returns:
            Tuple of (start_index, end_index) of login section, or (0, 0) if no login detected
        """
        steps = sorted(test_case.steps, key=lambda s: s.position)
        login_start = None
        login_end = None
        
        for i, step in enumerate(steps):
            if self._is_login_step(step):
                if login_start is None:
                    login_start = i
                login_end = i + 1
            elif login_start is not None:
                # Login section ended
                break
        
        if login_start is not None:
            return (login_start, login_end or len(steps))
        return (0, 0)
    
    def identify_flexible_merge_points(
        self,
        test_cases: List[TestCase]
    ) -> Dict:
        """
        Find merge points with flexible login handling.
        
        ENHANCED: Handles cases where:
        - Some test cases have login, others don't (post-login only)
        - Different login flows but same website/role
        - Login patterns are detected semantically, not just exact matches
        
        Args:
            test_cases: List of TestCase objects
            
        Returns:
            Dictionary with prefix, unique_middles, suffix, and login_info
        """
        if not test_cases:
            return {
                "prefix": [],
                "unique_middles": [],
                "suffix": [],
                "prefix_length": 0,
                "suffix_length": 0,
                "has_login": False,
                "login_sections": []
            }
        
        # Detect login sections for each test case
        login_sections = []
        has_login_any = False
        for tc in test_cases:
            login_start, login_end = self._detect_login_section(tc)
            login_sections.append({
                "test_case_id": tc.id,
                "start": login_start,
                "end": login_end,
                "has_login": login_end > login_start
            })
            if login_end > login_start:
                has_login_any = True
        
        # Strategy 1: If all have login, check if they're at the same position
        all_have_login = all(ls["has_login"] for ls in login_sections)
        if all_have_login:
            # Check if login sections are at the start for all (position 0)
            all_login_at_start = all(ls["start"] == 0 for ls in login_sections)
            if all_login_at_start:
                # All have login at start - use standard method with login-aware matching
                return self._find_merge_points_with_login(test_cases, login_sections)
            else:
                # Some have login at start, some in middle - use mixed login strategy
                return self._find_merge_points_mixed_login(test_cases, login_sections)
        
        # Strategy 2: Some have login, some don't - use login as optional prefix
        if has_login_any:
            return self._find_merge_points_mixed_login(test_cases, login_sections)
        
        # Strategy 3: No login detected - use standard method
        result = self.find_merge_points(test_cases)
        result["has_login"] = False
        result["login_sections"] = login_sections
        return result
    
    def _find_merge_points_with_login(
        self,
        test_cases: List[TestCase],
        login_sections: List[Dict]
    ) -> Dict:
        """Find merge points when all test cases have login."""
        # Find common login prefix (flexible matching)
        common_login_prefix = []
        steps_list = [sorted(tc.steps, key=lambda s: s.position) for tc in test_cases]
        
        # Find the maximum login section end
        max_login_end = max(ls["end"] for ls in login_sections)
        
        # Try to find common login steps (with flexible matching)
        for i in range(max_login_end):
            steps_at_i = []
            for j, steps in enumerate(steps_list):
                if i < len(steps) and i < login_sections[j]["end"]:
                    steps_at_i.append(steps[i])
                else:
                    steps_at_i.append(None)
            
            # Filter out None values
            valid_steps = [s for s in steps_at_i if s is not None]
            if len(valid_steps) < len(test_cases):
                break
            
            # Check if all steps are login-related and semantically similar
            if all(self._is_login_step(s) for s in valid_steps):
                # Use first step as representative
                common_login_prefix.append(valid_steps[0])
            else:
                break
        
        # Find common suffix
        common_suffix_steps = self.identify_common_suffix(test_cases)
        suffix_length = len(common_suffix_steps)
        
        # Extract unique middle sections (after login, before suffix)
        unique_middles = []
        for idx, test_case in enumerate(test_cases):
            steps = sorted(test_case.steps, key=lambda s: s.position)
            login_end = login_sections[idx]["end"]
            middle_start = max(len(common_login_prefix), login_end)
            middle_end = len(steps) - suffix_length if suffix_length > 0 else len(steps)
            
            middle_steps = steps[middle_start:middle_end]
            unique_middles.append({
                "test_case_id": test_case.id,
                "steps": middle_steps,
                "action_sequence": [step.action_name for step in middle_steps]
            })
        
        return {
            "prefix": common_login_prefix,
            "unique_middles": unique_middles,
            "suffix": common_suffix_steps,
            "prefix_length": len(common_login_prefix),
            "suffix_length": suffix_length,
            "prefix_actions": [step.action_name for step in common_login_prefix],
            "suffix_actions": [step.action_name for step in common_suffix_steps],
            "has_login": True,
            "login_sections": login_sections
        }
    
    def _find_merge_points_mixed_login(
        self,
        test_cases: List[TestCase],
        login_sections: List[Dict]
    ) -> Dict:
        """
        Find merge points when some test cases have login and others don't.
        
        Strategy: Use login as optional prefix - if one has login, use it;
        if others don't have login, their steps start after login section.
        """
        steps_list = [sorted(tc.steps, key=lambda s: s.position) for tc in test_cases]
        
        # Find the longest login section (will be our prefix)
        login_prefix_steps = []
        max_login_length = 0
        login_tc_idx = None
        
        for idx, ls in enumerate(login_sections):
            if ls["has_login"]:
                login_length = ls["end"] - ls["start"]
                if login_length > max_login_length:
                    max_login_length = login_length
                    login_tc_idx = idx
                    login_prefix_steps = steps_list[idx][ls["start"]:ls["end"]]
        
        # Find common suffix
        common_suffix_steps = self.identify_common_suffix(test_cases)
        suffix_length = len(common_suffix_steps)
        
        # Extract unique middle sections
        # For test cases with login: start after their login section
        # For test cases without login: start from beginning (they're already post-login)
        unique_middles = []
        for idx, test_case in enumerate(test_cases):
            steps = steps_list[idx]
            ls = login_sections[idx]
            
            if ls["has_login"]:
                # Has login - middle starts after its login section
                middle_start = ls["end"]
            else:
                # No login - all steps are post-login (middle starts at 0)
                middle_start = 0
            
            middle_end = len(steps) - suffix_length if suffix_length > 0 else len(steps)
            middle_steps = steps[middle_start:middle_end]
            
            unique_middles.append({
                "test_case_id": test_case.id,
                "steps": middle_steps,
                "action_sequence": [step.action_name for step in middle_steps]
            })
        
        return {
            "prefix": login_prefix_steps,
            "unique_middles": unique_middles,
            "suffix": common_suffix_steps,
            "prefix_length": len(login_prefix_steps),
            "suffix_length": suffix_length,
            "prefix_actions": [step.action_name for step in login_prefix_steps],
            "suffix_actions": [step.action_name for step in common_suffix_steps],
            "has_login": True,
            "login_sections": login_sections,
            "mixed_login": True  # Flag indicating mixed login scenario
        }

