"""
Module for classifying test cases by role
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase, TestStep


class RoleClassifier:
    """Classifies test cases as admin or user based on multiple indicators."""
    
    def __init__(self):
        """Initialize role classifier with indicators."""
        # Admin indicators
        self.admin_keywords = [
            "admin", "administrator", "system user", "manage", "management",
            "delete user", "create user", "add user", "remove user",
            "user management", "system settings", "system configuration",
            "permissions", "roles", "access control", "system admin"
        ]
        
        self.admin_actions = [
            "deleteuser", "createuser", "adduser", "removeuser",
            "manageusers", "managesystem", "systemsettings",
            "permissions", "roles", "accesscontrol", "adminpanel"
        ]
        
        self.admin_url_patterns = [
            r"/admin", r"/administrator", r"/management", r"/system",
            r"/admin/", r"/manage/", r"/system/", r"/settings"
        ]
        
        self.admin_element_patterns = [
            "admin", "administrator", "management", "system",
            "user management", "admin panel", "system settings"
        ]
        
        # User indicators
        self.user_keywords = [
            "user", "customer", "employee", "login", "profile",
            "dashboard", "my account", "my profile", "personal",
            "settings", "preferences", "account settings"
        ]
        
        self.user_actions = [
            "login", "logout", "viewprofile", "updateprofile",
            "editprofile", "changepassword", "myaccount"
        ]
        
        self.user_url_patterns = [
            r"/user", r"/customer", r"/dashboard", r"/profile",
            r"/my", r"/account", r"/settings", r"/preferences"
        ]
        
        self.user_element_patterns = [
            "user", "customer", "profile", "dashboard", "account",
            "my account", "personal", "settings"
        ]
    
    def classify_role(
        self,
        test_case: TestCase
    ) -> str:
        """
        Classify test case as admin or user.
        
        Args:
            test_case: The TestCase object to classify
            
        Returns:
            "admin", "user", or "unknown"
        """
        indicators = self.extract_role_indicators(test_case)
        confidence = self.get_role_confidence(test_case, indicators)
        
        if confidence["admin_confidence"] >= 0.6:
            return "admin"
        elif confidence["user_confidence"] >= 0.6:
            return "user"
        else:
            return "unknown"
    
    def is_admin_test_case(
        self,
        test_case: TestCase
    ) -> bool:
        """
        Check if test case is an admin test case.
        
        Args:
            test_case: The TestCase object
            
        Returns:
            True if admin, False otherwise
        """
        return self.classify_role(test_case) == "admin"
    
    def extract_role_indicators(
        self,
        test_case: TestCase
    ) -> Dict:
        """
        Extract role indicators from test case.
        
        Args:
            test_case: The TestCase object
            
        Returns:
            Dictionary of role indicators
        """
        # Combine name and description
        text = f"{test_case.name} {test_case.description or ''}".lower()
        
        # Extract URLs from steps
        urls = self._extract_urls_from_steps(test_case.steps)
        
        # Extract actions from steps
        actions = [step.action_name.lower() for step in test_case.steps]
        
        # Extract elements from steps
        elements = self._extract_elements_from_steps(test_case.steps)
        
        # Count admin indicators
        admin_keyword_count = sum(1 for keyword in self.admin_keywords if keyword in text)
        admin_action_count = sum(1 for action in actions if any(admin_action in action for admin_action in self.admin_actions))
        admin_url_count = sum(1 for url in urls if any(re.search(pattern, url, re.IGNORECASE) for pattern in self.admin_url_patterns))
        admin_element_count = sum(1 for elem in elements if any(pattern in elem for pattern in self.admin_element_patterns))
        
        # Count user indicators
        user_keyword_count = sum(1 for keyword in self.user_keywords if keyword in text)
        user_action_count = sum(1 for action in actions if any(user_action in action for user_action in self.user_actions))
        user_url_count = sum(1 for url in urls if any(re.search(pattern, url, re.IGNORECASE) for pattern in self.user_url_patterns))
        user_element_count = sum(1 for elem in elements if any(pattern in elem for pattern in self.user_element_patterns))
        
        return {
            "admin": {
                "keywords": admin_keyword_count,
                "actions": admin_action_count,
                "urls": admin_url_count,
                "elements": admin_element_count,
                "total": admin_keyword_count + admin_action_count + admin_url_count + admin_element_count
            },
            "user": {
                "keywords": user_keyword_count,
                "actions": user_action_count,
                "urls": user_url_count,
                "elements": user_element_count,
                "total": user_keyword_count + user_action_count + user_url_count + user_element_count
            },
            "urls": urls,
            "actions": actions,
            "elements": elements
        }
    
    def get_role_confidence(
        self,
        test_case: TestCase,
        indicators: Optional[Dict] = None
    ) -> Dict:
        """
        Get confidence scores for role classification.
        
        Args:
            test_case: The TestCase object
            indicators: Optional pre-computed indicators (for efficiency)
            
        Returns:
            Dictionary with admin_confidence and user_confidence (0.0 to 1.0)
        """
        if indicators is None:
            indicators = self.extract_role_indicators(test_case)
        
        admin_total = indicators["admin"]["total"]
        user_total = indicators["user"]["total"]
        total_indicators = admin_total + user_total
        
        if total_indicators == 0:
            return {
                "admin_confidence": 0.0,
                "user_confidence": 0.3, 
                "classification": "unknown"
            }
        
        admin_confidence = admin_total / total_indicators if total_indicators > 0 else 0.0
        user_confidence = user_total / total_indicators if total_indicators > 0 else 0.0
        
        if indicators["admin"]["keywords"] > 0 and indicators["admin"]["actions"] > 0:
            admin_confidence = min(1.0, admin_confidence + 0.2)
        if indicators["user"]["keywords"] > 0 and indicators["user"]["actions"] > 0:
            user_confidence = min(1.0, user_confidence + 0.2)
        
        # Determine classification
        if admin_confidence >= 0.6:
            classification = "admin"
        elif user_confidence >= 0.6:
            classification = "user"
        else:
            classification = "unknown"
        
        return {
            "admin_confidence": admin_confidence,
            "user_confidence": user_confidence,
            "classification": classification,
            "indicators": indicators
        }
    
    def _extract_urls_from_steps(
        self,
        steps: List[TestStep]
    ) -> List[str]:
        """Extract URLs from test steps."""
        urls = []
        for step in steps:
            # Check test_data
            if step.test_data and ("http://" in step.test_data or "https://" in step.test_data):
                urls.append(step.test_data)
            
            text = f"{step.action} {step.description or ''}"
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            matches = re.findall(url_pattern, text)
            urls.extend(matches)
        
        return list(set(urls)) 
    
    def _extract_elements_from_steps(
        self,
        steps: List[TestStep]
    ) -> List[str]:
        """Extract element identifiers from test steps."""
        elements = []
        for step in steps:
            if step.element:
                elements.append(step.element.lower().strip())
            
            if step.locator:
                if isinstance(step.locator, dict):
                    for key in ["label", "id", "name", "placeholder", "xpath", "selector"]:
                        if key in step.locator:
                            value = str(step.locator[key]).lower().strip()
                            elements.append(value)
        
        return elements
    
    def classify_test_cases(
        self,
        test_cases: Dict[int, TestCase]
    ) -> Dict[int, str]:
        """
        Classify multiple test cases by role.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Dictionary mapping test case ID to role ("admin", "user", or "unknown")
        """
        classifications = {}
        for test_id, test_case in test_cases.items():
            role = self.classify_role(test_case)
            classifications[test_id] = role
        
        return classifications
    
    def get_role_statistics(
        self,
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Get statistics about role distribution.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Statistics dictionary
        """
        classifications = self.classify_test_cases(test_cases)
        
        admin_count = sum(1 for role in classifications.values() if role == "admin")
        user_count = sum(1 for role in classifications.values() if role == "user")
        unknown_count = sum(1 for role in classifications.values() if role == "unknown")
        
        return {
            "total": len(test_cases),
            "admin": admin_count,
            "user": user_count,
            "unknown": unknown_count,
            "admin_percentage": (admin_count / len(test_cases) * 100) if test_cases else 0.0,
            "user_percentage": (user_count / len(test_cases) * 100) if test_cases else 0.0,
            "unknown_percentage": (unknown_count / len(test_cases) * 100) if test_cases else 0.0,
            "classifications": classifications
        }

