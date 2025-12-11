"""
Module for generating all output files in the same format as input.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from flows.flow_analyzer import FlowAnalyzer


class OutputGenerator:
    """Generates all output files for optimized test suite."""
    
    def __init__(self, output_dir: str, original_data_dir: Optional[str] = None):
        """
        Initialize output generator.
        
        Args:
            output_dir: Directory to write output files
            original_data_dir: Optional directory with original data files (for metadata preservation)
        """
        self.output_dir = Path(output_dir)
        self.test_cases_dir = self.output_dir / "test_cases"
        self.steps_dir = self.output_dir / "steps_in_test_cases"
        self.flow_analyzer = FlowAnalyzer()
        
        # Original data directories for metadata preservation
        if original_data_dir:
            self.original_data_dir = Path(original_data_dir)
            self.original_test_cases_dir = self.original_data_dir / "test_cases"
            self.original_steps_dir = self.original_data_dir / "steps_in_test_cases"
        else:
            self.original_data_dir = None
            self.original_test_cases_dir = None
            self.original_steps_dir = None
        
        # Create directories
        self.test_cases_dir.mkdir(parents=True, exist_ok=True)
        self.steps_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_optimized_test_case_files(
        self,
        optimized_test_cases: Dict[int, TestCase],
        original_test_cases: Dict[int, TestCase]
    ):
        """
        Generate optimized test case JSON files in same format as input.
        Preserves all metadata from original files.
        
        Args:
            optimized_test_cases: Optimized test cases to output
            original_test_cases: Original test cases (for raw_data reference)
        """
        print(f"  [OUTPUT GENERATOR] Generating {len(optimized_test_cases)} optimized test case files...")
        
        for idx, (test_id, test_case) in enumerate(optimized_test_cases.items(), 1):
            print(f"    [{idx}/{len(optimized_test_cases)}] Generating TC{test_id:02d}.json...", end=" ")
            test_case_json = None
            
            # Check if this is a merged test case (not in original)
            is_merged = test_id not in original_test_cases
            
            if test_id in original_test_cases:
                original_raw = original_test_cases[test_id].raw_data
                if original_raw:
                    
                    test_case_json = original_raw.copy()
                    test_case_json["id"] = test_case.id
                    test_case_json["name"] = test_case.name
                    if test_case.description:
                        test_case_json["description"] = test_case.description
            
            if not test_case_json and self.original_test_cases_dir:
                original_file = self.original_test_cases_dir / f"{test_id:02d}.json"
                if original_file.exists():
                    try:
                        with open(original_file, 'r', encoding='utf-8') as f:
                            test_case_json = json.load(f)
                            # Update with optimized values
                            test_case_json["id"] = test_case.id
                            test_case_json["name"] = test_case.name
                            if test_case.description:
                                test_case_json["description"] = test_case.description
                    except Exception as e:
                        print(f"Warning: Could not load original file {original_file}: {e}")
            
            # CRITICAL FIX: For merged test cases, use structure from first source test case
            if not test_case_json and is_merged:
                # Get source test case IDs from description
                import re
                source_ids = re.findall(r'\(ID:\s*(\d+)\)', test_case.description or "")
                if source_ids:
                    # Try to get structure from first source test case
                    first_source_id = int(source_ids[0])
                    if first_source_id in original_test_cases:
                        source_tc = original_test_cases[first_source_id]
                        if source_tc.raw_data:
                            test_case_json = source_tc.raw_data.copy()
                            # Update with merged test case values
                            test_case_json["id"] = test_case.id
                            test_case_json["name"] = test_case.name
                            if test_case.description:
                                test_case_json["description"] = test_case.description
                            if test_case.priority is not None:
                                test_case_json["priority"] = test_case.priority
                            if test_case.status:
                                test_case_json["status"] = test_case.status
                    else:
                        # Try loading from file
                        source_file = self.original_test_cases_dir / f"{first_source_id:02d}.json"
                        if not source_file.exists():
                            source_file = self.original_test_cases_dir / f"{first_source_id}.json"
                        if source_file.exists():
                            try:
                                with open(source_file, 'r', encoding='utf-8') as f:
                                    test_case_json = json.load(f)
                                    # Update with merged test case values
                                    test_case_json["id"] = test_case.id
                                    test_case_json["name"] = test_case.name
                                    if test_case.description:
                                        test_case_json["description"] = test_case.description
                                    if test_case.priority is not None:
                                        test_case_json["priority"] = test_case.priority
                                    if test_case.status:
                                        test_case_json["status"] = test_case.status
                            except Exception as e:
                                print(f"Warning: Could not load source file {source_file}: {e}")
            
            if not test_case_json:
                test_case_json = self._test_case_to_json(test_case, preserve_structure=True)
            
            # For merged test cases, remove merge-specific metadata to match standalone structure
            if is_merged and test_case_json:
                # Remove merge-specific fields that shouldn't be in final output
                merge_fields_to_remove = [
                    "source_test_cases",
                    "merged_from",
                    "merged_metadata",
                    "combined_flows",
                    "merge_strategy",
                    "prefix_length",
                    "suffix_length",
                    "total_unique_steps",
                    "original_total_steps"
                ]
                for field in merge_fields_to_remove:
                    test_case_json.pop(field, None)
            
            # Write the file
            file_path = self.test_cases_dir / f"{test_id:02d}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(test_case_json, f, indent=2, ensure_ascii=False)
            print(f"✓ Written ({len(test_case.steps)} steps)")
    
    def generate_optimized_step_files(
        self,
        optimized_test_cases: Dict[int, TestCase],
        original_test_cases: Dict[int, TestCase]
    ):
        """
        Generate optimized step JSON files in same format as input.
        Preserves all metadata including pageable.
        
        Args:
            optimized_test_cases: Optimized test cases
            original_test_cases: Original test cases (for raw_data reference)
        """
        print(f"  [OUTPUT GENERATOR] Generating {len(optimized_test_cases)} optimized step files...")
        
        for idx, (test_id, test_case) in enumerate(optimized_test_cases.items(), 1):
            print(f"    [{idx}/{len(optimized_test_cases)}] Generating steps for TC{test_id:02d}.json...", end=" ")
            # Get steps data
            steps_data = []
            for step in sorted(test_case.steps, key=lambda s: s.position):
                if step.raw_data:
                    
                    step_json = step.raw_data.copy()
                    step_json["position"] = step.position
                    step_json["testCaseId"] = test_id
                    steps_data.append(step_json)
                else:
                    
                    steps_data.append(self._test_step_to_json(step, test_id))
            
            original_metadata = None
            if self.original_steps_dir:
                original_file = self.original_steps_dir / f"{test_id:02d}.json"
                if original_file.exists():
                    try:
                        with open(original_file, 'r', encoding='utf-8') as f:
                            original_data = json.load(f)
                            original_metadata = original_data
                    except Exception as e:
                        print(f"Warning: Could not load original steps file {original_file}: {e}")
            
            # Also try from original test cases
            if not original_metadata and test_id in original_test_cases:
                
                if original_test_cases[test_id].steps:
                    first_step = original_test_cases[test_id].steps[0]
                    if first_step.raw_data and isinstance(first_step.raw_data, dict):
                       
                        pass
            
            # Create step file with all metadata
            step_count = len(steps_data)
            steps_json = {
                "content": steps_data
            }
           
            if original_metadata:
                steps_json["pageable"] = original_metadata.get("pageable", self._create_default_pageable())
                steps_json["sort"] = original_metadata.get("sort", self._create_default_sort())
            else:
                # Create default metadata structure
                steps_json["pageable"] = self._create_default_pageable()
                steps_json["sort"] = self._create_default_sort()
            
            steps_json["totalElements"] = step_count
            steps_json["totalPages"] = 1 if step_count > 0 else 0
            steps_json["last"] = True
            steps_json["first"] = True
            steps_json["size"] = 2000
            steps_json["number"] = 0
            steps_json["numberOfElements"] = step_count
            steps_json["empty"] = step_count == 0
            
            # Write the file
            file_path = self.steps_dir / f"{test_id:02d}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(steps_json, f, indent=2, ensure_ascii=False)
            print(f"✓ Written ({step_count} steps)")
    
    def generate_admin_user_separated_files(
        self,
        optimized_test_cases: Dict[int, TestCase],
        optimization_result: Dict
    ):
        """
        Generate separate files for admin and user test cases.
        
        Args:
            optimized_test_cases: Optimized test cases
            optimization_result: Optimization result
        """
        admin_test_cases = []
        user_test_cases = []
        
        for test_id in optimization_result["test_cases_kept"]:
            if test_id in optimized_test_cases:
                test_case = optimized_test_cases[test_id]
                flows = self.flow_analyzer.identify_flow_type(test_case)
                
                # Check if it's an admin test case
                is_admin = self._is_admin_test_case(test_case, flows)
                
                if is_admin:
                    admin_test_cases.append(test_id)
                else:
                    user_test_cases.append(test_id)
        
        # Generate admin file
        admin_file = self.output_dir / "admin_optimized_tests.json"
        with open(admin_file, 'w', encoding='utf-8') as f:
            json.dump({
                "admin_test_case_ids": sorted(admin_test_cases),
                "count": len(admin_test_cases),
                "description": "Optimized admin test cases"
            }, f, indent=2)
        
        # Generate user file
        user_file = self.output_dir / "user_optimized_tests.json"
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump({
                "user_test_case_ids": sorted(user_test_cases),
                "count": len(user_test_cases),
                "description": "Optimized user/employee test cases"
            }, f, indent=2)
        
        print(f"  Admin test cases: {len(admin_test_cases)}")
        print(f"  User test cases: {len(user_test_cases)}")
    
    def _is_admin_test_case(self, test_case: TestCase, flows: List[str]) -> bool:
        """Check if test case is an admin test case."""
        text = f"{test_case.name} {test_case.description or ''}".lower()
        admin_keywords = ["admin", "user management", "system user", "delete user", "create user"]
        
        if any(keyword in text for keyword in admin_keywords):
            return True
        
        # Check steps for admin actions
        for step in test_case.steps[:5]:  # Check first 5 steps
            step_text = f"{step.action} {step.description or ''}".lower()
            if any(keyword in step_text for keyword in ["admin", "user management", "system user"]):
                return True
        
        return False
    
    def generate_optimization_summary(
        self,
        optimization_result: Dict,
        optimization_report: Dict
    ):
        """Generate optimization_summary.json."""
        summary_file = self.output_dir / "optimization_summary.json"
        
        summary = {
            "optimization_date": optimization_report.get("summary", {}).get("optimization_successful", True),
            "original_test_cases": optimization_result["original_test_cases"],
            "optimized_test_cases": optimization_result["optimized_test_cases"],
            "reduction": optimization_result["reduction"],
            "reduction_percentage": optimization_result["reduction_percentage"],
            "coverage": {
                "before": optimization_result["coverage"]["before"],
                "after": optimization_result["coverage"]["after"]
            },
            "time_savings": optimization_result["time_savings"],
            "breakdown": {
                "admin_test_cases": "See admin_optimized_tests.json",
                "user_test_cases": "See user_optimized_tests.json"
            }
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
    
    def generate_duplicate_analysis(
        self,
        duplicate_groups: Dict
    ):
        """Generate duplicate_analysis.json."""
        dup_file = self.output_dir / "duplicate_analysis.json"
        
        with open(dup_file, 'w', encoding='utf-8') as f:
            json.dump(duplicate_groups, f, indent=2, default=str)
    
    def generate_execution_order(
        self,
        execution_plan: Dict
    ):
        """Generate execution_order.json."""
        exec_file = self.output_dir / "execution_order.json"
        
        with open(exec_file, 'w', encoding='utf-8') as f:
            json.dump(execution_plan, f, indent=2, default=str)
    
    def generate_user_flows(
        self,
        flow_coverage: Dict,
        flow_classifications: Dict
    ):
        """Generate user_flows.json."""
        flows_file = self.output_dir / "user_flows.json"
        
        flows_data = {
            "flow_coverage": flow_coverage,
            "flow_classifications": flow_classifications,
            "summary": {
                "total_flows": flow_coverage.get("total_unique_flows", 0),
                "covered_flows": flow_coverage.get("covered_flows", 0),
                "coverage_percentage": flow_coverage.get("coverage_percentage", 0)
            }
        }
        
        with open(flows_file, 'w', encoding='utf-8') as f:
            json.dump(flows_data, f, indent=2, default=str)
    
    def generate_recommendations(
        self,
        optimization_report: Dict,
        ai_recommendations: Dict = None
    ):
        """Generate recommendations.json."""
        rec_file = self.output_dir / "recommendations.json"
        
        recommendations = {
            "removed_test_cases": optimization_report.get("test_cases_removed", []),
            "kept_test_cases": optimization_report.get("test_cases_kept", []),
            "ai_recommendations": ai_recommendations or {},
            "summary": optimization_report.get("summary", {})
        }
        
        with open(rec_file, 'w', encoding='utf-8') as f:
            json.dump(recommendations, f, indent=2, default=str)
    
    def _test_case_to_json(self, test_case: TestCase, preserve_structure: bool = False) -> Dict:
        """
        Convert TestCase to JSON format.
        
        Args:
            test_case: TestCase object
            preserve_structure: If True, preserve all fields from raw_data
        """
        if preserve_structure and test_case.raw_data:
            json_data = test_case.raw_data.copy()
            # Remove merge-specific metadata fields to match standalone structure
            merge_fields_to_remove = [
                "source_test_cases",
                "merged_from",
                "merged_metadata",
                "combined_flows",
                "merge_strategy",
                "prefix_length",
                "suffix_length",
                "total_unique_steps",
                "original_total_steps"
            ]
            for field in merge_fields_to_remove:
                json_data.pop(field, None)
            
            json_data["id"] = test_case.id
            json_data["name"] = test_case.name
            if test_case.description:
                json_data["description"] = test_case.description
            if test_case.priority is not None:
                json_data["priority"] = test_case.priority
            if test_case.status:
                json_data["status"] = test_case.status
            if test_case.tags:
                json_data["tags"] = test_case.tags
            return json_data
        
        # Basic structure - match input format with all required fields
        import time
        current_time = int(time.time() * 1000)
        json_data = {
            "id": test_case.id,
            "name": test_case.name,
            "description": test_case.description or "",
            "priority": test_case.priority if test_case.priority is not None else None,
            "status": test_case.status or "READY",
            "tags": test_case.tags or [],
            "preRequisiteCase": test_case.prerequisite_case,
            "testDataId": test_case.test_data_id,
            "createdDate": test_case.created_date or current_time,
            "updatedDate": test_case.updated_date or current_time,
            "startTime": None,
            "endTime": None,
            "deleted": False,
            "isDataDriven": False,
            "isStepGroup": False,
            "draftAt": None,
            "obsoleteAt": None,
            "readyAt": None,
            "type": 1,
            "workspaceVersionId": 1,
            "preRequisite": None,
            "copiedFrom": None,
            "testDataStartIndex": 0,
            "testDataEndIndex": None,
            "results": None,
            "priorityName": None,
            "typeName": None,
            "testDataName": None,
            "preRequisiteName": None,
            "order": None,
            "files": [],
            "testType": "BROWSER",
            "jiraTicketsId": None,
            "isExtensionUsed": False,
            "testConfiguration": {
                "viewport": {
                    "width": 1280,
                    "height": 720
                }
            },
            "testDataFunctionArgs": None,
            "disableAutoWaitSteps": False,
            "testcaseTimeout": 20,
            "session": None,
            "lastRun": None,
            "lastRunResult": None,
            "updateMetadata": True,
            "missingData": None,
            "createdBy": None,
            "knowledgeId": None,
            "platform": None,
            "suites": None,
            "version": {
                "id": 1,
                "workspaceId": 1,
                "versionName": "Version1.0",
                "description": None,
                "workspace": {
                    "id": 1,
                    "name": "Web workspace (Live)",
                    "description": "Add, Delete or Update multiple workspace versions using Live.",
                    "workspaceType": "WebApplication",
                    "createdDate": 1655628237000,
                    "updatedDate": 1655628237000,
                    "userIds": [],
                    "createdBy": None,
                    "versions": None,
                    "is_demo": True
                },
                "createdDate": 1550559354000,
                "updatedDate": 1655628237000
            },
            "from": None,
            "to": None,
            "url": None,
            "testData": None,
            "draftAt": None,
            "obsoleteAt": None,
            "readyAt": None,
            "type": 3,
            "testType": "BROWSER",
            "files": [],
            "results": None,
            "priorityName": None,
            "typeName": None,
            "testDataName": None,
            "preRequisiteName": None,
            "order": None,
            "startTime": None,
            "endTime": None,
            "lastRun": None,
            "jiraTicketsId": None,
            "isExtensionUsed": False,
            "testConfiguration": {
                "viewport": {
                    "width": 1280,
                    "height": 720
                }
            },
            "testDataFunctionArgs": None,
            "disableAutoWaitSteps": False,
            "testcaseTimeout": None,
            "session": None,
            "lastRunResult": test_case.last_run_result,
            "updateMetadata": False,
            "missingData": None,
            "createdBy": None,
            "knowledgeId": None,
            "platform": None,
            "suites": None
        }
        
        # Preserve version/workspace if in raw_data
        if test_case.raw_data:
            for key in ["version", "workspaceVersionId", "testData"]:
                if key in test_case.raw_data:
                    json_data[key] = test_case.raw_data[key]
        
        return json_data
    
    def _test_step_to_json(self, step, test_case_id: Optional[int] = None) -> Dict:
        """
        Convert TestStep to JSON format with full structure.
        
        Args:
            step: TestStep object
            test_case_id: Test case ID to use
        """
        tc_id = test_case_id or step.test_case_id
        
        return {
            "id": step.id,
            "priority": "MAJOR",
            "position": step.position,
            "preRequisiteStepId": None,
            "action": step.action,
            "actionName": step.action_name,
            "testCaseId": tc_id,
            "stepGroupId": None,
            "testData": step.test_data,
            "testDataType": None,
            "attribute": None,
            "element": step.element,
            "elementId": None,
            "fromElement": None,
            "toElement": None,
            "forLoopStartIndex": None,
            "forLoopEndIndex": None,
            "forLoopTestDataId": None,
            "visualEnabled": False,
            "testDataFunctionId": None,
            "testDataProfileName": None,
            "processedAsSubStep": False,
            "addonTDF": None,
            "testDataFunctionArgs": None,
            "exceptedResult": None,
            "naturalTextActionId": None,
            "type": "ACTION_TEXT",
            "waitTime": step.wait_time or 30,
            "conditionType": None,
            "parentId": None,
            "restStep": None,
            "phoneNumberId": None,
            "addonActionId": None,
            "addonNaturalTextActionData": None,
            "addonTestData": None,
            "addonElements": None,
            "disabled": False,
            "ignoreStepResult": False,
            "testDataProfileStepId": None,
            "testStepDTOS": [],
            "index": None,
            "testDataId": None,
            "testDataIndex": None,
            "setName": None,
            "description": step.description,
            "specs": None,
            "metadata": None,
            "event": step.locator or {},
            "goldenScreenshot": None,
            "goldenHtmlCode": None,
            "environmentId": None,
            "screenshotUrl": None,
            "domElementImageUrl": None,
            "requestList": None,
            "testDataList": None,
            "manualExecution": False,
            "dataMapBean": {
                "condition_if": [],
                "for_loop": {
                    "startIndex": None,
                    "endIndex": None,
                    "testDataId": None
                }
            },
            "dataMapJson": {
                "conditionIf": []
            },
            "conditionIf": []
        }
    
    def _create_default_pageable(self) -> Dict:
        """Create default pageable metadata structure."""
        return {
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
        }
    
    def _create_default_sort(self) -> Dict:
        """Create default sort metadata structure."""
        return {
            "sorted": True,
            "unsorted": False,
            "empty": False
        }

