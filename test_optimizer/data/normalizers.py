"""
Utilities for normalizing test case data.
"""

import re
from typing import Optional, Dict, Any


def normalize_action_name(action_name: str) -> str:
    """
    Normalize action names to lowercase.
    
    Args:
        action_name: The action name to normalize
        
    Returns:
        Normalized action name in lowercase
    """
    if not action_name:
        return ""
    return action_name.lower().strip()


def normalize_element_identifier(element: Optional[str]) -> Optional[str]:
    """
    Normalize element identifiers (case-insensitive).
    
    Args:
        element: The element identifier to normalize
        
    Returns:
        Normalized element identifier or None
    """
    if not element:
        return None
    return element.strip()


def extract_url_from_navigate_to(step_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract and normalize URL from navigateTo action.
    
    Args:
        step_data: The step data dictionary
        
    Returns:
        Normalized URL or None
    """
    # Check testData field
    test_data = step_data.get("testData")
    if test_data and isinstance(test_data, str) and test_data.startswith("http"):
        return test_data.strip()
    
    # Check event.href field
    event = step_data.get("event", {})
    if isinstance(event, dict):
        href = event.get("href")
        if href and isinstance(href, str) and href.startswith("http"):
            return href.strip()
    
    # Check action field
    action = step_data.get("action")
    if action and isinstance(action, str):
        # Try to extract URL from action text
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        match = re.search(url_pattern, action)
        if match:
            return match.group(0).strip()
    
    return None


def clean_description(description: Optional[str]) -> Optional[str]:
    """
    Clean and normalize description text.
    
    Args:
        description: The description to clean
        
    Returns:
        Cleaned description or None
    """
    if not description:
        return None
    
    # Remove HTML tags if present
    description = re.sub(r'<[^>]+>', '', description)
    
    # Normalize whitespace
    description = re.sub(r'\s+', ' ', description)
    
    # Strip leading/trailing whitespace
    description = description.strip()
    
    return description if description else None


def normalize_locator(locator: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Normalize locator information.
    
    Args:
        locator: The locator dictionary
        
    Returns:
        Normalized locator dictionary or None
    """
    if not locator or not isinstance(locator, dict):
        return None
    
    normalized = {}
    
    # Normalize common locator fields
    for key in ["xpath", "selector", "label", "placeholder", "id", "name", "class"]:
        if key in locator:
            value = locator[key]
            if isinstance(value, str):
                normalized[key] = value.strip()
            else:
                normalized[key] = value
    
    return normalized if normalized else None


def normalize_test_data(test_data: Optional[Any]) -> Optional[str]:
    """
    Normalize test data to string format.
    
    Args:
        test_data: The test data to normalize
        
    Returns:
        Normalized test data as string or None
    """
    if test_data is None:
        return None
    
    if isinstance(test_data, str):
        return test_data.strip()
    
    if isinstance(test_data, (int, float, bool)):
        return str(test_data)
    
    if isinstance(test_data, dict):
        # For complex test data, return a string representation
        return str(test_data)
    
    return None

