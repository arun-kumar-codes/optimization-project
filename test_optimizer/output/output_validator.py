"""
Module for validating output files.
"""

import sys
from pathlib import Path
from typing import Dict, List
sys.path.insert(0, str(Path(__file__).parent.parent))


class OutputValidator:
    """Validates generated output files."""
    
    def __init__(self, output_dir: str):
        """
        Initialize output validator.
        
        Args:
            output_dir: Output directory path
        """
        self.output_dir = Path(output_dir)
    
    def validate_all_outputs(
        self,
        expected_test_case_ids: List[int]
    ) -> Dict:
        """
        Validate all output files.
        
        Args:
            expected_test_case_ids: List of expected test case IDs
            
        Returns:
            Validation result dictionary
        """
        validation_results = {
            "test_case_files": self._validate_test_case_files(expected_test_case_ids),
            "step_files": self._validate_step_files(expected_test_case_ids),
            "summary_files": self._validate_summary_files(),
            "all_valid": True
        }
        
        # Check if all valid
        validation_results["all_valid"] = (
            validation_results["test_case_files"]["valid"] and
            validation_results["step_files"]["valid"] and
            validation_results["summary_files"]["valid"]
        )
        
        return validation_results
    
    def _validate_test_case_files(self, expected_ids: List[int]) -> Dict:
        """Validate test case JSON files."""
        test_cases_dir = self.output_dir / "test_cases"
        issues = []
        found_files = []
        
        if not test_cases_dir.exists():
            return {"valid": False, "issues": ["test_cases directory not found"]}
        
        for test_id in expected_ids:
            file_path = test_cases_dir / f"{test_id:02d}.json"
            if file_path.exists():
                found_files.append(test_id)
                # Try to parse JSON
                try:
                    import json
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    if "id" not in data:
                        issues.append(f"Test case {test_id}: Missing 'id' field")
                except Exception as e:
                    issues.append(f"Test case {test_id}: Invalid JSON - {str(e)}")
            else:
                issues.append(f"Test case {test_id}: File not found")
        
        return {
            "valid": len(issues) == 0,
            "expected": len(expected_ids),
            "found": len(found_files),
            "issues": issues
        }
    
    def _validate_step_files(self, expected_ids: List[int]) -> Dict:
        """Validate step JSON files."""
        steps_dir = self.output_dir / "steps_in_test_cases"
        issues = []
        found_files = []
        
        if not steps_dir.exists():
            return {"valid": False, "issues": ["steps_in_test_cases directory not found"]}
        
        for test_id in expected_ids:
            file_path = steps_dir / f"{test_id:02d}.json"
            if file_path.exists():
                found_files.append(test_id)
                # Try to parse JSON
                try:
                    import json
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    if "content" not in data:
                        issues.append(f"Steps {test_id}: Missing 'content' field")
                except Exception as e:
                    issues.append(f"Steps {test_id}: Invalid JSON - {str(e)}")
            else:
                issues.append(f"Steps {test_id}: File not found")
        
        return {
            "valid": len(issues) == 0,
            "expected": len(expected_ids),
            "found": len(found_files),
            "issues": issues
        }
    
    def _validate_summary_files(self) -> Dict:
        """Validate summary JSON files."""
        required_files = [
            "admin_optimized_tests.json",
            "user_optimized_tests.json",
            "execution_order.json"
        ]
        
        issues = []
        found_files = []
        
        for filename in required_files:
            file_path = self.output_dir / filename
            if file_path.exists():
                found_files.append(filename)
                try:
                    import json
                    with open(file_path, 'r') as f:
                        json.load(f)
                except Exception as e:
                    issues.append(f"{filename}: Invalid JSON - {str(e)}")
            else:
                issues.append(f"{filename}: File not found")
        
        return {
            "valid": len(issues) == 0,
            "expected": len(required_files),
            "found": len(found_files),
            "issues": issues
        }


