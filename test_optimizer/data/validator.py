"""
Module for validating test case data structure and completeness.
"""

from typing import List, Dict, Optional
from .models import TestCase, TestStep


class DataValidator:
    """Validates test case data structure and completeness."""
    
    def __init__(self):
        self.validation_errors: List[Dict] = []
        self.validation_warnings: List[Dict] = []
    
    def validate_test_case(self, test_case: TestCase) -> bool:
        """
        Validate a single test case.
        
        Args:
            test_case: The TestCase object to validate
            
        Returns:
            True if valid, False otherwise
        """
        is_valid = True
        
        # Check required fields
        if not test_case.id:
            self._add_error(test_case.id, "Missing test case ID")
            is_valid = False
        
        if not test_case.name or not test_case.name.strip():
            self._add_warning(test_case.id, "Test case name is empty or missing")
        
        # Check steps
        if not test_case.steps:
            self._add_warning(test_case.id, "Test case has no steps")
        else:
            # Validate each step
            for step in test_case.steps:
                if not self._validate_step(step, test_case.id):
                    is_valid = False
        
        # Check for duplicate step positions
        positions = [step.position for step in test_case.steps]
        if len(positions) != len(set(positions)):
            self._add_warning(
                test_case.id,
                f"Duplicate step positions found: {positions}"
            )
        
        return is_valid
    
    def _validate_step(self, step: TestStep, test_case_id: int) -> bool:
        """
        Validate a single test step.
        
        Args:
            step: The TestStep object to validate
            test_case_id: The test case ID this step belongs to
            
        Returns:
            True if valid, False otherwise
        """
        is_valid = True
        
        # Check required fields
        if step.id is None:
            self._add_error(test_case_id, f"Step at position {step.position} has no ID")
            is_valid = False
        
        if step.position is None:
            self._add_error(test_case_id, f"Step {step.id} has no position")
            is_valid = False
        
        if not step.action_name:
            self._add_warning(
                test_case_id,
                f"Step {step.id} at position {step.position} has no action name"
            )
        
        # Check for common issues
        if step.action_name == "navigateTo" and not step.test_data:
            # Try to extract URL from action or description
            has_url = False
            if step.action and ("http://" in step.action or "https://" in step.action):
                has_url = True
            if step.description and ("http://" in step.description or "https://" in step.description):
                has_url = True
            if not has_url:
                self._add_warning(
                    test_case_id,
                    f"Step {step.id} (navigateTo) has no URL in test_data, action, or description"
                )
        
        return is_valid
    
    def validate_all(self, test_cases: Dict[int, TestCase]) -> Dict:
        """
        Validate all test cases.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Validation report dictionary
        """
        self.validation_errors = []
        self.validation_warnings = []
        
        valid_count = 0
        invalid_count = 0
        
        for test_case_id, test_case in test_cases.items():
            if self.validate_test_case(test_case):
                valid_count += 1
            else:
                invalid_count += 1
        
        return {
            "total_test_cases": len(test_cases),
            "valid_test_cases": valid_count,
            "invalid_test_cases": invalid_count,
            "total_errors": len(self.validation_errors),
            "total_warnings": len(self.validation_warnings),
            "errors": self.validation_errors,
            "warnings": self.validation_warnings
        }
    
    def _add_error(self, test_case_id: int, message: str):
        """Add a validation error."""
        self.validation_errors.append({
            "test_case_id": test_case_id,
            "message": message,
            "type": "error"
        })
    
    def _add_warning(self, test_case_id: int, message: str):
        """Add a validation warning."""
        self.validation_warnings.append({
            "test_case_id": test_case_id,
            "message": message,
            "type": "warning"
        })
    
    def generate_validation_report(self, validation_result: Dict) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            validation_result: The result dictionary from validate_all()
            
        Returns:
            Formatted report string
        """
        report_lines = [
            "=" * 80,
            "TEST CASE DATA VALIDATION REPORT",
            "=" * 80,
            "",
            f"Total Test Cases: {validation_result['total_test_cases']}",
            f"Valid Test Cases: {validation_result['valid_test_cases']}",
            f"Invalid Test Cases: {validation_result['invalid_test_cases']}",
            f"Total Errors: {validation_result['total_errors']}",
            f"Total Warnings: {validation_result['total_warnings']}",
            "",
        ]
        
        if validation_result['errors']:
            report_lines.extend([
                "ERRORS:",
                "-" * 80
            ])
            for error in validation_result['errors']:
                report_lines.append(
                    f"  Test Case {error['test_case_id']}: {error['message']}"
                )
            report_lines.append("")
        
        if validation_result['warnings']:
            report_lines.extend([
                "WARNINGS:",
                "-" * 80
            ])
            for warning in validation_result['warnings']:
                report_lines.append(
                    f"  Test Case {warning['test_case_id']}: {warning['message']}"
                )
            report_lines.append("")
        
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)

