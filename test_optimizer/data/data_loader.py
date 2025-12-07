"""
Module for loading and parsing test case data from JSON files.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from .models import TestCase, TestStep
from .normalizers import (
    normalize_action_name,
    normalize_element_identifier,
    clean_description,
    normalize_locator,
    normalize_test_data
)


class DataLoader:
    """Loads and parses test case data from JSON files."""
    
    def __init__(self, test_cases_dir: str, steps_dir: str):
        """
        Initialize the data loader.
        
        Args:
            test_cases_dir: Path to directory containing test case JSON files
            steps_dir: Path to directory containing test step JSON files
        """
        self.test_cases_dir = Path(test_cases_dir)
        self.steps_dir = Path(steps_dir)
        self.test_cases: Dict[int, TestCase] = {}
        self.load_errors: List[Tuple[int, str]] = []
    
    def load_all(self) -> Dict[int, TestCase]:
        """
        Load all test cases and their steps.
        
        Returns:
            Dictionary mapping test case IDs to TestCase objects
        """
        print(f"  [DATA LOADER] Discovering test case IDs...")
        # First, find all available test case IDs
        test_case_ids = self._discover_test_case_ids()
        print(f"  [DATA LOADER] Found {len(test_case_ids)} test case IDs: {test_case_ids[:10]}{'...' if len(test_case_ids) > 10 else ''}")
        
        # Load test cases
        print(f"  [DATA LOADER] Loading {len(test_case_ids)} test cases...")
        for idx, test_case_id in enumerate(test_case_ids, 1):
            try:
                print(f"    [{idx}/{len(test_case_ids)}] Loading test case {test_case_id:02d}...", end=" ")
                test_case = self.load_test_case(test_case_id)
                if test_case:
                    self.test_cases[test_case_id] = test_case
                    print(f"✓ Loaded (name: '{test_case.name[:50]}...', {len(test_case.steps)} steps)")
                else:
                    print(f"✗ Failed (not found)")
            except Exception as e:
                error_msg = f"Error loading test case {test_case_id}: {str(e)}"
                self.load_errors.append((test_case_id, error_msg))
                print(f"✗ Error: {str(e)}")
        
        print(f"  [DATA LOADER] ✓ Successfully loaded {len(self.test_cases)}/{len(test_case_ids)} test cases")
        if self.load_errors:
            print(f"  [DATA LOADER] ⚠ {len(self.load_errors)} errors occurred")
        
        return self.test_cases
    
    def _discover_test_case_ids(self) -> List[int]:
        """
        Discover all available test case IDs from both directories.
        
        Returns:
            List of test case IDs found
        """
        test_case_ids = set()
        
        # Check test_cases directory
        if self.test_cases_dir.exists():
            for file_path in self.test_cases_dir.glob("*.json"):
                try:
                    # Extract ID from filename (e.g., "01.json" -> 1)
                    test_id = int(file_path.stem)
                    test_case_ids.add(test_id)
                except ValueError:
                    continue
        
        # Check steps directory
        if self.steps_dir.exists():
            for file_path in self.steps_dir.glob("*.json"):
                try:
                    test_id = int(file_path.stem)
                    test_case_ids.add(test_id)
                except ValueError:
                    continue
        
        return sorted(list(test_case_ids))
    
    def load_test_case(self, test_case_id: int) -> Optional[TestCase]:
        """
        Load a single test case with its steps.
        
        Args:
            test_case_id: The test case ID to load
            
        Returns:
            TestCase object or None if not found
        """
        # Load test case metadata
        test_case_data = self._load_test_case_metadata(test_case_id)
        if not test_case_data:
            return None
        
        # Load test steps
        steps = self._load_test_steps(test_case_id)
        
        # Create TestCase object
        test_case = self._parse_test_case(test_case_data, steps)
        return test_case
    
    def _load_test_case_metadata(self, test_case_id: int) -> Optional[Dict]:
        """Load test case metadata from JSON file."""
        file_path = self.test_cases_dir / f"{test_case_id:02d}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading test case metadata for {test_case_id}: {e}")
            return None
    
    def _load_test_steps(self, test_case_id: int) -> List[Dict]:
        """Load test steps from JSON file."""
        file_path = self.steps_dir / f"{test_case_id:02d}.json"
        
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Steps are in the "content" array
                if isinstance(data, dict) and "content" in data:
                    return data["content"]
                return []
        except Exception as e:
            print(f"Error loading test steps for {test_case_id}: {e}")
            return []
    
    def _parse_test_case(self, test_case_data: Dict, steps_data: List[Dict]) -> TestCase:
        """Parse test case data into TestCase object."""
        # Extract lastRun information if available
        last_run = test_case_data.get("lastRun")
        duration = None
        pass_count = None
        fail_count = None
        last_run_result = None
        
        if last_run:
            duration = last_run.get("duration")
            pass_count = last_run.get("passedCount")
            fail_count = last_run.get("failedCount")
            last_run_result = last_run.get("result")
        
        # Parse steps
        test_steps = []
        for step_data in steps_data:
            step = self._parse_test_step(step_data)
            if step:
                test_steps.append(step)
        
        # Sort steps by position
        test_steps.sort(key=lambda s: s.position)
        
        # Create TestCase
        test_case = TestCase(
            id=test_case_data.get("id"),
            name=test_case_data.get("name", ""),
            description=clean_description(test_case_data.get("description")),
            priority=test_case_data.get("priority"),
            status=test_case_data.get("status"),
            duration=duration,
            pass_count=pass_count,
            fail_count=fail_count,
            tags=test_case_data.get("tags", []),
            steps=test_steps,
            prerequisite_case=test_case_data.get("preRequisiteCase"),
            test_data_id=test_case_data.get("testDataId"),
            last_run_result=last_run_result,
            created_date=test_case_data.get("createdDate"),
            updated_date=test_case_data.get("updatedDate"),
            raw_data=test_case_data
        )
        
        return test_case
    
    def _parse_test_step(self, step_data: Dict) -> Optional[TestStep]:
        """Parse step data into TestStep object."""
        # Skip step groups for now (we can handle them later if needed)
        step_type = step_data.get("type")
        if step_type == "STEP_GROUP":
            return None
        
        # Extract locator information
        event = step_data.get("event", {})
        locator = None
        if isinstance(event, dict):
            locator = normalize_locator(event.get("locator"))
            if not locator:
                # Try to get locator from other fields
                if "selector" in event:
                    locator = {"selector": event["selector"]}
                elif "label" in event:
                    locator = {"label": event["label"]}
        
        test_data = normalize_test_data(step_data.get("testData"))
        
        step = TestStep(
            id=step_data.get("id"),
            position=step_data.get("position", 0),
            action_name=normalize_action_name(step_data.get("actionName", "")),
            action=step_data.get("action", ""),
            element=normalize_element_identifier(step_data.get("element")),
            description=clean_description(step_data.get("description")),
            locator=locator,
            test_data=test_data,
            wait_time=step_data.get("waitTime"),
            test_case_id=step_data.get("testCaseId"),
            raw_data=step_data
        )
        
        return step
    
    def get_load_summary(self) -> Dict:
        """Get a summary of the loading process."""
        return {
            "total_test_cases_loaded": len(self.test_cases),
            "total_steps_loaded": sum(len(tc.steps) for tc in self.test_cases.values()),
            "load_errors": len(self.load_errors),
            "error_details": self.load_errors
        }

