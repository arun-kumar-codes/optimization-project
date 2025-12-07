"""
Module for analyzing user flows from test cases.
"""

from typing import Dict, List, Set, Optional
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase, TestStep


class FlowAnalyzer:
    """Analyzes user flows from test cases."""
    
    def __init__(self):
        self.flow_patterns = {
            "authentication": ["login", "logout", "signin", "signout", "authenticate", "password"],
            "navigation": ["navigate", "goto", "visit", "open", "menu", "dashboard"],
            "crud": ["create", "add", "new", "edit", "update", "modify", "delete", "remove"],
            "form": ["submit", "form", "fill", "enter", "input", "select"],
            "search": ["search", "find", "filter", "query"],
            "verification": ["verify", "assert", "check", "validate", "confirm"]
        }
    
    def identify_flow_type(self, test_case: TestCase) -> List[str]:
        """
        Identify the type(s) of flow a test case represents.
        
        Args:
            test_case: The TestCase object
            
        Returns:
            List of flow types (e.g., ["authentication", "navigation"])
        """
        flow_types = set()
        text_to_analyze = f"{test_case.name} {test_case.description or ''}".lower()
        
        # Check each flow pattern
        for flow_type, keywords in self.flow_patterns.items():
            for keyword in keywords:
                if keyword in text_to_analyze:
                    flow_types.add(flow_type)
                    break
        
        # Also analyze steps
        for step in test_case.steps:
            action_lower = step.action_name.lower()
            desc_lower = (step.description or "").lower()
            
            # Check for authentication flows
            if any(kw in action_lower or kw in desc_lower for kw in ["login", "password", "username"]):
                flow_types.add("authentication")
            
            # Check for CRUD operations
            if any(kw in action_lower or kw in desc_lower for kw in ["create", "add", "new", "edit", "update", "delete"]):
                flow_types.add("crud")
            
            # Check for navigation
            if action_lower == "navigateto" or "navigate" in desc_lower:
                flow_types.add("navigation")
            
            # Check for form submission
            if any(kw in action_lower or kw in desc_lower for kw in ["submit", "form", "save"]):
                flow_types.add("form")
            
            # Check for search
            if any(kw in action_lower or kw in desc_lower for kw in ["search", "filter", "find"]):
                flow_types.add("search")
        
        return sorted(list(flow_types)) if flow_types else ["general"]
    
    def extract_flow_boundaries(self, test_case: TestCase) -> Dict[str, Optional[int]]:
        """
        Extract flow boundaries (start and end points).
        
        Args:
            test_case: The TestCase object
            
        Returns:
            Dictionary with start_position and end_position
        """
        if not test_case.steps:
            return {"start_position": None, "end_position": None}
        
        sorted_steps = sorted(test_case.steps, key=lambda s: s.position)
        
        start_position = sorted_steps[0].position if sorted_steps else None
        end_position = sorted_steps[-1].position if sorted_steps else None
        
        return {
            "start_position": start_position,
            "end_position": end_position,
            "total_steps": len(sorted_steps)
        }
    
    def identify_flow_dependencies(self, test_case: TestCase) -> List[int]:
        """
        Identify flow dependencies (prerequisites).
        
        Args:
            test_case: The TestCase object
            
        Returns:
            List of prerequisite test case IDs
        """
        dependencies = []
        
        # Check explicit prerequisite
        if test_case.prerequisite_case:
            dependencies.append(test_case.prerequisite_case)
        
        # Check for login/navigation patterns that might indicate dependencies
        first_steps = sorted(test_case.steps, key=lambda s: s.position)[:3]
        for step in first_steps:
            action_lower = step.action_name.lower()
            desc_lower = (step.description or "").lower()
            
            
            if "login" not in action_lower and "login" not in desc_lower:
                flow_types = self.identify_flow_type(test_case)
                if "authentication" in flow_types:
                    
                    pass
        
        return dependencies
    
    def extract_page_transitions(self, test_case: TestCase) -> List[Dict]:
        """
        Extract page/URL transitions from test case.
        
        Args:
            test_case: The TestCase object
            
        Returns:
            List of transition dictionaries
        """
        transitions = []
        current_url = None
        
        for step in sorted(test_case.steps, key=lambda s: s.position):
            # Check for navigation actions
            if step.action_name == "navigateto":
                new_url = self._extract_url_from_step(step)
                if new_url:
                    if current_url:
                        transitions.append({
                            "from": current_url,
                            "to": new_url,
                            "step_position": step.position
                        })
                    current_url = new_url
        
        return transitions
    
    def _extract_url_from_step(self, step: TestStep) -> Optional[str]:
        """Extract URL from a navigation step."""
        # Check test_data
        if step.test_data and ("http://" in step.test_data or "https://" in step.test_data):
            return step.test_data
        
        # Check action/description
        text = f"{step.action} {step.description or ''}"
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        match = re.search(url_pattern, text)
        if match:
            return match.group(0)
        
        return None
    
    def identify_critical_paths(self, test_cases: Dict[int, TestCase]) -> List[Dict]:
        """
        Identify critical paths (high-frequency, high-priority flows).
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            List of critical path dictionaries
        """
        # Count flow type frequencies
        flow_type_counts = {}
        flow_type_priorities = {}
        
        for test_id, test_case in test_cases.items():
            flow_types = self.identify_flow_type(test_case)
            priority = test_case.priority or 5 
            
            for flow_type in flow_types:
                if flow_type not in flow_type_counts:
                    flow_type_counts[flow_type] = 0
                    flow_type_priorities[flow_type] = []
                
                flow_type_counts[flow_type] += 1
                flow_type_priorities[flow_type].append(priority)
        
        # Calculate critical paths
        critical_paths = []
        for flow_type, count in flow_type_counts.items():
            avg_priority = sum(flow_type_priorities[flow_type]) / len(flow_type_priorities[flow_type])
            # Lower priority number = higher priority
            priority_score = 6 - avg_priority if avg_priority > 0 else 0
            
            criticality = (count * 0.5) + (priority_score * 0.5)
            
            critical_paths.append({
                "flow_type": flow_type,
                "frequency": count,
                "average_priority": avg_priority,
                "criticality_score": criticality,
                "test_case_ids": [
                    tid for tid, tc in test_cases.items()
                    if flow_type in self.identify_flow_type(tc)
                ]
            })
        
        # Sort by criticality
        critical_paths.sort(key=lambda x: x["criticality_score"], reverse=True)
        
        return critical_paths
    
    def extract_common_flows(self, test_cases: Dict[int, TestCase]) -> Dict[str, List[int]]:
        """
        Extract common flow patterns across test cases.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Dictionary mapping flow patterns to test case IDs
        """
        flow_groups = {}
        
        for test_id, test_case in test_cases.items():
            flow_types = self.identify_flow_type(test_case)
            flow_signature = "->".join(sorted(flow_types))
            
            if flow_signature not in flow_groups:
                flow_groups[flow_signature] = []
            flow_groups[flow_signature].append(test_id)
        
        return flow_groups

