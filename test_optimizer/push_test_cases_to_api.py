#!/usr/bin/env python3
"""
Script to push merged test cases to ContextQA API.
Converts optimized test cases to API format and POSTs them.
"""

import json
import sys
import requests
from pathlib import Path
from typing import Dict, List, Optional

# API Configuration
API_URL = "https://server.contextqa.com/test_cases"
AUTHORIZATION_TOKEN = "Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJkZWVwY3FhX2FydW4iLCJleHAiOjE3NjU0MzY3MDIsImlhdCI6MTc2NTM1MDMwMiwidGVuYW50IjoiYXJ1biJ9.ncBejuxmaZKaJfEPh3Ign6tnStTrq3YgJ3iv8PBNsomBlcRhCrwziZ2w0S4ylsttpgiZMdk4NiNLg4asqJu9Zg"

# Additional headers required by API
API_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "authorization": AUTHORIZATION_TOKEN,
    "content-type": "application/json",
    "cqa-origin": "https://arun.contextqa.com/api",
    "origin": "https://arun.contextqa.com",
    "referer": "https://arun.contextqa.com/"
}

# Output directories
OUTPUT_DIR = Path("json-data/output")
TEST_CASES_DIR = OUTPUT_DIR / "test_cases"
STEPS_DIR = OUTPUT_DIR / "steps_in_test_cases"


def load_test_case(test_case_id: int) -> Optional[Dict]:
    """Load test case JSON file."""
    file_path = TEST_CASES_DIR / f"{test_case_id:02d}.json"
    if not file_path.exists():
        file_path = TEST_CASES_DIR / f"{test_case_id}.json"
    
    if not file_path.exists():
        print(f"  ✗ Test case file not found: {file_path}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  ✗ Error loading test case: {e}")
        return None


def load_steps(test_case_id: int) -> List[Dict]:
    """Load steps JSON file."""
    file_path = STEPS_DIR / f"{test_case_id:02d}.json"
    if not file_path.exists():
        file_path = STEPS_DIR / f"{test_case_id}.json"
    
    if not file_path.exists():
        print(f"  ✗ Steps file not found: {file_path}")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Handle both formats: {"content": [...]} and direct array
            if isinstance(data, dict) and "content" in data:
                return data["content"]
            elif isinstance(data, list):
                return data
            else:
                print(f"  ✗ Unexpected steps format")
                return []
    except Exception as e:
        print(f"  ✗ Error loading steps: {e}")
        return []


def convert_step_to_api_format(step: Dict, position: int) -> Dict:
    """
    Convert step from output format to API format.
    
    API format expects:
    - actionName
    - naturalTextActionId
    - name (for navigateToUrl)
    - event (with customEvent, href, etc.)
    - action
    - testData
    - position
    - type
    """
    api_step = {
        "position": position,
        "type": step.get("type", "ACTION_TEXT"),
        "disabled": step.get("disabled", False),
        "ignoreStepResult": step.get("ignoreStepResult", False),
        "visualEnabled": step.get("visualEnabled", False),
    }
    
    # Map actionName
    action_name = step.get("actionName", "")
    api_step["actionName"] = action_name
    
    # Map naturalTextActionId (required for API)
    natural_text_action_id = step.get("naturalTextActionId")
    if natural_text_action_id:
        api_step["naturalTextActionId"] = natural_text_action_id
    else:
        # Try to infer from actionName if not present
        # This is a fallback - ideally should be in the data
        action_id_map = {
            "navigateTo": 425,  # navigateToUrl
            "click": 1,
            "enter": 2,
            "verify": 3,
        }
        if action_name.lower() in action_id_map:
            api_step["naturalTextActionId"] = action_id_map[action_name.lower()]
    
    # Map action text
    if "action" in step:
        api_step["action"] = step["action"]
    
    # Map testData
    if "testData" in step and step["testData"]:
        api_step["testData"] = step["testData"]
    
    # Map event - this is critical for API
    # Copy ALL event fields to preserve element locators, selectors, labels, etc.
    event = step.get("event", {})
    api_event = {}
    
    # Special handling for navigateTo/navigateToUrl
    if action_name == "navigateTo" or action_name == "navigateToUrl":
        api_event["customEvent"] = "navigateToUrl"
        # Extract URL from event.href or testData
        url = event.get("href") or step.get("testData")
        if url:
            api_event["href"] = url
            api_step["name"] = url  # API expects "name" field with URL for navigateToUrl
        # Copy other navigation-related fields
        for key in ["action", "control", "type", "signals"]:
            if key in event:
                api_event[key] = event[key]
    else:
        # For all other actions, copy ALL event fields to preserve element information
        # This includes: label, locator, selector, pwLocator, parsedSelector, value, button, clickCount, etc.
        api_event = event.copy()  # Copy entire event object to preserve all element data
    
    # Always include event (API expects it)
    api_step["event"] = api_event
    
    # Map element if present
    if "element" in step and step["element"]:
        api_step["element"] = step["element"]
    
    return api_step


