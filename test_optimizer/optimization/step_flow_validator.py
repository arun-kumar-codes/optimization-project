"""
Step Flow Validator - Ensures logical step ordering and consistency.
"""
from typing import List, Dict, Tuple, Optional
from data.models import TestStep


class StepFlowValidator:
    """Validates and fixes step flow consistency."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self._logout_step = None  # Store logout step to add at end
    
    def validate_and_fix_step_sequence(self, steps: List[TestStep]) -> Tuple[List[TestStep], List[str]]:
        """
        Validate step sequence and fix ordering issues.
        
        Returns:
            (fixed_steps, issues_found)
        """
        if not steps:
            return steps, []
        
        fixed_steps = []
        issues = []
        state = {"logged_in": False, "logged_out": False, "current_page": None}
        
        i = 0
        while i < len(steps):
            step = steps[i]
            action = step.action_name or ""
            action_text = (step.action or "").lower()
            element = (step.element or "").lower() if step.element else ""
            
            # Check for logout FIRST (before state tracking)
            # Check 5: Skip ALL logout steps in the middle (we'll add one at the end)
            has_logout = ("logout" in action_text or 
                         (element and "logout" in element.lower()) or
                         (step.raw_data and isinstance(step.raw_data, dict) and 
                          "logout" in str(step.raw_data.get("event", {}).get("label", "")).lower()))
            
            if has_logout:
                # Store the FIRST logout step we find for later, but skip ALL logout steps now
                if self._logout_step is None:
                    self._logout_step = step
                # Update state to logged_out so subsequent steps are skipped
                state["logged_in"] = False
                state["logged_out"] = True
                issues.append(f"Step {i+1}: Logout found in middle - skipping (will add at end)")
                i += 1
                continue
            
            # Track state - detect login completion (after checking for logout)
            if action == "click" and element and "login" in element.lower():
                # Login button clicked - user is now logged in
                state["logged_in"] = True
                state["logged_out"] = False
            elif "login" in action_text and action == "click" and ("button" in action_text or element == "login"):
                state["logged_in"] = True
                state["logged_out"] = False
            
            # Check 1: After login, skip password/username related steps (already logged in)
            if state["logged_in"] and i > 0:
                # Skip password field clicks/entries after login
                # Check both element field and action text (element might be None but action text has it)
                has_password = (element and "password" in element.lower()) or "password" in action_text
                has_username = (element and "username" in element.lower()) or "username" in action_text
                
                if action == "click" and has_password:
                    # Also check event.label if available
                    if step.raw_data and isinstance(step.raw_data, dict):
                        event = step.raw_data.get("event", {})
                        if isinstance(event, dict) and "password" in str(event.get("label", "")).lower():
                            has_password = True
                    
                    if has_password:
                        issues.append(f"Step {i+1}: Clicking password field after login - skipping")
                        i += 1
                        continue
                
                if action in ["enter", "type", "input"] and has_password:
                    issues.append(f"Step {i+1}: Entering password after login - skipping")
                    i += 1
                    continue
                
                # Skip username field clicks after login (unless it's a search field)
                if action == "click" and has_username and "search" not in action_text.lower():
                    issues.append(f"Step {i+1}: Clicking username field after login - skipping")
                    i += 1
                    continue
            
            # Check 2: After logout, must navigate or login before other actions
            if state["logged_out"] and i > 0:
                if action not in ["navigateTo"] and "login" not in action_text:
                    # Skip steps that require being logged in
                    if action in ["enter", "type", "input"]:
                        test_data_str = str(step.test_data or "").lower()
                        # Skip entering credentials/data after logout (unless it's part of login flow)
                        if "admin" in test_data_str or "password" in action_text or "username" in action_text:
                            issues.append(f"Step {i+1}: Entering data after logout - skipping")
                            i += 1
                            continue
                    elif action == "click" and "search" not in action_text and "dropdown" not in action_text:
                        # Skip clicks after logout (except search/dropdown which might be on login page)
                        issues.append(f"Step {i+1}: Clicking after logout without navigation - skipping")
                        i += 1
                        continue
            
            # Check 2: Enter data should have click before it (unless it's a search field)
            if action in ["enter", "type", "input"] and element:
                if "search" not in action_text and "search" not in element:
                    # Check if previous steps clicked this element
                    found_click = False
                    for j in range(max(0, i-3), i):
                        prev = steps[j]
                        if prev.action_name == "click":
                            prev_elem = (prev.element or "").lower()
                            if prev_elem == element or ("username" in prev_elem and "username" in element):
                                found_click = True
                                break
                    
                    if not found_click and i > 0:
                        # Add a click step before enter
                        click_step = TestStep(
                            id=step.id,
                            position=len(fixed_steps) + 1,
                            action_name="click",
                            action=f"Click on {step.element}",
                            element=step.element,
                            description=f"Click on {step.element}",
                            locator=step.locator,
                            test_data=None,
                            wait_time=step.wait_time,
                            test_case_id=step.test_case_id,
                            raw_data=step.raw_data
                        )
                        fixed_steps.append(click_step)
                        issues.append(f"Step {i+1}: Added click before enter for '{step.element}'")
            
            # Check 3: Remove duplicate consecutive actions on same element
            if i > 0 and len(fixed_steps) > 0:
                prev_step = fixed_steps[-1]
                if (prev_step.action_name == action and 
                    prev_step.element == step.element and
                    action in ["click", "enter", "type", "input"]):
                    # Check if it's a search field (might be OK)
                    if "search" not in action_text and "search" not in (prev_step.action or "").lower():
                        # Also check if elements are both None (might be different actions)
                        if step.element is not None or prev_step.element is not None:
                            issues.append(f"Step {i+1}: Duplicate {action} on '{step.element or 'element'}' - skipping")
                            i += 1
                            continue
            
            # Check 4: Remove redundant navigation to same URL
            if action == "navigateTo" and step.test_data:
                if len(fixed_steps) > 0:
                    prev_step = fixed_steps[-1]
                    if (prev_step.action_name == "navigateTo" and 
                        prev_step.test_data == step.test_data):
                        issues.append(f"Step {i+1}: Duplicate navigation to same URL - skipping")
                        i += 1
                        continue
            
            
            # Check 6: Remove steps that don't make sense after logout
            if state["logged_out"]:
                if action in ["enter", "type", "input"]:
                    test_data = str(step.test_data or "")
                    # Skip entering credentials after logout (unless it's part of login)
                    if ("admin" in test_data.lower() or "password" in action_text) and "login" not in action_text:
                        issues.append(f"Step {i+1}: Entering data after logout without login - skipping")
                        i += 1
                        continue
                elif action == "click" and "search" not in action_text and "dropdown" not in action_text:
                    # Skip clicks after logout (except search/dropdown which might be on login page)
                    issues.append(f"Step {i+1}: Clicking after logout without navigation - skipping")
                    i += 1
                    continue
                elif action not in ["navigateTo"]:
                    # Skip any action after logout that's not navigation
                    issues.append(f"Step {i+1}: Action after logout without navigation - skipping")
                    i += 1
                    continue
            
            # Step is OK, add it
            new_step = TestStep(
                id=step.id,
                position=len(fixed_steps) + 1,
                action_name=step.action_name,
                action=step.action,
                element=step.element,
                description=step.description,
                locator=step.locator,
                test_data=step.test_data,
                wait_time=step.wait_time,
                test_case_id=step.test_case_id,
                raw_data=step.raw_data
            )
            fixed_steps.append(new_step)
            i += 1
        
        # CRITICAL: Add logout at the end if there was a logout step
        # Check if we stored a logout step
        if self._logout_step is not None:
            # Check if last step is already logout
            last_is_logout = False
            if fixed_steps:
                last_action = (fixed_steps[-1].action or "").lower()
                if "logout" in last_action:
                    last_is_logout = True
            
            if not last_is_logout:
                # Add logout as the last step
                logout_step = TestStep(
                    id=self._logout_step.id,
                    position=len(fixed_steps) + 1,
                    action_name=self._logout_step.action_name,
                    action=self._logout_step.action,
                    element=self._logout_step.element,
                    description=self._logout_step.description,
                    locator=self._logout_step.locator,
                    test_data=self._logout_step.test_data,
                    wait_time=self._logout_step.wait_time,
                    test_case_id=self._logout_step.test_case_id,
                    raw_data=self._logout_step.raw_data
                )
                fixed_steps.append(logout_step)
                issues.append(f"Added logout as final step (step {len(fixed_steps)})")
        
        # Re-number positions
        for idx, step in enumerate(fixed_steps, 1):
            step.position = idx
        
        return fixed_steps, issues
    
    def validate_step_dependencies(self, steps: List[TestStep]) -> List[str]:
        """Validate that step dependencies are maintained."""
        issues = []
        
        for i, step in enumerate(steps):
            action = step.action_name or ""
            action_text = (step.action or "").lower()
            element = step.element or ""
            
            # Navigation should come before actions on a page
            if action in ["click", "enter", "type", "input"] and i > 0:
                # Check if we have navigation in recent steps
                has_navigation = False
                for j in range(max(0, i-5), i):
                    if steps[j].action_name == "navigateTo":
                        has_navigation = True
                        break
                
                # First action after login might not need navigation
                if not has_navigation and i > 10:
                    # This might be OK if we're on the same page
                    pass
            
            # Click should come before enter for same element
            if action in ["enter", "type", "input"] and element:
                if "search" not in action_text:
                    found_click = False
                    for j in range(max(0, i-3), i):
                        prev = steps[j]
                        if prev.action_name == "click":
                            prev_elem = prev.element or ""
                            if prev_elem.lower() == element.lower():
                                found_click = True
                                break
                    
                    if not found_click:
                        issues.append(f"Step {i+1}: Entering into '{element}' without clicking it first")
        
        return issues

