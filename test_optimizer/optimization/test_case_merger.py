"""
Module for identifying and merging test cases.
Enhanced to create actual merged TestCase objects.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import hashlib
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase, TestStep
from analysis.similarity_analyzer import SimilarityAnalyzer
from analysis.step_uniqueness_analyzer import StepUniquenessAnalyzer
from analysis.prefix_analyzer import PrefixAnalyzer
from flows.flow_analyzer import FlowAnalyzer


class TestCaseMerger:
    """Identifies and merges test cases to preserve all unique steps."""
    
    def __init__(self, merge_threshold: float = 0.70, role_classifications: Dict[int, str] = None):
        """
        Initialize test case merger.
        
        Args:
            merge_threshold: Similarity threshold for considering merge (0.0 to 1.0)
            role_classifications: Optional dictionary mapping test case ID to role
        """
        self.similarity_analyzer = SimilarityAnalyzer()
        self.step_uniqueness_analyzer = StepUniquenessAnalyzer()
        self.prefix_analyzer = PrefixAnalyzer()
        self.flow_analyzer = FlowAnalyzer()
        self.merge_threshold = merge_threshold
        self.role_classifications = role_classifications or {}
    
    def identify_merge_candidates(
        self,
        test_cases: Dict[int, TestCase]
    ) -> List[Dict]:
        """
        Identify test cases that can be merged.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            List of merge candidate groups
        """
        merge_candidates = []
        test_case_ids = list(test_cases.keys())
        
        # Find similar pairs that could be merged
        for i in range(len(test_case_ids)):
            for j in range(i + 1, len(test_case_ids)):
                id1 = test_case_ids[i]
                id2 = test_case_ids[j]
                
                tc1 = test_cases[id1]
                tc2 = test_cases[id2]
                
                # Check similarity
                similarity_result = self.similarity_analyzer.calculate_comprehensive_similarity(tc1, tc2)
                similarity = similarity_result["overall"]
                
                # Check if they're mergeable
                if similarity >= self.merge_threshold:
                    role1 = self.role_classifications.get(id1, "unknown")
                    role2 = self.role_classifications.get(id2, "unknown")
                    if role1 != role2 or role1 == "unknown":
                        continue
                    
                    merge_info = self._analyze_merge_feasibility(tc1, tc2, similarity)
                    if merge_info["can_merge"]:
                        merge_candidates.append(merge_info)
        
        # Sort by similarity (highest first)
        merge_candidates.sort(key=lambda x: x["similarity"], reverse=True)
        
        return merge_candidates
    
    def should_merge_instead_of_remove(
        self,
        test_case1: TestCase,
        test_case2: TestCase
    ) -> bool:
        """
        Decision logic: merge vs remove.
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            
        Returns:
            True if should merge, False if should remove
        """
        # Identify unique steps
        uniqueness_result = self.step_uniqueness_analyzer.identify_unique_steps(
            test_case1,
            test_case2
        )
        
        unique_in_1 = uniqueness_result["unique_in_test_case_1"]["total"]
        unique_in_2 = uniqueness_result["unique_in_test_case_2"]["total"]
        
        should_merge = unique_in_1 > 0 and unique_in_2 > 0
        
        return should_merge
    
    def generate_merged_test_case(
        self,
        test_case1: TestCase,
        test_case2: TestCase,
        new_test_case_id: Optional[int] = None
    ) -> TestCase:
        """
        Generate an actual merged TestCase object.
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            new_test_case_id: Optional new ID for merged test case
            
        Returns:
            Merged TestCase object
        """
        print(f"      [MERGER] Merging TC{test_case1.id} ({len(test_case1.steps)} steps) + TC{test_case2.id} ({len(test_case2.steps)} steps)...")
        
        uniqueness_result = self.step_uniqueness_analyzer.identify_unique_steps(
            test_case1,
            test_case2
        )
        unique_1 = uniqueness_result["unique_in_test_case_1"]["total"]
        unique_2 = uniqueness_result["unique_in_test_case_2"]["total"]
        print(f"      [MERGER] Unique steps: TC{test_case1.id} has {unique_1} unique, TC{test_case2.id} has {unique_2} unique")
        
        steps1 = sorted(test_case1.steps, key=lambda s: s.position)
        steps2 = sorted(test_case2.steps, key=lambda s: s.position)
        
        merged_steps = self._merge_steps_intelligently(steps1, steps2)
        print(f"      [MERGER] Merged to {len(merged_steps)} steps (from {len(steps1) + len(steps2)} total)")
        
        # CRITICAL: Use AI to order steps and remove duplicates
        try:
            from ai.step_orderer import AIStepOrderer
            ai_orderer = AIStepOrderer()
            print(f"      [MERGER] Using AI to order {len(merged_steps)} steps semantically...")
            merged_steps, ai_issues = ai_orderer.order_steps_semantically(merged_steps)
            if ai_issues:
                print(f"      [MERGER] AI found {len(ai_issues)} ordering issues")
                for issue in ai_issues[:3]:
                    print(f"      [MERGER]   - {issue}")
        except Exception as e:
            print(f"      [MERGER] AI ordering unavailable: {e}, using validator instead")
            from optimization.step_flow_validator import StepFlowValidator
            flow_validator = StepFlowValidator()
            merged_steps, flow_issues = flow_validator.validate_and_fix_step_sequence(merged_steps)
            if flow_issues:
                print(f"      [MERGER] Fixed {len(flow_issues)} flow consistency issues")
        
        # FINAL CLEANUP: Remove duplicate login steps (same as in merge_multiple_test_cases)
        final_clean_steps = []
        login_complete = False
        removed_count = 0
        for step in merged_steps:
            action_text = (step.action or "").lower()
            element = (step.element or "").lower() if step.element else ""
            
            if step.action_name == "click" and "login" in action_text:
                login_complete = True
                final_clean_steps.append(step)
                continue
            
            if login_complete:
                # MORE PRECISE: Only remove steps that are ACTUALLY duplicate login sequences
                # Not just any step that mentions username/password (could be search fields, etc.)
                is_duplicate_login = False
                
                # Pattern 1: Focus on Username/Password Input Field (login field, not search)
                if "focus" in action_text:
                    if ("username input field" in action_text or "password input field" in action_text):
                        is_duplicate_login = True
                    # Don't remove "Focus on Username Search Field" - that's legitimate
                
                # Pattern 2: Entering credentials into login fields (not search)
                elif step.action_name in ["enter", "type", "input"]:
                    # Only remove if it's entering admin/admin123 AND it's a login field (not search)
                    test_data_str = str(step.test_data or "").lower()
                    is_admin_credential = ("admin" in test_data_str and "admin123" in test_data_str) or test_data_str == "admin" or test_data_str == "admin123"
                    is_login_field = (
                        ("username" in action_text and "search" not in action_text and "search" not in element) or
                        ("password" in action_text)
                    )
                    # Only remove if BOTH: it's admin credentials AND it's a login field
                    if is_admin_credential and is_login_field:
                        is_duplicate_login = True
                
                # Pattern 3: Clicking login button again
                elif step.action_name == "click" and "login" in action_text and ("button" in action_text or step.element is None or (step.element and "login" in step.element.lower())):
                    is_duplicate_login = True
                
                # Pattern 4: Clicking username/password fields for login (not search)
                elif step.action_name == "click":
                    # Only if it's clearly a login field click, not a search field
                    if (("username" in action_text or "username" in element) and "search" not in action_text and "search" not in element and "input field" in action_text):
                        is_duplicate_login = True
                    elif ("password" in action_text or "password" in element) and "search" not in action_text:
                        is_duplicate_login = True
                
                if is_duplicate_login:
                    removed_count += 1
                    continue
            
            final_clean_steps.append(step)
        
        merged_steps = final_clean_steps
        if removed_count > 0:
            print(f"      [MERGER] Final cleanup: Removed {removed_count} duplicate login steps. Final step count: {len(merged_steps)}")
        
        # Re-number positions
        for idx, step in enumerate(merged_steps, start=1):
            step.position = idx
        
        if new_test_case_id is None:
            new_test_case_id = self.generate_merged_test_case_id([test_case1.id, test_case2.id])
        
        merged_metadata = self.preserve_merged_metadata([test_case1, test_case2])
        
        flows1 = self.flow_analyzer.identify_flow_type(test_case1)
        flows2 = self.flow_analyzer.identify_flow_type(test_case2)
        combined_flows = list(set(flows1 + flows2))
        
        merged_name = f"Merged: {test_case1.name} + {test_case2.name}"
        if len(merged_name) > 100:
            merged_name = f"Merged Test Case {test_case1.id} + {test_case2.id}"
        
        merged_description = (
            f"Combined test case merging:\n"
            f"- {test_case1.name} (ID: {test_case1.id})\n"
            f"- {test_case2.name} (ID: {test_case2.id})\n"
            f"Preserves all unique steps from both test cases."
        )
        
        merged_test_case = TestCase(
            id=new_test_case_id,
            name=merged_name,
            description=merged_description,
            priority=min(test_case1.priority or 5, test_case2.priority or 5),
            status=test_case1.status or test_case2.status or "READY",
            duration=(test_case1.duration or 0) + (test_case2.duration or 0),
            pass_count=test_case1.pass_count,
            fail_count=test_case1.fail_count,
            tags=list(set((test_case1.tags or []) + (test_case2.tags or []))),
            steps=merged_steps,
            prerequisite_case=test_case1.prerequisite_case or test_case2.prerequisite_case,
            test_data_id=test_case1.test_data_id or test_case2.test_data_id,
            last_run_result=test_case1.last_run_result or test_case2.last_run_result,
            created_date=min(
                test_case1.created_date or 0,
                test_case2.created_date or 0
            ) if (test_case1.created_date and test_case2.created_date) else None,
            updated_date=max(
                test_case1.updated_date or 0,
                test_case2.updated_date or 0
            ) if (test_case1.updated_date or test_case2.updated_date) else None,
            raw_data={
                "source_test_cases": [test_case1.id, test_case2.id],
                "merged_from": [test_case1.raw_data, test_case2.raw_data] if (test_case1.raw_data and test_case2.raw_data) else None,
                "merged_metadata": merged_metadata,
                "combined_flows": combined_flows
            }
        )
        
        return merged_test_case
    
    def merge_test_cases_intelligently(
        self,
        test_cases_list: List[TestCase],
        new_test_case_id: Optional[int] = None
    ) -> TestCase:
        """
        Merge multiple test cases into one (iterative pair merging).
        
        Args:
            test_cases_list: List of test cases to merge
            new_test_case_id: Optional new ID for merged test case
            
        Returns:
            Merged TestCase object
        """
        if len(test_cases_list) == 0:
            raise ValueError("Cannot merge empty list of test cases")
        
        if len(test_cases_list) == 1:
            return test_cases_list[0]
        
        merged = test_cases_list[0]
        
        for i in range(1, len(test_cases_list)):
            merged = self.generate_merged_test_case(
                merged,
                test_cases_list[i],
                new_test_case_id if i == len(test_cases_list) - 1 else None
            )
        
        return merged
    
    def merge_multiple_test_cases(
        self,
        test_cases: List[TestCase],
        new_test_case_id: Optional[int] = None
    ) -> TestCase:
        """
        Merge multiple test cases using prefix/suffix strategy (NEW - Phase 4).
        
        Strategy: [Common Prefix] + [All Unique Middles] + [Common Suffix]
        
        Args:
            test_cases: List of TestCase objects to merge (3+ test cases)
            new_test_case_id: Optional new ID for merged test case
            
        Returns:
            Merged TestCase object
        """
        if len(test_cases) == 0:
            raise ValueError("Cannot merge empty list of test cases")
        
        if len(test_cases) == 1:
            return test_cases[0]
        
        if len(test_cases) == 2:
            return self.generate_merged_test_case(test_cases[0], test_cases[1], new_test_case_id)
        
        print(f"      [MERGER] Merging {len(test_cases)} test cases using comprehensive step preservation...")
        source_ids = [tc.id for tc in test_cases]
        print(f"      [MERGER] Source test cases: {source_ids}")
        
        # CORRECT STRATEGY: [Common Login] + [All Unique Middle Steps] + [Common Logout]
        # Goal: Login once, run all unique test scenarios, logout once
        # CRITICAL: Preserve ALL unique steps - no step should be lost
        
        # Step 1: Find common prefix (login) and suffix (logout) for ordering
        # ENHANCED: Use flexible merge points that handle mixed login scenarios
        merge_points = self.prefix_analyzer.identify_flexible_merge_points(test_cases)
        prefix_steps = merge_points["prefix"]  # Common login steps (or longest login if mixed)
        suffix_steps = merge_points["suffix"]  # Common logout steps
        prefix_length = len(prefix_steps)
        suffix_length = len(suffix_steps)
        has_mixed_login = merge_points.get("mixed_login", False)
        
        print(f"      [MERGER] Common prefix (login): {len(prefix_steps)} steps")
        print(f"      [MERGER] Common suffix (logout): {len(suffix_steps)} steps")
        
        # Step 2: Collect ALL steps from ALL test cases with signatures
        # This ensures we don't lose any steps
        all_steps_map = {}  # signature -> (step, test_case_id, original_position)
        all_steps_list = []  # Keep ALL steps in order for verification
        for tc in test_cases:
            steps = sorted(tc.steps, key=lambda s: s.position)
            for idx, step in enumerate(steps):
                step_sig = self._get_step_signature(step)
                all_steps_list.append((step, step_sig, tc.id, idx))
                # Keep the first occurrence of each unique step
                if step_sig not in all_steps_map:
                    all_steps_map[step_sig] = (step, tc.id, idx)
        
        # Step 3: Build merged steps: [Prefix] + [All Unique Middles] + [Suffix]
        merged_steps = []
        seen_step_signatures = set()
        position = 1
        
        # Add common prefix (login steps - appear in ALL test cases)
        prefix_sigs = set()
        for step in prefix_steps:
            step_sig = self._get_step_signature(step)
            prefix_sigs.add(step_sig)
            if step_sig not in seen_step_signatures:
                new_step = TestStep(
                    id=step.id,
                    position=position,
                    action_name=step.action_name,
                    action=step.action,
                    element=step.element,
                    description=step.description,
                    locator=step.locator,
                    test_data=step.test_data,
                    wait_time=step.wait_time,
                    test_case_id=None,
                    raw_data=step.raw_data
                )
                merged_steps.append(new_step)
                seen_step_signatures.add(step_sig)
                position += 1
        
        # Add ALL unique middle steps (not in prefix or suffix)
        # Preserve order by collecting from each test case's middle section
        # ENHANCED: Handle mixed login scenarios where some test cases have login, others don't
        middle_steps_by_tc = []
        login_sections = merge_points.get("login_sections", [])
        
        for idx, tc in enumerate(test_cases):
            steps = sorted(tc.steps, key=lambda s: s.position)
            
            if has_mixed_login and login_sections and idx < len(login_sections):
                # For mixed login: use login section info from merge_points
                ls = login_sections[idx]
                if ls.get("has_login", False):
                    # Has login - start after its login section
                    middle_start = ls.get("end", prefix_length)
                else:
                    # No login - all steps are post-login (start from beginning)
                    middle_start = 0
            else:
                # Standard: start after common prefix
                middle_start = prefix_length
            
            middle_end = len(steps) - suffix_length if suffix_length > 0 else len(steps)
            middle_steps = steps[middle_start:middle_end]
            middle_steps_by_tc.append((tc.id, middle_steps))
        
        # Collect all unique middle steps, preserving order
        # CRITICAL: Exclude any login-related steps from middle sections
        suffix_sigs = {self._get_step_signature(s) for s in suffix_steps}
        
        # Helper function to check if step is a duplicate login step
        # ENHANCED: Detect duplicate login sequences after initial login
        def is_duplicate_login_step(step, prefix_sigs, current_position):
            """Check if step is a duplicate login step that should be excluded."""
            step_sig = self._get_step_signature(step)
            
            # If this step signature is already in the prefix, it's a duplicate
            if step_sig in prefix_sigs:
                return True
            
            # Check if it's navigating to login page (should only be in prefix)
            if step.action_name == "navigateTo":
                if step.raw_data and isinstance(step.raw_data, dict):
                    event = step.raw_data.get("event", {})
                    if isinstance(event, dict):
                        href = event.get("href", "")
                        if "/auth/login" in href.lower() or "/login" in href.lower():
                            return True  # Duplicate login navigation
            
            # MORE PRECISE: Only detect ACTUAL duplicate login sequences
            # Not just any step that mentions username/password (could be search fields, etc.)
            action_lower = (step.action_name or "").lower()
            action_text = (step.action or "").lower()
            element_lower = (step.element or "").lower() if step.element else ""
            test_data_str = str(step.test_data or "").lower()
            
            # Pattern 1: Entering admin/admin123 credentials into login fields (not search)
            if action_lower in ["enter", "type", "input"]:
                is_admin_credential = test_data_str == "admin" or test_data_str == "admin123" or ("admin" in test_data_str and "admin123" in test_data_str)
                is_login_field = (
                    ("username" in element_lower or "username" in action_text) and 
                    "search" not in action_text and "search" not in element_lower
                ) or ("password" in element_lower or "password" in action_text)
                
                # Only remove if BOTH: admin credentials AND login field (not search)
                if is_admin_credential and is_login_field:
                    return True
            
            # Pattern 2: Clicking login button again
            if action_lower == "click" and "login" in action_text.lower():
                # Only if it's clearly a login button, not a search field
                if "search" not in action_text.lower() and "search" not in element_lower:
                    return True
            
            # Pattern 3: Clicking username/password input fields for login (not search)
            if action_lower == "click":
                # Only if it's clearly a login field click, not a search field
                if (("username" in action_text or "username" in element_lower) and 
                    "search" not in action_text and "search" not in element_lower and 
                    "input field" in action_text):
                    return True
                elif ("password" in action_text or "password" in element_lower) and "search" not in action_text:
                    return True
            
            return False
        
        # CRITICAL FIX: Collect ALL unique steps from all_steps_map that aren't in prefix/suffix
        # This ensures we don't lose ANY steps
        # Build a map of step_sig -> step for quick lookup
        steps_to_add = {}  # step_sig -> step (from all_steps_map)
        for step_sig, (step, tc_id, orig_pos) in all_steps_map.items():
            if step_sig not in prefix_sigs and step_sig not in suffix_sigs:
                steps_to_add[step_sig] = step
        
        print(f"      [MERGER] DEBUG: all_steps_map has {len(all_steps_map)} unique steps")
        print(f"      [MERGER] DEBUG: prefix_sigs has {len(prefix_sigs)} steps")
        print(f"      [MERGER] DEBUG: suffix_sigs has {len(suffix_sigs)} steps")
        print(f"      [MERGER] DEBUG: steps_to_add has {len(steps_to_add)} steps (should be {len(all_steps_map) - len(prefix_sigs) - len(suffix_sigs)})")
        
        # Now add them in order from middle_steps_by_tc to preserve logical flow
        # CRITICAL: Only skip if already added, NOT if in prefix_sigs (step might be in middle of another TC)
        for tc_id, middle_steps in middle_steps_by_tc:
            for step in middle_steps:
                step_sig = self._get_step_signature(step)
                
                # Skip if already added (duplicate across test cases)
                if step_sig in seen_step_signatures:
                    continue
                
                # Skip if in suffix (logout - should only be at end)
                if step_sig in suffix_sigs:
                    continue
                
                # Skip duplicate login navigation (navigateTo to login page) - but only if not already in prefix
                if step.action_name == "navigateTo":
                    if step.raw_data and isinstance(step.raw_data, dict):
                        event = step.raw_data.get("event", {})
                        if isinstance(event, dict):
                            href = event.get("href", "")
                            if "/auth/login" in href.lower() or "/login" in href.lower():
                                # Only skip if it's already in prefix (duplicate)
                                if step_sig in prefix_sigs:
                                    continue
                
                # Add this unique step (use step from all_steps_map if available, otherwise use step from middle)
                if step_sig in steps_to_add:
                    step_to_add = steps_to_add[step_sig]
                else:
                    # Step not in steps_to_add means it's in prefix_sigs - skip it (already added in prefix)
                    if step_sig in prefix_sigs:
                        continue
                    step_to_add = step
                
                new_step = TestStep(
                    id=step_to_add.id,
                    position=position,
                    action_name=step_to_add.action_name,
                    action=step_to_add.action,
                    element=step_to_add.element,
                    description=step_to_add.description,
                    locator=step_to_add.locator,
                    test_data=step_to_add.test_data,
                    wait_time=step_to_add.wait_time,
                    test_case_id=None,
                    raw_data=step_to_add.raw_data
                )
                merged_steps.append(new_step)
                seen_step_signatures.add(step_sig)
                position += 1
        
        # CRITICAL: Add ALL remaining unique steps that weren't in middle_steps_by_tc
        # This ensures we don't lose ANY steps
        remaining_count = 0
        for step_sig, step in steps_to_add.items():
            if step_sig not in seen_step_signatures:
                # Skip duplicate login navigation
                if step.action_name == "navigateTo":
                    if step.raw_data and isinstance(step.raw_data, dict):
                        event = step.raw_data.get("event", {})
                        if isinstance(event, dict):
                            href = event.get("href", "")
                            if "/auth/login" in href.lower() or "/login" in href.lower():
                                if step_sig in prefix_sigs:
                                    continue  # Skip duplicate login navigation
                
                remaining_count += 1
                new_step = TestStep(
                    id=step.id,
                    position=position,
                    action_name=step.action_name,
                    action=step.action,
                    element=step.element,
                    description=step.description,
                    locator=step.locator,
                    test_data=step.test_data,
                    wait_time=step.wait_time,
                    test_case_id=None,
                    raw_data=step.raw_data
                )
                merged_steps.append(new_step)
                seen_step_signatures.add(step_sig)
                position += 1
        
        if remaining_count > 0:
            print(f"      [MERGER] DEBUG: Added {remaining_count} remaining steps that weren't in middle_steps_by_tc")
        
        print(f"      [MERGER] DEBUG: Final merged_steps count: {len(merged_steps)} (expected: {len(prefix_steps) + len(steps_to_add) + len(suffix_steps)})")
        
        # Add common suffix (logout steps - appear in ALL test cases)
        for step in suffix_steps:
            step_sig = self._get_step_signature(step)
            if step_sig not in seen_step_signatures:
                new_step = TestStep(
                    id=step.id,
                    position=position,
                    action_name=step.action_name,
                    action=step.action,
                    element=step.element,
                    description=step.description,
                    locator=step.locator,
                    test_data=step.test_data,
                    wait_time=step.wait_time,
                    test_case_id=None,
                    raw_data=step.raw_data
                )
                merged_steps.append(new_step)
                seen_step_signatures.add(step_sig)
                position += 1
        
        # CRITICAL: Use AI to order steps semantically (but preserve ALL steps)
        original_step_count = len(merged_steps)
        original_step_signatures = {self._get_step_signature(s) for s in merged_steps}
        original_merged_steps = merged_steps.copy()  # Keep a copy to restore from
        
        try:
            from ai.step_orderer import AIStepOrderer
            ai_orderer = AIStepOrderer()
            print(f"      [MERGER] Using AI to order {len(merged_steps)} steps semantically...")
            merged_steps, ai_issues = ai_orderer.order_steps_semantically(merged_steps)
            
            # CRITICAL: Verify AI didn't remove steps - restore any that were removed
            if len(merged_steps) < original_step_count:
                lost = original_step_count - len(merged_steps)
                print(f"      [MERGER] ⚠ WARNING: AI removed {lost} steps! Restoring them...")
                
                # Restore missing steps by finding which ones are missing
                current_signatures = {self._get_step_signature(s) for s in merged_steps}
                missing_signatures = original_step_signatures - current_signatures
                
                # Find the original steps that are missing and restore them
                restored_count = 0
                for orig_step in original_merged_steps:
                    orig_sig = self._get_step_signature(orig_step)
                    if orig_sig in missing_signatures:
                        # This step was removed by AI - restore it
                        restored_step = TestStep(
                            id=orig_step.id,
                            position=len(merged_steps) + 1,
                            action_name=orig_step.action_name,
                            action=orig_step.action,
                            element=orig_step.element,
                            description=orig_step.description,
                            locator=orig_step.locator,
                            test_data=orig_step.test_data,
                            wait_time=orig_step.wait_time,
                            test_case_id=orig_step.test_case_id,
                            raw_data=orig_step.raw_data
                        )
                        merged_steps.append(restored_step)
                        restored_count += 1
                
                if restored_count > 0:
                    print(f"      [MERGER] ✓ Restored {restored_count} steps that AI removed")
                    # Re-number all positions
                    for idx, step in enumerate(merged_steps, 1):
                        step.position = idx
            
            if ai_issues:
                print(f"      [MERGER] AI found {len(ai_issues)} ordering issues")
                for issue in ai_issues[:5]:
                    print(f"      [MERGER]   - {issue}")
        except Exception as e:
            print(f"      [MERGER] AI ordering unavailable: {e}, using validator instead")
            # Fallback to validator
            from optimization.step_flow_validator import StepFlowValidator
            flow_validator = StepFlowValidator()
            merged_steps, flow_issues = flow_validator.validate_and_fix_step_sequence(merged_steps)
            
            if flow_issues:
                print(f"      [MERGER] Fixed {len(flow_issues)} flow consistency issues")
                logout_issues = [issue for issue in flow_issues if 'logout' in issue.lower()]
                if logout_issues:
                    print(f"      [MERGER]   Logout fixes: {len(logout_issues)}")
                for issue in flow_issues[:5]:
                    print(f"      [MERGER]   - {issue}")
        
        # Final validation pass - but don't let it add back duplicates that AI removed
        from optimization.step_flow_validator import StepFlowValidator
        flow_validator = StepFlowValidator()
        
        # Before validation, count steps
        steps_before = len(merged_steps)
        
        merged_steps, final_issues = flow_validator.validate_and_fix_step_sequence(merged_steps)
        
        # After validation, check if duplicates were added back
        steps_after = len(merged_steps)
        if steps_after > steps_before:
            print(f"      [MERGER] ⚠️  Warning: Validator added {steps_after - steps_before} steps back")
        
        if final_issues:
            print(f"      [MERGER] Final validation: {len(final_issues)} issues fixed")
        
        # Re-number positions
        for idx, step in enumerate(merged_steps, 1):
            step.position = idx
        
        # Verify logout is at the end
        if merged_steps:
            last_action = (merged_steps[-1].action or "").lower()
            if "logout" not in last_action:
                # Check if there are any logout steps
                logout_count = sum(1 for s in merged_steps if "logout" in (s.action or "").lower())
                if logout_count > 0:
                    print(f"      [MERGER] ⚠️  Warning: {logout_count} logout steps found, but last step is not logout")
                else:
                    print(f"      [MERGER] ⚠️  Warning: No logout step found in merged test case")
        
        # CRITICAL FIX: Ensure ALL unique steps from all_steps_map are included
        # Some steps might have been missed if they appear in multiple sections
        # Add any missing unique steps from all_steps_map
        # BUT: Exclude logout steps AND duplicate login steps
        merged_step_sigs = {self._get_step_signature(s) for s in merged_steps}
        
        # Find where login completes in merged steps
        login_complete = False
        for step in merged_steps:
            action_text = (step.action or "").lower()
            if step.action_name == "click" and "login" in action_text:
                login_complete = True
                break
        
        for step_sig, (step, tc_id, orig_pos) in all_steps_map.items():
            if step_sig not in merged_step_sigs:
                action_text = (step.action or "").lower()
                element = (step.element or "").lower() if step.element else ""
                
                # Skip logout steps - validator will add one at end
                is_logout = ("logout" in action_text or 
                            (element and "logout" in element.lower()))
                if is_logout:
                    continue
                
                # Skip duplicate login steps after login is complete
                if login_complete:
                    is_duplicate_login = (
                        (("username" in action_text or "username" in element) and "search" not in action_text and "search" not in element) or
                        ("password" in action_text or "password" in element) or
                        ("login" in action_text and step.action_name == "click") or
                        ("focus" in action_text and ("username" in action_text or "password" in action_text or "username" in element or "password" in element)) or
                        (step.action_name in ["enter", "type", "input"] and (
                            "admin" in str(step.test_data or "").lower() or 
                            "admin123" in str(step.test_data or "").lower() or
                            ("username" in action_text and "search" not in action_text) or
                            "password" in action_text
                        )) or
                        ("username input field" in action_text or "password input field" in action_text)
                    )
                    if is_duplicate_login:
                        continue  # Skip duplicate login steps
                
                # This step was missed - add it to middle section
                new_step = TestStep(
                    id=step.id,
                    position=position,
                    action_name=step.action_name,
                    action=step.action,
                    element=step.element,
                    description=step.description,
                    locator=step.locator,
                    test_data=step.test_data,
                    wait_time=step.wait_time,
                    test_case_id=None,
                    raw_data=step.raw_data
                )
                merged_steps.append(new_step)
                merged_step_sigs.add(step_sig)
                position += 1
        
        # Re-sort merged steps by position to maintain order
        merged_steps.sort(key=lambda s: s.position)
        # Re-number positions sequentially
        for idx, step in enumerate(merged_steps, start=1):
            step.position = idx
        
        # CRITICAL: Run validator AGAIN after adding back missing steps
        # This ensures logout is at the end even if steps were added back
        merged_steps, flow_issues_2 = flow_validator.validate_and_fix_step_sequence(merged_steps)
        if flow_issues_2:
            print(f"      [MERGER] Fixed additional {len(flow_issues_2)} flow issues after adding missing steps")
        
        # FINAL CLEANUP: Remove duplicate login steps one more time (safety net)
        print(f"      [MERGER] Running final cleanup on {len(merged_steps)} steps...")
        final_clean_steps = []
        login_complete = False
        removed_count = 0
        for step in merged_steps:
            action_text = (step.action or "").lower()
            element = (step.element or "").lower() if step.element else ""
            
            # Mark login as complete
            if step.action_name == "click" and "login" in action_text:
                login_complete = True
                print(f"      [MERGER] Final cleanup: Login complete at step: {step.action}")
                final_clean_steps.append(step)
                continue
            
            # After login, remove duplicate login steps
            if login_complete:
                # Debug: print all steps after login
                if "username" in action_text or "password" in action_text or "focus" in action_text or "login" in action_text:
                    print(f"      [MERGER] Final cleanup: Processing step after login: {step.action} (action_text='{action_text}', element='{element}')")
                
                is_duplicate_login = (
                    (("username" in action_text or "username" in element) and "search" not in action_text and "search" not in element) or
                    ("password" in action_text or "password" in element) or
                    ("login" in action_text and step.action_name == "click") or
                    ("focus" in action_text and ("username" in action_text or "password" in action_text or "username" in element or "password" in element)) or
                    (step.action_name in ["enter", "type", "input"] and (
                        "admin" in str(step.test_data or "").lower() or 
                        "admin123" in str(step.test_data or "").lower() or
                        ("username" in action_text and "search" not in action_text) or
                        "password" in action_text
                    )) or
                    ("username input field" in action_text or "password input field" in action_text)
                )
                if is_duplicate_login:
                    removed_count += 1
                    print(f"      [MERGER] Final cleanup: ✓ Removing duplicate login step {removed_count}: {step.action}")
                    continue  # Skip duplicate
                else:
                    # Debug: why wasn't it detected?
                    if ("username" in action_text or "password" in action_text or "focus" in action_text):
                        print(f"      [MERGER] Final cleanup: ✗ Step NOT detected as duplicate: {step.action} (why?)")
            
            final_clean_steps.append(step)
        
        merged_steps = final_clean_steps
        if removed_count > 0:
            print(f"      [MERGER] Final cleanup: Removed {removed_count} duplicate login steps. Final step count: {len(merged_steps)}")
        
        # Final re-number
        for idx, step in enumerate(merged_steps, start=1):
            step.position = idx
        
        # Verify: Count unique steps from all test cases
        total_unique_steps_expected = len(all_steps_map)
        total_original_steps = sum(len(tc.steps) for tc in test_cases)
        
        print(f"      [MERGER] Merged to {len(merged_steps)} unique steps (from {total_original_steps} total, {total_unique_steps_expected} unique expected)")
        
        # CRITICAL VALIDATION: Ensure we didn't lose any unique steps
        if len(merged_steps) < total_unique_steps_expected:
            lost_count = total_unique_steps_expected - len(merged_steps)
            print(f"      [MERGER] ⚠ WARNING: Lost {lost_count} unique steps! This should not happen.")
            # This is a bug - we should preserve all unique steps
        elif len(merged_steps) == total_unique_steps_expected:
            print(f"      [MERGER] ✓ All {total_unique_steps_expected} unique steps preserved")
        
        # Generate new ID if not provided
        if new_test_case_id is None:
            new_test_case_id = self.generate_merged_test_case_id(source_ids)
        
        merged_metadata = self.preserve_merged_metadata(test_cases)
        
        # Combine flows
        all_flows = set()
        for tc in test_cases:
            flows = self.flow_analyzer.identify_flow_type(tc)
            all_flows.update(flows)
        combined_flows = list(all_flows)
        
        # Generate merged name
        if len(test_cases) <= 3:
            names = [tc.name for tc in test_cases]
            merged_name = f"Merged: {' + '.join(names)}"
        else:
            merged_name = f"Consolidated Flow ({len(test_cases)} test cases)"
        
        if len(merged_name) > 100:
            merged_name = f"Merged Test Case {'+'.join(str(tc.id) for tc in test_cases)}"
        
        # Create merged description
        source_names = [f"- {tc.name} (ID: {tc.id})" for tc in test_cases]
        merged_description = (
            f"Consolidated test case merging {len(test_cases)} test cases:\n" +
            "\n".join(source_names) +
            f"\n\nPreserves ALL unique steps from all test cases (comprehensive step preservation strategy)."
        )
        
        priorities = [tc.priority for tc in test_cases if tc.priority is not None]
        combined_priority = min(priorities) if priorities else None
        
        # Combine durations
        combined_duration = sum(tc.duration or 0 for tc in test_cases)
        
        # Combine tags
        all_tags = set()
        for tc in test_cases:
            if tc.tags:
                all_tags.update(tc.tags)
        
        # Create merged TestCase object
        merged_test_case = TestCase(
            id=new_test_case_id,
            name=merged_name,
            description=merged_description,
            priority=combined_priority,
            status=test_cases[0].status or "READY",
            duration=combined_duration,
            pass_count=test_cases[0].pass_count,
            fail_count=test_cases[0].fail_count,
            tags=list(all_tags),
            steps=merged_steps,
            prerequisite_case=test_cases[0].prerequisite_case,
            test_data_id=test_cases[0].test_data_id,
            last_run_result=test_cases[0].last_run_result,
            created_date=min(tc.created_date or 0 for tc in test_cases) if any(tc.created_date for tc in test_cases) else None,
            updated_date=max(tc.updated_date or 0 for tc in test_cases) if any(tc.updated_date for tc in test_cases) else None,
            raw_data={
                "source_test_cases": source_ids,
                "merged_from": [tc.raw_data for tc in test_cases if tc.raw_data],
                "merged_metadata": merged_metadata,
                "combined_flows": combined_flows,
                "merge_strategy": "comprehensive_step_preservation",
                "prefix_length": len(prefix_steps),
                "suffix_length": len(suffix_steps),
                "total_unique_steps": len(merged_steps),
                "original_total_steps": sum(len(tc.steps) for tc in test_cases)
            }
        )
        
        return merged_test_case
    
    def create_optimized_merged_test_case(
        self,
        source_test_cases: List[TestCase],
        new_test_case_id: Optional[int] = None
    ) -> TestCase:
        """
        Create new optimized merged test case.
        
        Args:
            source_test_cases: List of source test cases
            new_test_case_id: Optional new ID
            
        Returns:
            Optimized merged TestCase
        """
        merged = self.merge_test_cases_intelligently(source_test_cases, new_test_case_id)
        
        optimized_steps = self._optimize_step_order(merged.steps)
        merged.steps = optimized_steps
        
        return merged
    
    def generate_merged_test_case_id(self, source_ids: List[int]) -> int:
        """
        Generate new ID for merged test case.
        
        Args:
            source_ids: List of source test case IDs
            
        Returns:
            New test case ID
        """
        source_str = "_".join(sorted(str(id) for id in source_ids))
        hash_value = int(hashlib.md5(source_str.encode()).hexdigest()[:8], 16)
        
        new_id = 10000 + (hash_value % 90000)
        
        return new_id
    
    def preserve_merged_metadata(self, source_test_cases: List[TestCase]) -> Dict:
        """
        Combine metadata from source test cases.
        
        Args:
            source_test_cases: List of source test cases
            
        Returns:
            Combined metadata dictionary
        """
        metadata = {
            "source_test_case_ids": [tc.id for tc in source_test_cases],
            "source_names": [tc.name for tc in source_test_cases],
            "combined_tags": [],
            "combined_priorities": [],
            "test_data_ids": []
        }
        
        # Combine tags
        all_tags = set()
        for tc in source_test_cases:
            if tc.tags:
                all_tags.update(tc.tags)
        metadata["combined_tags"] = sorted(list(all_tags))
        
        # Collect priorities
        priorities = [tc.priority for tc in source_test_cases if tc.priority is not None]
        metadata["combined_priorities"] = priorities
        metadata["min_priority"] = min(priorities) if priorities else None
        
        # Collect test data IDs
        test_data_ids = [tc.test_data_id for tc in source_test_cases if tc.test_data_id is not None]
        metadata["test_data_ids"] = list(set(test_data_ids))
        
        # Preserve raw data references
        raw_data_list = [tc.raw_data for tc in source_test_cases if tc.raw_data]
        metadata["raw_data_sources"] = raw_data_list
        
        return metadata
    
    def _get_step_signature(self, step: TestStep) -> str:
        """
        Create signature for step comparison (for deduplication).
        
        CRITICAL: Must match StepCoverageTracker signature to avoid losing steps.
        Includes test_data to distinguish steps with same action but different data.
        
        Args:
            step: TestStep object
            
        Returns:
            Signature string for comparison
        """
        import hashlib
        from data.normalizers import (
            normalize_action_name,
            normalize_element_identifier,
            clean_description
        )
        
        # Use same normalization as StepCoverageTracker
        action = normalize_action_name(step.action_name) if step.action_name else ""
        element = normalize_element_identifier(step.element) or ""
        description = clean_description(step.description) or ""
        if description:
            description = description.lower().strip()
        test_data = str(step.test_data).lower().strip() if step.test_data else ""
        
        # Build signature (must match StepCoverageTracker format)
        signature_parts = [action, element, description, test_data]
        signature_str = "|".join(signature_parts)
        
        # Return MD5 hash for consistency with StepCoverageTracker
        return hashlib.md5(signature_str.encode()).hexdigest()
    
    def _merge_steps_intelligently(
        self,
        steps1: List[TestStep],
        steps2: List[TestStep]
    ) -> List[TestStep]:
        """
        Merge steps intelligently, preserving order and removing duplicates.
        
        Args:
            steps1: Steps from first test case
            steps2: Steps from second test case
            
        Returns:
            Merged list of steps
        """
        merged_steps = []
        seen_step_signatures = set()
        
        # Add steps from first test case
        position = 1
        for step in steps1:
            sig = self._get_step_signature(step)
            if sig not in seen_step_signatures:
               
                new_step = TestStep(
                    id=step.id, 
                    position=position,
                    action_name=step.action_name,
                    action=step.action,
                    element=step.element,
                    description=step.description,
                    locator=step.locator,
                    test_data=step.test_data,
                    wait_time=step.wait_time,
                    test_case_id=None,  
                    raw_data=step.raw_data
                )
                merged_steps.append(new_step)
                seen_step_signatures.add(sig)
                position += 1
        
        # Add unique steps from second test case
        for step in steps2:
            sig = self._get_step_signature(step)
            if sig not in seen_step_signatures:
                new_step = TestStep(
                    id=step.id,
                    position=position,
                    action_name=step.action_name,
                    action=step.action,
                    element=step.element,
                    description=step.description,
                    locator=step.locator,
                    test_data=step.test_data,
                    wait_time=step.wait_time,
                    test_case_id=None,
                    raw_data=step.raw_data
                )
                merged_steps.append(new_step)
                seen_step_signatures.add(sig)
                position += 1
        
        return merged_steps
    
    def _optimize_step_order(self, steps: List[TestStep]) -> List[TestStep]:
        """
        Optimize step order (remove redundant waits, combine similar actions).
        
        Args:
            steps: List of steps to optimize
            
        Returns:
            Optimized list of steps
        """
        if not steps:
            return steps
        
        optimized = []
        prev_step = None
        
        for step in steps:
            
            if step.action_name == "wait" and prev_step and prev_step.wait_time:
                if step.wait_time and step.wait_time <= prev_step.wait_time:
                    continue  
            
           
            optimized.append(step)
            prev_step = step
        
        return optimized
    
    def _analyze_merge_feasibility(
        self,
        test_case1: TestCase,
        test_case2: TestCase,
        similarity: float
    ) -> Dict:
        """
        Analyze if two test cases can be merged.
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            similarity: Similarity score
            
        Returns:
            Merge feasibility analysis
        """
        # Check flow compatibility
        flows1 = set(self.flow_analyzer.identify_flow_type(test_case1))
        flows2 = set(self.flow_analyzer.identify_flow_type(test_case2))
        flow_overlap = len(flows1.intersection(flows2)) > 0
        
        steps1 = sorted(test_case1.steps, key=lambda s: s.position)
        steps2 = sorted(test_case2.steps, key=lambda s: s.position)
        sequential = self._check_sequential(steps1, steps2)
        minor_variations = self._check_minor_variations(steps1, steps2)
        
        can_merge = (
            similarity >= self.merge_threshold and
            (flow_overlap or sequential or minor_variations)
        )
        
        merged_steps = len(steps1) + len(steps2) - self._count_common_steps(steps1, steps2)
        merged_duration = (test_case1.duration or 0) + (test_case2.duration or 0)
        
        return {
            "test_case_1": test_case1.id,
            "test_case_2": test_case2.id,
            "similarity": similarity,
            "can_merge": can_merge,
            "flow_overlap": flow_overlap,
            "sequential": sequential,
            "minor_variations": minor_variations,
            "merged_estimate": {
                "estimated_steps": merged_steps,
                "estimated_duration_ms": merged_duration,
                "combined_flows": list(flows1.union(flows2))
            },
            "recommendation": self._get_merge_recommendation(can_merge, similarity, flow_overlap)
        }
    
    def _check_sequential(self, steps1: List[TestStep], steps2: List[TestStep]) -> bool:
        """Check if test cases are sequential."""
        if not steps1 or not steps2:
            return False
        last_step1 = steps1[-1]
        first_step2 = steps2[0]
        return last_step1.action_name == first_step2.action_name
    
    def _check_minor_variations(self, steps1: List[TestStep], steps2: List[TestStep]) -> bool:
        """Check if test cases have minor variations."""
        if len(steps1) != len(steps2):
            return False
        differences = 0
        for s1, s2 in zip(steps1, steps2):
            if s1.action_name != s2.action_name or s1.element != s2.element:
                differences += 1
        variation_ratio = differences / len(steps1) if steps1 else 0
        return variation_ratio < 0.3
    
    def _count_common_steps(self, steps1: List[TestStep], steps2: List[TestStep]) -> int:
        """Count common steps between two test cases."""
        common = 0
        min_len = min(len(steps1), len(steps2))
        for i in range(min_len):
            if (steps1[i].action_name == steps2[i].action_name and
                steps1[i].element == steps2[i].element):
                common += 1
        return common
    
    def _get_merge_recommendation(
        self,
        can_merge: bool,
        similarity: float,
        flow_overlap: bool
    ) -> str:
        """Get merge recommendation message."""
        if not can_merge:
            return "Cannot merge - too different"
        if similarity >= 0.90:
            return "Strong merge candidate - very similar test cases"
        elif flow_overlap:
            return "Good merge candidate - test similar flows"
        else:
            return "Moderate merge candidate - consider manual review"
