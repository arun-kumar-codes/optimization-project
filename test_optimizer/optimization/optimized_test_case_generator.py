"""
Module for generating new optimized test cases with proper IDs and metadata.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import hashlib
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase, TestStep


class OptimizedTestCaseGenerator:
    """Generates new optimized test cases with proper IDs and metadata."""
    
    def __init__(self, start_id_range: int = 1000):
        """
        Initialize optimized test case generator.
        
        Args:
            start_id_range: Starting ID range for new test cases (default: 1000)
        """
        self.start_id_range = start_id_range
        self._used_ids: Set[int] = set()
    
    def generate_optimized_test_cases(
        self,
        optimization_result: Dict,
        original_test_cases: Dict[int, TestCase],
        merged_test_cases: Optional[Dict[int, TestCase]] = None
    ) -> Dict[int, TestCase]:
        """
        Generate new optimized test cases from optimization results.
        
        Args:
            optimization_result: Result from optimization engine
            original_test_cases: Original test cases
            merged_test_cases: Optional pre-merged test cases
            
        Returns:
            Dictionary of new optimized test cases
        """
        optimized_test_cases = {}
        
        # Get existing IDs to avoid conflicts
        existing_ids = set(original_test_cases.keys())
        if merged_test_cases:
            existing_ids.update(merged_test_cases.keys())
        
        # Process merged test cases
        if merged_test_cases:
            for merged_id, merged_tc in merged_test_cases.items():
                # Ensure ID doesn't conflict
                final_id = self._ensure_unique_id(merged_id, existing_ids)
                if final_id != merged_id:
                    # Update ID in test case
                    merged_tc.id = final_id
                
                optimized_test_cases[final_id] = merged_tc
                existing_ids.add(final_id)
        
        # Process kept test cases (they keep their original IDs)
        kept_ids = optimization_result.get("test_cases_kept", [])
        for test_id in kept_ids:
            if test_id in original_test_cases:
                optimized_test_cases[test_id] = original_test_cases[test_id]
        
        return optimized_test_cases
    
    def create_merged_test_case(
        self,
        source_test_cases: List[TestCase],
        merged_data: Optional[Dict] = None
    ) -> TestCase:
        """
        Create TestCase from merged data.
        
        Args:
            source_test_cases: List of source test cases
            merged_data: Optional merged data dictionary
            
        Returns:
            Merged TestCase object
        """
        if len(source_test_cases) == 0:
            raise ValueError("Cannot create merged test case from empty list")
        
        if len(source_test_cases) == 1:
            return source_test_cases[0]
        
        # Generate new ID
        source_ids = [tc.id for tc in source_test_cases]
        new_id = self.assign_new_test_case_id(source_ids)
        
        # Merge steps (use first test case's steps as base, add unique from others)
        merged_steps = []
        seen_step_signatures = set()
        
        for tc in source_test_cases:
            for step in sorted(tc.steps, key=lambda s: s.position):
                step_sig = self._get_step_signature(step)
                if step_sig not in seen_step_signatures:
                    # Create new step with updated position
                    new_step = TestStep(
                        id=step.id,
                        position=len(merged_steps) + 1,
                        action_name=step.action_name,
                        action=step.action,
                        element=step.element,
                        description=step.description,
                        locator=step.locator,
                        test_data=step.test_data,
                        wait_time=step.wait_time,
                        test_case_id=new_id,
                        raw_data=step.raw_data
                    )
                    merged_steps.append(new_step)
                    seen_step_signatures.add(step_sig)
        
        # Generate metadata
        metadata = self.generate_test_case_metadata(
            source_test_cases[0],
            source_ids
        )
        
        # Create merged test case
        merged_test_case = TestCase(
            id=new_id,
            name=merged_data.get("name") if merged_data else f"Merged: {source_test_cases[0].name}",
            description=merged_data.get("description") if merged_data else self._create_merged_description(source_test_cases),
            priority=min(tc.priority or 5 for tc in source_test_cases),
            status=source_test_cases[0].status or "READY",
            duration=sum(tc.duration or 0 for tc in source_test_cases),
            pass_count=source_test_cases[0].pass_count,
            fail_count=source_test_cases[0].fail_count,
            tags=list(set(tag for tc in source_test_cases for tag in (tc.tags or []))),
            steps=merged_steps,
            prerequisite_case=source_test_cases[0].prerequisite_case,
            test_data_id=source_test_cases[0].test_data_id,
            last_run_result=source_test_cases[0].last_run_result,
            created_date=min(tc.created_date or 0 for tc in source_test_cases if tc.created_date) or None,
            updated_date=int(datetime.now().timestamp() * 1000),
            raw_data={
                "optimizationSource": "merged",
                "sourceTestCases": source_ids,
                "optimizationDate": int(datetime.now().timestamp() * 1000),
                "optimizationReason": "Merged similar test cases to preserve unique steps",
                "mergedMetadata": metadata,
                "originalRawData": [tc.raw_data for tc in source_test_cases if tc.raw_data]
            }
        )
        
        return merged_test_case
    
    def create_ai_optimized_test_case(
        self,
        ai_response: Dict,
        source_test_case: Optional[TestCase] = None
    ) -> TestCase:
        """
        Convert AI response to TestCase object.
        
        Args:
            ai_response: AI response dictionary
            source_test_case: Optional source test case for metadata
            
        Returns:
            TestCase object
        """
        # Generate new ID
        source_id = source_test_case.id if source_test_case else None
        new_id = self.assign_new_test_case_id([source_id] if source_id else [])
        
        # Create steps from AI response
        steps_data = ai_response.get("optimized_steps", ai_response.get("steps", []))
        steps = []
        
        for i, step_data in enumerate(steps_data, start=1):
            step = TestStep(
                id=step_data.get("id", i * 1000),
                position=step_data.get("position", i),
                action_name=step_data.get("action_name", ""),
                action=step_data.get("action", step_data.get("action_name", "")),
                element=step_data.get("element"),
                description=step_data.get("description"),
                locator=step_data.get("locator"),
                test_data=step_data.get("test_data"),
                wait_time=step_data.get("wait_time"),
                test_case_id=new_id,
                raw_data=step_data
            )
            steps.append(step)
        
        # Use source test case metadata if available
        if source_test_case:
            name = ai_response.get("name", f"AI-Optimized: {source_test_case.name}")
            description = ai_response.get("description", source_test_case.description)
            priority = source_test_case.priority
            status = source_test_case.status
            tags = source_test_case.tags
            test_data_id = source_test_case.test_data_id
        else:
            name = ai_response.get("name", "AI-Optimized Test Case")
            description = ai_response.get("description", "")
            priority = None
            status = "READY"
            tags = []
            test_data_id = None
        
        # Create test case
        test_case = TestCase(
            id=new_id,
            name=name,
            description=description,
            priority=priority,
            status=status,
            duration=ai_response.get("estimated_duration_ms"),
            tags=tags,
            steps=steps,
            test_data_id=test_data_id,
            updated_date=int(datetime.now().timestamp() * 1000),
            raw_data={
                "optimizationSource": "ai_optimized",
                "sourceTestCases": [source_test_case.id] if source_test_case else [],
                "optimizationDate": int(datetime.now().timestamp() * 1000),
                "optimizationReason": ai_response.get("reasoning", "AI-optimized test case"),
                "optimizations": ai_response.get("optimizations_made", []),
                "coverageMaintained": ai_response.get("coverage_maintained", True)
            }
        )
        
        return test_case
    
    def assign_new_test_case_id(
        self,
        existing_ids: List[int],
        preferred_id: Optional[int] = None
    ) -> int:
        """
        Generate new unique test case ID.
        
        Args:
            existing_ids: List of existing IDs to avoid
            preferred_id: Optional preferred ID (will adjust if conflicts)
            
        Returns:
            New unique test case ID
        """
        existing_set = set(existing_ids)
        
        # If preferred ID provided and available, use it
        if preferred_id and preferred_id not in existing_set:
            self._used_ids.add(preferred_id)
            return preferred_id
        
        # Generate new ID
        if preferred_id:
            # Start from preferred ID and find next available
            new_id = preferred_id
            while new_id in existing_set or new_id in self._used_ids:
                new_id += 1
        else:
            # Use hash-based or sequential approach
            if existing_ids:
                max_id = max(existing_ids)
                # Use range starting from max + 1 or start_id_range, whichever is higher
                new_id = max(max_id + 1, self.start_id_range)
            else:
                new_id = self.start_id_range
            
            # Ensure it's unique
            while new_id in existing_set or new_id in self._used_ids:
                new_id += 1
        
        self._used_ids.add(new_id)
        return new_id
    
    def generate_test_case_metadata(
        self,
        test_case: TestCase,
        source_ids: List[int]
    ) -> Dict:
        """
        Generate metadata for new test case.
        
        Args:
            test_case: Test case object
            source_ids: List of source test case IDs
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            "sourceTestCases": source_ids,
            "optimizationDate": int(datetime.now().timestamp() * 1000),
            "originalMetadata": {}
        }
        
        # Preserve original metadata if available
        if test_case.raw_data:
            original_raw = test_case.raw_data
            # Preserve important fields
            for key in ["version", "workspace", "testData", "testConfiguration", "files", "suites"]:
                if key in original_raw:
                    metadata["originalMetadata"][key] = original_raw[key]
        
        # Add optimization info
        metadata["optimizationInfo"] = {
            "sourceCount": len(source_ids),
            "optimizationType": "merged" if len(source_ids) > 1 else "optimized"
        }
        
        return metadata
    
    def generate_step_file_content(
        self,
        test_case: TestCase,
        include_pageable: bool = True
    ) -> Dict:
        """
        Generate step file JSON structure.
        
        Args:
            test_case: Test case with steps
            include_pageable: Whether to include pageable metadata
            
        Returns:
            Step file JSON structure
        """
        # Generate step content
        steps_data = []
        for step in sorted(test_case.steps, key=lambda s: s.position):
            if step.raw_data:
                # Use original raw data
                step_json = step.raw_data.copy()
                # Update position and test_case_id
                step_json["position"] = step.position
                step_json["testCaseId"] = test_case.id
            else:
                # Create from TestStep object
                step_json = {
                    "id": step.id,
                    "position": step.position,
                    "action": step.action,
                    "actionName": step.action_name,
                    "element": step.element,
                    "description": step.description,
                    "testData": step.test_data,
                    "waitTime": step.wait_time,
                    "testCaseId": test_case.id,
                    "type": "ACTION_TEXT",
                    "priority": "MAJOR"
                }
            
            steps_data.append(step_json)
        
        # Create step file structure
        step_file = {
            "content": steps_data
        }
        
        # Add pageable metadata if requested
        if include_pageable:
            step_count = len(steps_data)
            step_file.update({
                "pageable": {
                    "sort": {
                        "sorted": True,
                        "unsorted": False,
                        "empty": False
                    },
                    "offset": 0,
                    "pageNumber": 0,
                    "pageSize": 2000,
                    "paged": True,
                    "unpaged": False
                },
                "totalElements": step_count,
                "totalPages": 1 if step_count > 0 else 0,
                "last": True,
                "first": True,
                "size": 2000,
                "number": 0,
                "numberOfElements": step_count,
                "empty": step_count == 0,
                "sort": {
                    "sorted": True,
                    "unsorted": False,
                    "empty": False
                }
            })
        
        return step_file
    
    def _ensure_unique_id(self, test_id: int, existing_ids: Set[int]) -> int:
        """Ensure test ID is unique, adjust if needed."""
        if test_id not in existing_ids and test_id not in self._used_ids:
            self._used_ids.add(test_id)
            return test_id
        
        # Find next available ID
        new_id = test_id
        while new_id in existing_ids or new_id in self._used_ids:
            new_id += 1
        
        self._used_ids.add(new_id)
        return new_id
    
    def _get_step_signature(self, step: TestStep) -> str:
        """Create signature for step comparison."""
        action = step.action_name or ""
        element = step.element or ""
        desc = step.description or ""
        return f"{action}|{element}|{desc}".lower()
    
    def _create_merged_description(self, source_test_cases: List[TestCase]) -> str:
        """Create description for merged test case."""
        source_names = [tc.name for tc in source_test_cases]
        source_ids = [tc.id for tc in source_test_cases]
        
        description = (
            f"Combined test case merging:\n"
            f"- {', '.join(source_names)}\n"
            f"Source IDs: {', '.join(map(str, source_ids))}\n"
            f"Preserves all unique steps from source test cases."
        )
        
        return description