def convert_test_case_to_api_format(test_case: Dict, steps: List[Dict]) -> Dict:
    """
    Convert test case from output format to API format.
    
    API format expects:
    - isExtensionUsed
    - name
    - description
    - status
    - sendMailNotification
    - isStepGroup
    - priorityId (not priority)
    - type
    - isDataDriven
    - workspaceVersionId
    - deleted
    - testDataStartIndex
    - tags
    - steps (array of step objects)
    - testcaseTimeout
    - testType
    - isCrawl
    """
    
    # Map priority to priorityId
    priority = test_case.get("priority", 1)
    priority_id = priority if priority else 1
    
    # Map status
    status = test_case.get("status", "READY")
    # Convert status if needed
    status_map = {
        "READY": "READY",
        "IN_REVIEW": "IN_REVIEW",
        "DRAFT": "DRAFT"
    }
    api_status = status_map.get(status, "READY")
    
    # Convert steps
    api_steps = []
    for idx, step in enumerate(sorted(steps, key=lambda s: s.get("position", 0))):
        api_step = convert_step_to_api_format(step, idx)
        api_steps.append(api_step)
    
    # Build API payload
    api_payload = {
        "isExtensionUsed": False,
        "name": test_case.get("name", "Unnamed Test Case"),
        "description": test_case.get("description"),
        "status": api_status,
        "sendMailNotification": False,
        "isStepGroup": False,
        "priorityId": priority_id,
        "type": test_case.get("type", 1),
        "isDataDriven": False,
        "workspaceVersionId": test_case.get("workspaceVersionId", 1),
        "deleted": False,
        "testDataStartIndex": 0,
        "tags": test_case.get("tags", []),
        "steps": api_steps,
        "testcaseTimeout": 20,
        "testType": "BROWSER",
        "isCrawl": False
    }
    
    return api_payload


def push_test_case_to_api(test_case_id: int, dry_run: bool = False) -> bool:
    """
    Load, convert, and push a test case to the API.
    
    Args:
        test_case_id: Test case ID to push
        dry_run: If True, only print the payload without sending
        
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"Processing TC {test_case_id}")
    print(f"{'='*80}")
    
    # Load test case
    print(f"  Loading test case...")
    test_case = load_test_case(test_case_id)
    if not test_case:
        return False
    
    print(f"    ✓ Loaded: {test_case.get('name', 'Unknown')}")
    
    # Load steps
    print(f"  Loading steps...")
    steps = load_steps(test_case_id)
    if not steps:
        print(f"    ⚠ No steps found")
        return False
    
    print(f"    ✓ Loaded {len(steps)} steps")
    
    # Convert to API format
    print(f"  Converting to API format...")
    api_payload = convert_test_case_to_api_format(test_case, steps)
    print(f"    ✓ Converted ({len(api_payload['steps'])} steps)")
    
    if dry_run:
        print(f"\n  [DRY RUN] Would send payload:")
        print(json.dumps(api_payload, indent=2, ensure_ascii=False)[:500] + "...")
        return True
    
    # Push to API
    print(f"  Pushing to API...")
    try:
        # Use the updated headers with all required fields
        response = requests.post(
            API_URL,
            headers=API_HEADERS,
            json=api_payload,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            print(f"    ✓ Successfully pushed! Status: {response.status_code}")
            try:
                result = response.json()
                if "id" in result:
                    print(f"    ✓ Created test case ID: {result['id']}")
                print(f"    Response: {json.dumps(result, indent=2)[:200]}...")
            except:
                print(f"    Response: {response.text[:200]}...")
            return True
        else:
            print(f"    ✗ Failed! Status: {response.status_code}")
            print(f"    Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"    ✗ Error pushing to API: {e}")
        return False


def main():
    """Main function."""
    print("="*80)
    print("PUSH MERGED TEST CASES TO CONTEXTQA API")
    print("="*80)
    
    # Find merged OrangeHRM test case automatically
    from data.data_loader import DataLoader
    from analysis.website_grouper import WebsiteGrouper
    
    loader = DataLoader(
        test_cases_dir='json-data/output/test_cases',
        steps_dir='json-data/output/steps_in_test_cases'
    )
    test_cases = loader.load_all()
    grouper = WebsiteGrouper()
    
    # Find largest merged OrangeHRM test case
    merged_orangehrm = []
    for tc_id, tc in test_cases.items():
        website = grouper.extract_website(tc)
        if 'orangehrm' in website.lower():
            is_merged = ('merged' in tc.name.lower() or 
                        'consolidated' in tc.name.lower() or
                        len(tc.steps) > 50)
            if is_merged:
                merged_orangehrm.append((tc_id, len(tc.steps)))
    
    if merged_orangehrm:
        # Get the largest merged test case
        largest = max(merged_orangehrm, key=lambda x: x[1])
        test_case_ids = [largest[0]]
        print(f"\nFound merged OrangeHRM test case: TC {largest[0]} ({largest[1]} steps)")
    else:
        print("\n⚠ No merged OrangeHRM test case found")
        test_case_ids = []
    
    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-d" in sys.argv
    
    if dry_run:
        print("\n⚠ DRY RUN MODE - No data will be sent to API")
    
    results = []
    for tc_id in test_case_ids:
        success = push_test_case_to_api(tc_id, dry_run=dry_run)
        results.append((tc_id, success))
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    for tc_id, success in results:
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"  TC {tc_id}: {status}")
    
    success_count = sum(1 for _, s in results if s)
    print(f"\n  Total: {success_count}/{len(results)} test cases pushed successfully")


if __name__ == "__main__":
    main()

