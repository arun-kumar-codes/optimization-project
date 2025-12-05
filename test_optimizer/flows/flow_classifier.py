"""
Module for classifying test cases by flow types.
"""

from typing import Dict, List
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from flows.flow_analyzer import FlowAnalyzer


class FlowClassifier:
    """Classifies test cases by their primary and secondary flows."""
    
    def __init__(self):
        self.flow_analyzer = FlowAnalyzer()
        self.flow_categories = {
            "authentication": ["login", "logout", "signin", "signout", "password", "authenticate"],
            "dashboard": ["dashboard", "home", "main", "landing"],
            "data_entry": ["form", "input", "enter", "fill", "submit", "create", "add"],
            "search_filter": ["search", "filter", "find", "query", "lookup"],
            "reports_analytics": ["report", "analytics", "statistics", "chart", "graph"],
            "settings_config": ["settings", "config", "preferences", "options"],
            "user_management": ["user", "admin", "role", "permission", "account"],
            "navigation": ["navigate", "goto", "visit", "menu", "link"]
        }
    
    def classify_test_case(
        self, 
        test_case: TestCase
    ) -> Dict:
        """
        Classify a test case by its primary and secondary flows.
        
        Args:
            test_case: The TestCase object
            
        Returns:
            Classification dictionary with primary and secondary flows
        """
        # Get flow types
        flow_types = self.flow_analyzer.identify_flow_type(test_case)
        
        # Determine primary flow (most prominent)
        primary_flow = self._determine_primary_flow(test_case, flow_types)
        
        # Secondary flows (all other flows)
        secondary_flows = [f for f in flow_types if f != primary_flow]
        
        # Map to categories
        primary_category = self._map_to_category(primary_flow)
        secondary_categories = [self._map_to_category(f) for f in secondary_flows]
        
        return {
            "test_case_id": test_case.id,
            "primary_flow": primary_flow,
            "primary_category": primary_category,
            "secondary_flows": secondary_flows,
            "secondary_categories": secondary_categories,
            "all_flows": flow_types,
            "is_multi_flow": len(flow_types) > 1
        }
    
    def _determine_primary_flow(
        self, 
        test_case: TestCase, 
        flow_types: List[str]
    ) -> str:
        """
        Determine the primary flow for a test case.
        
        Args:
            test_case: The TestCase object
            flow_types: List of identified flow types
            
        Returns:
            Primary flow type
        """
        if not flow_types:
            return "general"
        
        if len(flow_types) == 1:
            return flow_types[0]
        
        # Count occurrences in name and description
        text = f"{test_case.name} {test_case.description or ''}".lower()
        flow_scores = {}
        
        for flow_type in flow_types:
            score = 0
            keywords = self.flow_analyzer.flow_patterns.get(flow_type, [])
            for keyword in keywords:
                if keyword in text:
                    score += text.count(keyword)
            flow_scores[flow_type] = score
        
        # Also check step actions
        for step in test_case.steps:
            action_lower = step.action_name.lower()
            desc_lower = (step.description or "").lower()
            
            for flow_type in flow_types:
                keywords = self.flow_analyzer.flow_patterns.get(flow_type, [])
                for keyword in keywords:
                    if keyword in action_lower or keyword in desc_lower:
                        flow_scores[flow_type] = flow_scores.get(flow_type, 0) + 1
        
        # Return flow with highest score, or first one if tie
        if flow_scores:
            primary = max(flow_scores.items(), key=lambda x: x[1])[0]
            return primary
        
        return flow_types[0]
    
    def _map_to_category(self, flow_type: str) -> str:
        """
        Map a flow type to a category.
        
        Args:
            flow_type: The flow type
            
        Returns:
            Category name
        """
        # Direct mapping
        category_map = {
            "authentication": "authentication",
            "navigation": "navigation",
            "crud": "data_entry",
            "form": "data_entry",
            "search": "search_filter",
            "verification": "general"
        }
        
        return category_map.get(flow_type, "general")
    
    def classify_all_test_cases(
        self, 
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Classify all test cases.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Classification results dictionary
        """
        classifications = {}
        category_groups = {}
        
        for test_id, test_case in test_cases.items():
            classification = self.classify_test_case(test_case)
            classifications[test_id] = classification
            
            # Group by primary category
            primary_cat = classification["primary_category"]
            if primary_cat not in category_groups:
                category_groups[primary_cat] = []
            category_groups[primary_cat].append(test_id)
        
        return {
            "classifications": classifications,
            "category_groups": category_groups,
            "summary": {
                "total_test_cases": len(test_cases),
                "categories": {
                    cat: len(ids) for cat, ids in category_groups.items()
                },
                "multi_flow_count": sum(
                    1 for c in classifications.values() if c["is_multi_flow"]
                )
            }
        }
    
    def get_test_cases_by_category(
        self, 
        test_cases: Dict[int, TestCase],
        category: str
    ) -> List[int]:
        """
        Get test case IDs for a specific category.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            category: Category name
            
        Returns:
            List of test case IDs
        """
        result = self.classify_all_test_cases(test_cases)
        return result["category_groups"].get(category, [])
    
    def get_test_cases_by_flow(
        self, 
        test_cases: Dict[int, TestCase],
        flow_type: str
    ) -> List[int]:
        """
        Get test case IDs for a specific flow type.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            flow_type: Flow type name
            
        Returns:
            List of test case IDs
        """
        matching_ids = []
        
        for test_id, test_case in test_cases.items():
            flows = self.flow_analyzer.identify_flow_type(test_case)
            if flow_type in flows:
                matching_ids.append(test_id)
        
        return matching_ids

