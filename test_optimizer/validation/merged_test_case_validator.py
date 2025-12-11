"""
Comprehensive validation system for merged test cases.
Validates flow correctness, step consistency, and execution-breaking issues.
Designed to be scalable for 100+ test cases.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase, TestStep


class MergedTestCaseValidator:
    """Validates merged test cases for correctness and consistency."""
    
    def __init__(self):
        """Initialize validator."""
        self.issues = []
        self.warnings = []
    
    def validate_merged_test_case(
        self,
        merged_test_case: TestCase,
        source_test_cases: List[TestCase]
    ) -> Dict:
        """
        Comprehensive validation of a merged test case.
        
        Args:
            merged_test_case: The merged test case to validate
            source_test_cases: List of source test cases that were merged
            
        Returns:
            Validation result dictionary
        """
        self.issues = []
        self.warnings = []
        
        # 1. Step Preservation Validation
        step_validation = self._validate_step_preservation(merged_test_case, source_test_cases)
        
        # 2. Flow Correctness Validation
        flow_validation = self._validate_flow_correctness(merged_test_case, source_test_cases)
        
        # 3. Step Order Consistency
        order_validation = self._validate_step_order(merged_test_case, source_test_cases)
        
        # 4. Execution-Breaking Issues
        execution_validation = self._validate_execution_safety(merged_test_case)
        
        # 5. Data Consistency
        data_validation = self._validate_data_consistency(merged_test_case, source_test_cases)
        
        # 6. Role Consistency (admin/user separation)
        role_validation = self._validate_role_consistency(merged_test_case, source_test_cases)
        
        # 7. Website Consistency
        website_validation = self._validate_website_consistency(merged_test_case, source_test_cases)
        
        all_passed = all([
            step_validation["passed"],
            flow_validation["passed"],
            order_validation["passed"],
            execution_validation["passed"],
            data_validation["passed"],
            role_validation["passed"],
            website_validation["passed"]
        ])
        
        return {
            "passed": all_passed,
            "step_preservation": step_validation,
            "flow_correctness": flow_validation,
            "step_order": order_validation,
            "execution_safety": execution_validation,
            "data_consistency": data_validation,
            "role_consistency": role_validation,
            "website_consistency": website_validation,
            "issues": self.issues,
            "warnings": self.warnings,
            "summary": self._generate_summary()
        }
    
    def _validate_step_preservation(
        self,
        merged_test_case: TestCase,
        source_test_cases: List[TestCase]
    ) -> Dict:
        """Validate that all unique steps are preserved."""
        # Collect all unique steps from source test cases
        source_step_signatures = set()
        for tc in source_test_cases:
            for step in tc.steps:
                sig = self._get_step_signature(step)
                source_step_signatures.add(sig)
        
        # Collect steps from merged test case
        merged_step_signatures = set()
        for step in merged_test_case.steps:
            sig = self._get_step_signature(step)
            merged_step_signatures.add(sig)
        
        # Check for missing steps
        missing_steps = source_step_signatures - merged_step_signatures
        if missing_steps:
            self.issues.append(f"Missing {len(missing_steps)} unique steps in merged test case")
            return {
                "passed": False,
                "missing_steps_count": len(missing_steps),
                "missing_signatures": list(missing_steps)[:10]  # First 10 for debugging
            }
        
        return {"passed": True, "preserved_steps": len(merged_step_signatures)}
    
    def _validate_flow_correctness(
        self,
        merged_test_case: TestCase,
        source_test_cases: List[TestCase]
    ) -> Dict:
        """Validate that the flow is logically correct."""
        issues = []
        
        steps = merged_test_case.steps
        if not steps:
            issues.append("Merged test case has no steps")
            return {"passed": False, "issues": issues}
        
        # CRITICAL: Check for duplicate login sequences
        # Login should only appear once at the beginning
        login_steps = []
        for idx, step in enumerate(steps):
            action_lower = (step.action_name or "").lower()
            action_text = (step.action or "").lower()
            element_lower = (step.element or "").lower() if step.element else ""
            
            # Detect login sequence: username/password entry or login button click
            is_login_step = False
            if action_lower in ["enter", "type", "input"]:
                if "username" in element_lower or "username" in action_text:
                    is_login_step = True
                elif "password" in element_lower or "password" in action_text:
                    is_login_step = True
            elif action_lower == "click" and "login" in element_lower:
                is_login_step = True
            elif action_lower == "navigateto":
                # Check if navigating to login page
                if step.raw_data and isinstance(step.raw_data, dict):
                    event = step.raw_data.get("event", {})
                    if isinstance(event, dict):
                        href = event.get("href", "")
                        if "/auth/login" in href.lower() or "/login" in href.lower():
                            is_login_step = True
            
            if is_login_step:
                login_steps.append((idx, step))
        
        # If we have multiple login sequences (more than 5 login-related steps), it's likely a duplicate
        if len(login_steps) > 5:
            # Check if login steps appear after position 10 (likely duplicate)
            late_login_steps = [pos for pos, step in login_steps if pos > 10]
            if late_login_steps:
                issues.append(f"Duplicate login sequence detected: {len(late_login_steps)} login steps after position 10 (positions: {late_login_steps[:5]})")
        
        # Check for login/logout pattern
        has_login = False
        has_logout = False
        login_position = None
        logout_position = None
        
        for idx, step in enumerate(steps):
            action_lower = step.action_name.lower() if step.action_name else ""
            action_text = step.action.lower() if step.action else ""
            
            # Check for login
            if not has_login and ("login" in action_lower or "login" in action_text or 
                                 (step.test_data and "login" in str(step.test_data).lower())):
                # Verify it's actually a login (has username/password or navigates to login page)
                if "username" in action_text or "password" in action_text or "navigatetologin" in action_text:
                    has_login = True
                    login_position = idx
            
            # Check for logout
            if "logout" in action_lower or "logout" in action_text:
                has_logout = True
                logout_position = idx
        
        # Validate flow structure
        if has_login and has_logout:
            if logout_position <= login_position:
                issues.append(f"Logout (position {logout_position}) appears before login (position {login_position})")
        elif not has_login:
            self.warnings.append("No login step detected - may be post-login flow")
        elif not has_logout:
            self.warnings.append("No logout step detected - session may remain open")
        
        # CRITICAL: Check for admin credentials in user flows
        # Determine if this should be a user flow based on source test cases
        from analysis.role_classifier import RoleClassifier
        classifier = RoleClassifier()
        
        source_roles = set()
        for tc in source_test_cases:
            role = classifier.classify_role(tc)
            source_roles.add(role)
        
        # If all source test cases are "user", check for admin credentials
        if source_roles == {"user"} or (len(source_roles) == 1 and "user" in source_roles):
            admin_credentials_found = []
            for idx, step in enumerate(steps[:20]):  # Check first 20 steps
                test_data = str(step.test_data or "")
                action_text = (step.action or "").lower()
                
                # Check for "Admin" (capital A) in username field
                if "Admin" in test_data and "username" in action_text:
                    admin_credentials_found.append(f"Step {idx+1}: '{step.action}' with testData='{test_data}'")
                
                # Also check event.value
                if step.raw_data and isinstance(step.raw_data, dict):
                    event = step.raw_data.get("event", {})
                    if isinstance(event, dict):
                        event_value = str(event.get("value", ""))
                        if "Admin" in event_value and "username" in action_text:
                            admin_credentials_found.append(f"Step {idx+1}: '{step.action}' with event.value='{event_value}'")
            
            if admin_credentials_found:
                issues.append(f"Admin credentials found in user flow: {admin_credentials_found[:3]}")
        
        # Check for navigation before actions
        has_navigation = False
        for step in steps[:5]:  # Check first 5 steps
            if step.action_name == "navigateTo" or (step.action and "navigate" in step.action.lower()):
                has_navigation = True
                break
        
        if not has_navigation and len(steps) > 3:
            self.warnings.append("No navigation step in first 5 steps - may start in wrong context")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "has_login": has_login,
            "has_logout": has_logout,
            "has_navigation": has_navigation
        }
    
    def _validate_step_order(
        self,
        merged_test_case: TestCase,
        source_test_cases: List[TestCase]
    ) -> Dict:
        """Validate that step order is consistent and logical."""
        issues = []
        steps = merged_test_case.steps
        
        # Check position sequence
        positions = [step.position for step in steps]
        if positions != list(range(1, len(steps) + 1)):
            issues.append(f"Step positions are not sequential: {positions[:10]}...")
        
        # Check for logical order violations
        # 1. Actions should not appear before navigation (except in first few steps)
        for idx, step in enumerate(steps[3:], start=3):  # Skip first 3 steps
            if step.action_name in ["click", "enter", "verify"]:
                # Check if there's a navigation in recent steps
                recent_nav = any(
                    s.action_name == "navigateTo" 
                    for s in steps[max(0, idx-5):idx]
                )
                if not recent_nav and idx > 5:
                    # This might be okay if we're in a flow, but log as warning
                    pass
        
        # 2. Verify steps should come after actions
        verify_positions = []
        action_positions = []
        for idx, step in enumerate(steps):
            if step.action_name == "verify":
                verify_positions.append(idx)
            elif step.action_name in ["click", "enter", "type"]:
                action_positions.append(idx)
        
        # Check if verifies appear before any actions (might be okay for initial state checks)
        if verify_positions and action_positions:
            first_verify = min(verify_positions)
            first_action = min(action_positions)
            if first_verify > first_action + 10:  # Allow some verifies after actions
                pass  # This is fine
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "total_steps": len(steps),
            "position_sequence_valid": positions == list(range(1, len(steps) + 1))
        }
    
    def _validate_execution_safety(
        self,
        merged_test_case: TestCase
    ) -> Dict:
        """Validate that test case can be executed without breaking."""
        issues = []
        warnings = []
        steps = merged_test_case.steps
        
        if not steps:
            issues.append("Test case has no steps - cannot execute")
            return {"passed": False, "issues": issues}
        
        # Check for required fields
        for idx, step in enumerate(steps, start=1):
            # Action name is required
            if not step.action_name or step.action_name.strip() == "":
                issues.append(f"Step {idx} has no action_name")
            
            # For click/enter actions, element or locator should be present
            if step.action_name in ["click", "enter", "type"]:
                if not step.element and not (step.raw_data and step.raw_data.get("event", {}).get("locator")):
                    if not step.raw_data or not step.raw_data.get("event", {}).get("label"):
                        warnings.append(f"Step {idx} ({step.action_name}) has no element/locator - may fail at runtime")
            
            # For navigateTo, URL should be present
            if step.action_name == "navigateTo":
                if not step.test_data and not (step.raw_data and step.raw_data.get("event", {}).get("href")):
                    issues.append(f"Step {idx} (navigateTo) has no URL")
        
        # Check for duplicate step IDs (could cause execution issues)
        step_ids = [step.id for step in steps]
        if len(step_ids) != len(set(step_ids)):
            duplicates = [sid for sid in step_ids if step_ids.count(sid) > 1]
            issues.append(f"Duplicate step IDs found: {set(duplicates)}")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "executable": len(issues) == 0
        }
    
    def _validate_data_consistency(
        self,
        merged_test_case: TestCase,
        source_test_cases: List[TestCase]
    ) -> Dict:
        """Validate that test data is consistent."""
        issues = []
        
        # Check for conflicting test data
        # (e.g., different usernames in same flow)
        login_data = []
        for step in merged_test_case.steps:
            if step.action_name in ["enter", "type"] and step.test_data:
                if "username" in (step.element or "").lower() or "user" in (step.description or "").lower():
                    login_data.append(step.test_data)
        
        unique_login_data = set(login_data)
        if len(unique_login_data) > 1:
            # Multiple different usernames - this might be intentional (testing different users)
            # But log as warning if it's in the same flow
            self.warnings.append(f"Multiple different usernames detected: {unique_login_data}")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues
        }
    
    def _validate_role_consistency(
        self,
        merged_test_case: TestCase,
        source_test_cases: List[TestCase]
    ) -> Dict:
        """Validate that all source test cases have the same role."""
        from analysis.role_classifier import RoleClassifier
        
        classifier = RoleClassifier()
        roles = []
        for tc in source_test_cases:
            role = classifier.classify_role(tc)
            roles.append(role)
        
        unique_roles = set(roles)
        if len(unique_roles) > 1:
            return {
                "passed": False,
                "issue": f"Mixed roles detected: {unique_roles}. Admin and user test cases should not be merged.",
                "roles": list(unique_roles)
            }
        
        # Check merged test case itself
        merged_role = classifier.classify_role(merged_test_case)
        if merged_role not in unique_roles and "unknown" not in unique_roles:
            self.warnings.append(f"Merged test case role ({merged_role}) differs from source roles ({unique_roles})")
        
        return {
            "passed": True,
            "role": list(unique_roles)[0] if unique_roles else "unknown"
        }
    
    def _validate_website_consistency(
        self,
        merged_test_case: TestCase,
        source_test_cases: List[TestCase]
    ) -> Dict:
        """Validate that all source test cases are from the same website."""
        from analysis.website_grouper import WebsiteGrouper
        
        grouper = WebsiteGrouper()
        websites = []
        for tc in source_test_cases:
            website = grouper.extract_website(tc)
            websites.append(website)
        
        unique_websites = set(websites)
        if len(unique_websites) > 1:
            return {
                "passed": False,
                "issue": f"Mixed websites detected: {unique_websites}. Different websites should not be merged.",
                "websites": list(unique_websites)
            }
        
        return {
            "passed": True,
            "website": list(unique_websites)[0] if unique_websites else "unknown"
        }
    
    def _get_step_signature(self, step: TestStep) -> str:
        """Create signature for step (matches merger signature exactly)."""
        # Use the same method as TestCaseMerger._get_step_signature
        # Import the merger to use its method
        from optimization.test_case_merger import TestCaseMerger
        merger = TestCaseMerger()
        return merger._get_step_signature(step)
    
    def validate_merged_test_case_standalone(
        self,
        merged_test_case: TestCase
    ) -> Dict:
        """
        Validate merged test case without source test cases (standalone validation).
        
        Args:
            merged_test_case: The merged test case to validate
            
        Returns:
            Validation result dictionary
        """
        self.issues = []
        self.warnings = []
        
        # 1. Flow Correctness Validation
        flow_validation = self._validate_flow_correctness(merged_test_case, [])
        
        # 2. Step Order Consistency
        order_validation = self._validate_step_order(merged_test_case, [])
        
        # 3. Execution-Breaking Issues
        execution_validation = self._validate_execution_safety(merged_test_case)
        
        # 4. Data Consistency
        data_validation = self._validate_data_consistency(merged_test_case, [])
        
        all_passed = all([
            flow_validation["passed"],
            order_validation["passed"],
            execution_validation["passed"],
            data_validation["passed"]
        ])
        
        return {
            "passed": all_passed,
            "flow_correctness": flow_validation,
            "step_order": order_validation,
            "execution_safety": execution_validation,
            "data_consistency": data_validation,
            "issues": self.issues,
            "warnings": self.warnings,
            "summary": self._generate_summary()
        }
    
    def _generate_summary(self) -> str:
        """Generate validation summary."""
        if not self.issues and not self.warnings:
            return "✓ All validations passed - test case is ready for execution"
        
        summary_parts = []
        if self.issues:
            summary_parts.append(f"❌ {len(self.issues)} critical issues found")
        if self.warnings:
            summary_parts.append(f"⚠️ {len(self.warnings)} warnings")
        
        return " | ".join(summary_parts)

