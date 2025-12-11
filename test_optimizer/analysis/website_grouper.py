"""
Module for grouping test cases by website/domain.
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from urllib.parse import urlparse
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase, TestStep


class WebsiteGrouper:
    """Groups test cases by website/domain for role-aware merging."""
    
    def __init__(self):
        """Initialize website grouper."""
        pass
    
    def extract_website(
        self,
        test_case: TestCase
    ) -> str:
        """
        Extract website/domain identifier from test case.
        
        Args:
            test_case: The TestCase object
            
        Returns:
            Website identifier (e.g., "orangehrm", "salesforce", "ecommerce")
        """
        # Extract URLs from steps
        urls = self._extract_urls_from_steps(test_case.steps)
        
        # Extract from name/description
        text = f"{test_case.name} {test_case.description or ''}".lower()
        
        # Try to extract domain from URLs
        domains = set()
        for url in urls:
            domain = self.normalize_website(url)
            if domain:
                domains.add(domain)
        
        # If no URLs found, try to extract from text
        if not domains:
            # Look for common website patterns in text
            website_patterns = {
                "orangehrmlive": ["orangehrm", "orange hrm", "ohrm"],  # Normalize to orangehrmlive
                "salesforce": ["salesforce", "sfdc"],
                "ecommerce": ["ecommerce", "e-commerce", "shop", "store"],
                "amazon": ["amazon"],
                "airbnb": ["airbnb", "air bnb"]
            }
            
            for website, patterns in website_patterns.items():
                if any(pattern in text for pattern in patterns):
                    domains.add(website)
                    break
        
        if domains:
            return list(domains)[0]  
        
        return "unknown"
    
    def normalize_website(
        self,
        url: str
    ) -> str:
        """
        Normalize URL to extract domain identifier.
        
        Args:
            url: URL string
            
        Returns:
            Normalized domain identifier (e.g., "orangehrm", "salesforce")
        """
        if not url:
            return "unknown"
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            
            if domain.startswith("www."):
                domain = domain[4:]
            
            
            parts = domain.split(".")
            
            if len(parts) >= 2:
                main_domain = parts[-2] if len(parts) >= 2 else parts[0]
                
                # Map common domains
                # CRITICAL: Normalize all OrangeHRM variants to "orangehrmlive" for consistency
                domain_mapping = {
                    "orangehrm": "orangehrmlive",  # Normalize to orangehrmlive
                    "orangehrmlive": "orangehrmlive",  # Keep as is
                    "ohrm": "orangehrmlive",  # Normalize to orangehrmlive
                    "salesforce": "salesforce",
                    "sfdc": "salesforce",
                    "force": "salesforce",  # CRITICAL: lightning.force.com is Salesforce
                    "amazon": "amazon",
                    "airbnb": "airbnb",
                    "demo": "demo"  
                }
                
                main_domain_lower = main_domain.lower()
                if main_domain_lower in domain_mapping:
                    return domain_mapping[main_domain_lower]
                
                return main_domain_lower
            
            return domain.lower() if domain else "unknown"
        
        except Exception:
            return "unknown"
    
    def _extract_urls_from_steps(
        self,
        steps: List[TestStep]
    ) -> List[str]:
        """Extract URLs from test steps."""
        urls = []
        for step in steps:
            # Check test_data
            if step.test_data:
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                matches = re.findall(url_pattern, step.test_data)
                urls.extend(matches)
            
            # Check action
            if step.action:
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                matches = re.findall(url_pattern, step.action)
                urls.extend(matches)
            
            # Check description
            if step.description:
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                matches = re.findall(url_pattern, step.description)
                urls.extend(matches)
        
        return list(set(urls))  
    
    def group_by_website(
        self,
        test_cases: Dict[int, TestCase]
    ) -> Dict[str, List[int]]:
        """
        Group test cases by website/domain.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Dictionary mapping website identifier to list of test case IDs
        """
        groups = {}
        for test_id, test_case in test_cases.items():
            website = self.extract_website(test_case)
            if website not in groups:
                groups[website] = []
            groups[website].append(test_id)
        
        return groups
    
    def group_by_role_and_website(
        self,
        test_cases: Dict[int, TestCase],
        role_classifications: Dict[int, str]
    ) -> Dict[Tuple[str, str], List[int]]:
        """
        Group test cases by (role, website) tuple.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            role_classifications: Dictionary mapping test case ID to role
            
        Returns:
            Dictionary mapping (role, website) tuple to list of test case IDs
        """
        groups = {}
        for test_id, test_case in test_cases.items():
            role = role_classifications.get(test_id, "unknown")
            website = self.extract_website(test_case)
            key = (role, website)
            if key not in groups:
                groups[key] = []
            groups[key].append(test_id)
        
        return groups
    
    def get_website_statistics(
        self,
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Get statistics about website distribution.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Statistics dictionary
        """
        groups = self.group_by_website(test_cases)
        
        return {
            "total": len(test_cases),
            "websites": len(groups),
            "groups": {website: len(test_ids) for website, test_ids in groups.items()},
            "distribution": groups
        }
    
    def get_role_website_statistics(
        self,
        test_cases: Dict[int, TestCase],
        role_classifications: Dict[int, str]
    ) -> Dict:
        """
        Get statistics about (role, website) distribution.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            role_classifications: Dictionary mapping test case ID to role
            
        Returns:
            Statistics dictionary
        """
        groups = self.group_by_role_and_website(test_cases, role_classifications)
        
        return {
            "total": len(test_cases),
            "groups": len(groups),
            "distribution": {
                f"{role}_{website}": len(test_ids) 
                for (role, website), test_ids in groups.items()
            },
            "detailed_groups": groups
        }

