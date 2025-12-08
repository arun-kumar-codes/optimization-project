"""
Module for validating coverage after optimization.
"""

import sys
from pathlib import Path
from typing import Dict, List
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from flows.coverage_analyzer import CoverageAnalyzer
from flows.flow_analyzer import FlowAnalyzer
from optimization.step_coverage_tracker import StepCoverageTracker
from analysis.step_uniqueness_analyzer import StepUniquenessAnalyzer
from analysis.sequence_extractor import SequenceExtractor
from analysis.role_classifier import RoleClassifier
from analysis.website_grouper import WebsiteGrouper
from execution.dependency_analyzer import DependencyAnalyzer


class CoverageValidator:
    """Validates that optimization maintains required coverage."""
    
    def __init__(
        self,
        min_coverage_percentage: float = 0.90,
        min_step_coverage_percentage: float = 0.95
    ):
        """
        Initialize coverage validator.
        
        Args:
            min_coverage_percentage: Minimum flow coverage percentage to maintain (0.0 to 1.0)
            min_step_coverage_percentage: Minimum step coverage percentage to maintain (0.0 to 1.0)
        """
        self.coverage_analyzer = CoverageAnalyzer()
        self.flow_analyzer = FlowAnalyzer()
        self.step_coverage_tracker = StepCoverageTracker()
        self.step_uniqueness_analyzer = StepUniquenessAnalyzer()
        self.sequence_extractor = SequenceExtractor()
        self.dependency_analyzer = DependencyAnalyzer()
        self.role_classifier = RoleClassifier()
        self.website_grouper = WebsiteGrouper()
        self.min_coverage = min_coverage_percentage
        self.min_step_coverage = min_step_coverage_percentage
    
    def validate_optimization(
        self,
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Validate that optimization maintains required coverage.
        
        Args:
            original_test_cases: Original test cases before optimization
            optimized_test_cases: Optimized test cases after optimization
            
        Returns:
            Validation result dictionary
        """
        # Calculate coverage for both
        original_coverage = self.coverage_analyzer.calculate_flow_coverage(original_test_cases)
        optimized_coverage = self.coverage_analyzer.calculate_flow_coverage(optimized_test_cases)
        
        # Check critical flows
        original_critical = self.coverage_analyzer.identify_critical_flow_coverage(original_test_cases)
        optimized_critical = self.coverage_analyzer.identify_critical_flow_coverage(optimized_test_cases)
        
        # Validate coverage percentage
        coverage_maintained = optimized_coverage["coverage_percentage"] >= (self.min_coverage * 100)
        
        all_critical_covered = optimized_critical["all_critical_covered"]
        
        # Find lost flows
        original_flows = set(original_coverage["all_flows"])
        optimized_flows = set(optimized_coverage["all_flows"])
        lost_flows = original_flows - optimized_flows
        
        # Find lost critical flows
        lost_critical_flows = []
        for flow, coverage_info in original_critical["coverage"].items():
            if coverage_info["covered"] and not optimized_critical["coverage"][flow]["covered"]:
                lost_critical_flows.append(flow)
        
        # Validate each critical flow
        critical_flow_validation = {}
        for flow in ["authentication", "navigation", "crud"]:
            original_covered = original_critical["coverage"].get(flow, {}).get("covered", False)
            optimized_covered = optimized_critical["coverage"].get(flow, {}).get("covered", False)
            
            critical_flow_validation[flow] = {
                "original_covered": original_covered,
                "optimized_covered": optimized_covered,
                "maintained": optimized_covered or not original_covered  # OK if wasn't covered originally
            }
        
        # Overall validation
        is_valid = (
            coverage_maintained and
            all_critical_covered and
            len(lost_critical_flows) == 0
        )
        
        return {
            "is_valid": is_valid,
            "coverage_maintained": coverage_maintained,
            "all_critical_covered": all_critical_covered,
            "coverage_comparison": {
                "original": {
                    "total_flows": original_coverage["total_unique_flows"],
                    "covered_flows": original_coverage["covered_flows"],
                    "coverage_percentage": original_coverage["coverage_percentage"]
                },
                "optimized": {
                    "total_flows": optimized_coverage["total_unique_flows"],
                    "covered_flows": optimized_coverage["covered_flows"],
                    "coverage_percentage": optimized_coverage["coverage_percentage"]
                },
                "coverage_delta": optimized_coverage["coverage_percentage"] - original_coverage["coverage_percentage"]
            },
            "critical_flow_validation": critical_flow_validation,
            "lost_flows": list(lost_flows),
            "lost_critical_flows": lost_critical_flows,
            "warnings": self._generate_warnings(
                coverage_maintained,
                all_critical_covered,
                lost_flows,
                lost_critical_flows
            )
        }
    
    def _generate_warnings(
        self,
        coverage_maintained: bool,
        all_critical_covered: bool,
        lost_flows: List[str],
        lost_critical_flows: List[str]
    ) -> List[str]:
        """Generate warning messages."""
        warnings = []
        
        if not coverage_maintained:
            warnings.append("Coverage percentage dropped below minimum threshold")
        
        if not all_critical_covered:
            warnings.append("Some critical flows are no longer covered")
        
        if lost_critical_flows:
            warnings.append(f"Lost critical flows: {', '.join(lost_critical_flows)}")
        
        if lost_flows:
            warnings.append(f"Lost flows: {', '.join(lost_flows)}")
        
        return warnings
    
    def validate_test_case_removal(
        self,
        test_cases: Dict[int, TestCase],
        test_case_id: int
    ) -> Dict:
        """
        Validate if a specific test case can be safely removed.
        
        Args:
            test_cases: All test cases
            test_case_id: Test case ID to check for removal
            
        Returns:
            Validation result for this specific removal
        """
        if test_case_id not in test_cases:
            return {
                "can_remove": False,
                "reason": "Test case not found"
            }
        
        # Calculate coverage without this test case
        test_cases_without = {tid: tc for tid, tc in test_cases.items() if tid != test_case_id}
        
        original_coverage = self.coverage_analyzer.calculate_flow_coverage(test_cases)
        new_coverage = self.coverage_analyzer.calculate_flow_coverage(test_cases_without)
        
        # Check critical flows
        original_critical = self.coverage_analyzer.identify_critical_flow_coverage(test_cases)
        new_critical = self.coverage_analyzer.identify_critical_flow_coverage(test_cases_without)
        
        # Check if coverage is maintained
        coverage_maintained = new_coverage["coverage_percentage"] >= (self.min_coverage * 100)
        all_critical_covered = new_critical["all_critical_covered"]
        
        # Check what flows this test case covers
        test_case = test_cases[test_case_id]
        flows_covered = self.flow_analyzer.identify_flow_type(test_case)
        
        # Check if any critical flows would be lost
        critical_flows_lost = []
        for flow in flows_covered:
            if flow in ["authentication", "navigation", "crud"]:
                original_covered = original_critical["coverage"].get(flow, {}).get("covered", False)
                new_covered = new_critical["coverage"].get(flow, {}).get("covered", False)
                if original_covered and not new_covered:
                    critical_flows_lost.append(flow)
        
        can_remove = coverage_maintained and all_critical_covered and len(critical_flows_lost) == 0
        
        return {
            "can_remove": can_remove,
            "coverage_maintained": coverage_maintained,
            "all_critical_covered": all_critical_covered,
            "critical_flows_lost": critical_flows_lost,
            "flows_covered_by_test_case": flows_covered,
            "coverage_impact": {
                "before": original_coverage["coverage_percentage"],
                "after": new_coverage["coverage_percentage"],
                "delta": new_coverage["coverage_percentage"] - original_coverage["coverage_percentage"]
            },
            "reason": "Can be safely removed" if can_remove else "Removal would impact coverage"
        }
    
    def validate_step_coverage(
        self,
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Validate step-level coverage.
        
        Args:
            original_test_cases: Original test cases
            optimized_test_cases: Optimized test cases
            
        Returns:
            Step coverage validation result
        """
        # Build coverage maps
        original_map = self.step_coverage_tracker.build_step_coverage_map(original_test_cases)
        optimized_map = self.step_coverage_tracker.build_step_coverage_map(optimized_test_cases)
        
        # Find lost steps
        original_steps = set(original_map.keys())
        optimized_steps = set(optimized_map.keys())
        lost_steps = original_steps - optimized_steps
        
        # Calculate coverage
        original_count = len(original_steps)
        optimized_count = len(optimized_steps)
        coverage_percentage = (optimized_count / original_count * 100) if original_count > 0 else 0.0
        
        # Check threshold
        threshold = self.min_step_coverage * 100
        passed = coverage_percentage >= threshold
        
        # Get details of lost steps
        lost_step_details = []
        for step_sig in lost_steps:
            covering_test_cases = original_map.get(step_sig, [])
            lost_step_details.append({
                "step_signature": step_sig,
                "was_covered_by": covering_test_cases
            })
        
        return {
            "original_steps": original_count,
            "optimized_steps": optimized_count,
            "lost_steps_count": len(lost_steps),
            "coverage_percentage": coverage_percentage,
            "threshold": threshold,
            "passed": passed,
            "lost_steps": lost_step_details
        }
    
    def validate_element_coverage(
        self,
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Validate element-level coverage.
        
        Args:
            original_test_cases: Original test cases
            optimized_test_cases: Optimized test cases
            
        Returns:
            Element coverage validation result
        """
        # Extract all elements from original
        original_elements = set()
        for test_case in original_test_cases.values():
            for step in test_case.steps:
                if step.element:
                    original_elements.add(step.element.lower().strip())
                if step.locator:
                    if isinstance(step.locator, dict):
                        for key in ["label", "id", "name", "placeholder", "xpath", "selector"]:
                            if key in step.locator:
                                original_elements.add(str(step.locator[key]).lower().strip())
        
        optimized_elements = set()
        for test_case in optimized_test_cases.values():
            for step in test_case.steps:
                if step.element:
                    optimized_elements.add(step.element.lower().strip())
                if step.locator:
                    if isinstance(step.locator, dict):
                        for key in ["label", "id", "name", "placeholder", "xpath", "selector"]:
                            if key in step.locator:
                                optimized_elements.add(str(step.locator[key]).lower().strip())
        
        lost_elements = original_elements - optimized_elements
        
        original_count = len(original_elements)
        optimized_count = len(optimized_elements)
        coverage_percentage = (optimized_count / original_count * 100) if original_count > 0 else 0.0
        
        
        threshold = 90.0  
        passed = coverage_percentage >= threshold
        
        return {
            "original_elements": original_count,
            "optimized_elements": optimized_count,
            "lost_elements_count": len(lost_elements),
            "lost_elements": list(lost_elements),
            "coverage_percentage": coverage_percentage,
            "threshold": threshold,
            "passed": passed
        }
    
    def validate_scenario_coverage(
        self,
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Validate scenario-level coverage (happy path, error cases, edge cases).
        
        Args:
            original_test_cases: Original test cases
            optimized_test_cases: Optimized test cases
            
        Returns:
            Scenario coverage validation result
        """
        # Identify scenarios from test case names and descriptions
        original_scenarios = set()
        for test_case in original_test_cases.values():
            text = f"{test_case.name} {test_case.description or ''}".lower()
            
            if any(keyword in text for keyword in ["error", "fail", "invalid", "exception"]):
                original_scenarios.add("error_scenario")
            if any(keyword in text for keyword in ["edge", "boundary", "limit", "extreme"]):
                original_scenarios.add("edge_case")
            if any(keyword in text for keyword in ["happy", "success", "valid", "normal"]):
                original_scenarios.add("happy_path")
            if any(keyword in text for keyword in ["alternative", "different", "other"]):
                original_scenarios.add("alternative_flow")
            
            if not original_scenarios:
                original_scenarios.add("happy_path")
        
        optimized_scenarios = set()
        for test_case in optimized_test_cases.values():
            text = f"{test_case.name} {test_case.description or ''}".lower()
            
            if any(keyword in text for keyword in ["error", "fail", "invalid", "exception"]):
                optimized_scenarios.add("error_scenario")
            if any(keyword in text for keyword in ["edge", "boundary", "limit", "extreme"]):
                optimized_scenarios.add("edge_case")
            if any(keyword in text for keyword in ["happy", "success", "valid", "normal"]):
                optimized_scenarios.add("happy_path")
            if any(keyword in text for keyword in ["alternative", "different", "other"]):
                optimized_scenarios.add("alternative_flow")
            
            if not optimized_scenarios:
                optimized_scenarios.add("happy_path")
        
        lost_scenarios = original_scenarios - optimized_scenarios
        
        critical_scenarios = {"happy_path", "error_scenario"}
        lost_critical = critical_scenarios.intersection(lost_scenarios)
        
        passed = len(lost_critical) == 0
        
        return {
            "original_scenarios": list(original_scenarios),
            "optimized_scenarios": list(optimized_scenarios),
            "lost_scenarios": list(lost_scenarios),
            "lost_critical_scenarios": list(lost_critical),
            "passed": passed
        }
    
    def validate_data_coverage(
        self,
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Validate test data coverage.
        
        Args:
            original_test_cases: Original test cases
            optimized_test_cases: Optimized test cases
            
        Returns:
            Data coverage validation result
        """
        # Extract test data IDs
        original_data_ids = set()
        for test_case in original_test_cases.values():
            if test_case.test_data_id:
                original_data_ids.add(test_case.test_data_id)
        
        optimized_data_ids = set()
        for test_case in optimized_test_cases.values():
            if test_case.test_data_id:
                optimized_data_ids.add(test_case.test_data_id)
        
        original_step_data = set()
        for test_case in original_test_cases.values():
            for step in test_case.steps:
                if step.test_data:
                    original_step_data.add(str(step.test_data).lower().strip())
        
        optimized_step_data = set()
        for test_case in optimized_test_cases.values():
            for step in test_case.steps:
                if step.test_data:
                    optimized_step_data.add(str(step.test_data).lower().strip())
        
        lost_data_ids = original_data_ids - optimized_data_ids
        lost_step_data = original_step_data - optimized_step_data
        
        data_id_coverage = (len(optimized_data_ids) / len(original_data_ids) * 100) if original_data_ids else 100.0
        step_data_coverage = (len(optimized_step_data) / len(original_step_data) * 100) if original_step_data else 100.0
        
        data_id_threshold = 90.0
        step_data_threshold = 90.0
        passed = data_id_coverage >= data_id_threshold and step_data_coverage >= step_data_threshold
        
        return {
            "original_data_ids": len(original_data_ids),
            "optimized_data_ids": len(optimized_data_ids),
            "lost_data_ids": list(lost_data_ids),
            "original_step_data": len(original_step_data),
            "optimized_step_data": len(optimized_step_data),
            "lost_step_data": list(lost_step_data),
            "data_id_coverage_percentage": data_id_coverage,
            "step_data_coverage_percentage": step_data_coverage,
            "data_id_threshold": data_id_threshold,
            "step_data_threshold": step_data_threshold,
            "passed": passed
        }
    
    def validate_step_sequence_preservation(
        self,
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Validate that critical step sequences are preserved.
        
        Checks if critical sequences like Login → Action → Logout are maintained
        in the correct order.
        
        Args:
            original_test_cases: Original test cases
            optimized_test_cases: Optimized test cases
            
        Returns:
            Sequence validation result
        """
        # Define critical sequences that must be preserved
        critical_sequences = [
            ["navigateto", "click", "enter", "click"], 
            ["navigateto", "click", "enter", "click", "verify"],
            ["click", "enter", "click"], 
            ["click", "enter", "click", "verify"],
        ]
        
        original_sequences = {}
        for test_id, test_case in original_test_cases.items():
            sequence = self.sequence_extractor.extract_action_sequence(test_case)
            original_sequences[test_id] = sequence
        
        optimized_sequences = {}
        for test_id, test_case in optimized_test_cases.items():
            sequence = self.sequence_extractor.extract_action_sequence(test_case)
            optimized_sequences[test_id] = sequence
        
        broken_sequences = []
        lost_sequences = []
        
        # Check each original sequence
        for test_id, original_seq in original_sequences.items():
            matches_critical = False
            for critical_seq in critical_sequences:
                if self._sequence_contains_pattern(original_seq, critical_seq):
                    matches_critical = True
                    break
            
            if matches_critical:
                preserved = False
                for opt_id, opt_seq in optimized_sequences.items():
                    if self._sequence_contains_pattern(opt_seq, critical_seq):
                        if self._check_sequence_order(original_seq, opt_seq, critical_seq):
                            preserved = True
                            break
                
                if not preserved:
                    # Check if sequence exists but order is broken
                    sequence_exists = False
                    for opt_seq in optimized_sequences.values():
                        if self._sequence_contains_pattern(opt_seq, critical_seq):
                            sequence_exists = True
                            break
                    
                    if sequence_exists:
                        broken_sequences.append({
                            "test_case_id": test_id,
                            "original_sequence": "->".join(original_seq[:10]),  
                            "issue": "Sequence order broken"
                        })
                    else:
                        lost_sequences.append({
                            "test_case_id": test_id,
                            "original_sequence": "->".join(original_seq[:10]),
                            "issue": "Sequence completely lost"
                        })
        
        passed = len(broken_sequences) == 0 and len(lost_sequences) == 0
        
        return {
            "passed": passed,
            "broken_sequences": broken_sequences,
            "lost_sequences": lost_sequences,
            "total_issues": len(broken_sequences) + len(lost_sequences)
        }
    
    def _sequence_contains_pattern(self, sequence: List[str], pattern: List[str]) -> bool:
        """Check if sequence contains pattern in order."""
        if len(pattern) == 0:
            return True
        if len(sequence) < len(pattern):
            return False
        
        # Use sliding window to find pattern
        for i in range(len(sequence) - len(pattern) + 1):
            if sequence[i:i+len(pattern)] == pattern:
                return True
        return False
    
    def _check_sequence_order(self, original_seq: List[str], optimized_seq: List[str], pattern: List[str]) -> bool:
        """Check if pattern order is maintained between original and optimized."""
        # Find pattern positions in both sequences
        orig_positions = self._find_pattern_positions(original_seq, pattern)
        opt_positions = self._find_pattern_positions(optimized_seq, pattern)
        
        if not orig_positions or not opt_positions:
            return False
        
        
        return True
    
    def _find_pattern_positions(self, sequence: List[str], pattern: List[str]) -> List[int]:
        """Find all positions where pattern occurs in sequence."""
        positions = []
        for i in range(len(sequence) - len(pattern) + 1):
            if sequence[i:i+len(pattern)] == pattern:
                positions.append(i)
        return positions
    
    def validate_state_dependencies(
        self,
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Validate that prerequisite chains are maintained.
        
        Checks if test cases that depend on others still have their dependencies
        available after optimization.
        
        Args:
            original_test_cases: Original test cases
            optimized_test_cases: Optimized test cases
            
        Returns:
            State dependency validation result
        """
        # Analyze dependencies in original
        original_deps = self.dependency_analyzer.analyze_dependencies(original_test_cases)
        
        # Analyze dependencies in optimized
        optimized_deps = self.dependency_analyzer.analyze_dependencies(optimized_test_cases)
        
        # Find broken dependencies
        broken_dependencies = []
        
        # Check each test case in optimized
        for test_id, test_case in optimized_test_cases.items():
            # Get dependencies for this test case
            deps = optimized_deps["dependencies"].get(test_id, [])
            
            # Check if all dependencies are still present
            for dep_id in deps:
                if dep_id not in optimized_test_cases:
                    # Dependency was removed/merged
                    broken_dependencies.append({
                        "test_case_id": test_id,
                        "missing_dependency": dep_id,
                        "issue": f"TC{test_id} depends on TC{dep_id} which was removed/merged"
                    })
        
        implicit_broken = self._check_implicit_dependencies(
            original_test_cases,
            optimized_test_cases
        )
        broken_dependencies.extend(implicit_broken)
        
        passed = len(broken_dependencies) == 0
        
        return {
            "passed": passed,
            "broken_dependencies": broken_dependencies,
            "total_issues": len(broken_dependencies)
        }
    
    def _check_implicit_dependencies(
        self,
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase]
    ) -> List[Dict]:
        """Check for implicit dependencies (e.g., create user vs use user)."""
        broken = []
      
        creators = {}
        users = {}
        
        for test_id, test_case in original_test_cases.items():
            name_lower = test_case.name.lower()
            desc_lower = (test_case.description or "").lower()
            text = f"{name_lower} {desc_lower}"
            
            if any(keyword in text for keyword in ["create", "add", "new", "register"]):
                entity = self._extract_entity(text)
                if entity:
                    if entity not in creators:
                        creators[entity] = []
                    creators[entity].append(test_id)
            
            if any(keyword in text for keyword in ["use", "with", "login as", "as user"]):
                entity = self._extract_entity(text)
                if entity:
                    if entity not in users:
                        users[entity] = []
                    users[entity].append(test_id)
        
        for entity, creator_ids in creators.items():
            # Check if any creator is still in optimized
            creator_exists = any(cid in optimized_test_cases for cid in creator_ids)
            
            if not creator_exists and entity in users:
                user_ids = users[entity]
                for user_id in user_ids:
                    if user_id in optimized_test_cases:
                        broken.append({
                            "test_case_id": user_id,
                            "missing_dependency": creator_ids[0],
                            "issue": f"TC{user_id} uses {entity} but creator TC{creator_ids[0]} was removed"
                        })
        
        return broken
    
    def _extract_entity(self, text: str) -> str:
        """Extract entity name from text (e.g., 'user', 'employee', 'account')."""
        entities = ["user", "employee", "account", "customer", "admin", "data"]
        for entity in entities:
            if entity in text:
                return entity
        return None
    
    def validate_flow_transitions(
        self,
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Validate that page/flow transitions are preserved.
        
        Checks if transitions like Login → Dashboard → Settings are maintained.
        
        Args:
            original_test_cases: Original test cases
            optimized_test_cases: Optimized test cases
            
        Returns:
            Flow transition validation result
        """
        original_transitions = set()
        for test_case in original_test_cases.values():
            transitions = self.flow_analyzer.extract_page_transitions(test_case)
            for trans in transitions:
                sig = f"{trans['from']}->{trans['to']}"
                original_transitions.add(sig)
        
        optimized_transitions = set()
        for test_case in optimized_test_cases.values():
            transitions = self.flow_analyzer.extract_page_transitions(test_case)
            for trans in transitions:
                sig = f"{trans['from']}->{trans['to']}"
                optimized_transitions.add(sig)
        
        lost_transitions = original_transitions - optimized_transitions
        
        broken_chains = []
        
        # Check if critical transition chains are broken
        for test_case in original_test_cases.values():
            transitions = self.flow_analyzer.extract_page_transitions(test_case)
            if len(transitions) >= 2:
                chain_preserved = False
                for opt_tc in optimized_test_cases.values():
                    opt_transitions = self.flow_analyzer.extract_page_transitions(opt_tc)
                    if len(opt_transitions) >= len(transitions):
                        opt_sigs = {f"{t['from']}->{t['to']}" for t in opt_transitions}
                        orig_sigs = {f"{t['from']}->{t['to']}" for t in transitions}
                        if orig_sigs.issubset(opt_sigs):
                            chain_preserved = True
                            break
                
                if not chain_preserved:
                    broken_chains.append({
                        "test_case_id": test_case.id,
                        "transitions": [f"{t['from']}->{t['to']}" for t in transitions],
                        "issue": "Transition chain broken or incomplete"
                    })
        
        passed = len(lost_transitions) == 0 and len(broken_chains) == 0
        
        return {
            "passed": passed,
            "lost_transitions": list(lost_transitions),
            "broken_chains": broken_chains,
            "total_issues": len(lost_transitions) + len(broken_chains)
        }
    
    def validate_data_combinations(
        self,
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Validate that test data combinations are preserved.
        
        Checks if specific data value combinations (e.g., "valid email + invalid password")
        are maintained.
        
        Args:
            original_test_cases: Original test cases
            optimized_test_cases: Optimized test cases
            
        Returns:
            Data combination validation result
        """
        # Extract data combinations from original
        original_combinations = set()
        for test_case in original_test_cases.values():
            # Get all test data values from steps
            data_values = []
            for step in sorted(test_case.steps, key=lambda s: s.position):
                if step.test_data:
                    data_values.append(step.test_data.lower().strip())
            
            # Create combination signature
            if len(data_values) >= 2:
                combo_sig = "|".join(sorted(data_values[:5]))  
                original_combinations.add(combo_sig)
            elif len(data_values) == 1:
                value = data_values[0]
                if any(keyword in value for keyword in ["invalid", "error", "empty", "null", "expired", "wrong"]):
                    original_combinations.add(f"edge_case:{value}")
        
        # Extract data combinations from optimized
        optimized_combinations = set()
        for test_case in optimized_test_cases.values():
            data_values = []
            for step in sorted(test_case.steps, key=lambda s: s.position):
                if step.test_data:
                    data_values.append(step.test_data.lower().strip())
            
            if len(data_values) >= 2:
                combo_sig = "|".join(sorted(data_values[:5]))
                optimized_combinations.add(combo_sig)
            elif len(data_values) == 1:
                value = data_values[0]
                if any(keyword in value for keyword in ["invalid", "error", "empty", "null", "expired", "wrong"]):
                    optimized_combinations.add(f"edge_case:{value}")
        
        # Find lost combinations
        lost_combinations = original_combinations - optimized_combinations
        
        # Check for edge case data loss
        edge_cases_lost = [c for c in lost_combinations if c.startswith("edge_case:")]
        
        passed = len(edge_cases_lost) == 0 
        
        return {
            "passed": passed,
            "lost_combinations": list(lost_combinations),
            "edge_cases_lost": edge_cases_lost,
            "total_issues": len(lost_combinations)
        }
    
    def validate_scenario_context(
        self,
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Validate that scenario contexts are preserved.
        
        Checks if actual error conditions (not just keywords) are maintained.
        
        Args:
            original_test_cases: Original test cases
            optimized_test_cases: Optimized test cases
            
        Returns:
            Scenario context validation result
        """
        # Extract error conditions from original
        original_error_conditions = set()
        for test_case in original_test_cases.values():
            # Check steps for error conditions
            for step in test_case.steps:
                step_text = f"{step.action} {step.description or ''} {step.test_data or ''}".lower()
                
                # Extract specific error conditions
                if "expired" in step_text:
                    original_error_conditions.add("expired_session")
                if "invalid password" in step_text or "wrong password" in step_text:
                    original_error_conditions.add("invalid_password")
                if "empty" in step_text and ("password" in step_text or "field" in step_text):
                    original_error_conditions.add("empty_field")
                if "null" in step_text or "none" in step_text:
                    original_error_conditions.add("null_value")
                if "timeout" in step_text:
                    original_error_conditions.add("timeout")
                if "unauthorized" in step_text or "403" in step_text:
                    original_error_conditions.add("unauthorized")
        
        # Extract error conditions from optimized
        optimized_error_conditions = set()
        for test_case in optimized_test_cases.values():
            for step in test_case.steps:
                step_text = f"{step.action} {step.description or ''} {step.test_data or ''}".lower()
                
                if "expired" in step_text:
                    optimized_error_conditions.add("expired_session")
                if "invalid password" in step_text or "wrong password" in step_text:
                    optimized_error_conditions.add("invalid_password")
                if "empty" in step_text and ("password" in step_text or "field" in step_text):
                    optimized_error_conditions.add("empty_field")
                if "null" in step_text or "none" in step_text:
                    optimized_error_conditions.add("null_value")
                if "timeout" in step_text:
                    optimized_error_conditions.add("timeout")
                if "unauthorized" in step_text or "403" in step_text:
                    optimized_error_conditions.add("unauthorized")
        
        lost_error_conditions = original_error_conditions - optimized_error_conditions
        
        critical_errors = {"invalid_password", "expired_session", "unauthorized"}
        lost_critical = critical_errors.intersection(lost_error_conditions)
        
        passed = len(lost_critical) == 0
        
        return {
            "passed": passed,
            "lost_error_conditions": list(lost_error_conditions),
            "lost_critical_errors": list(lost_critical),
            "total_issues": len(lost_error_conditions)
        }
    
    def validate_role_consistency(
        self,
        merged_test_case: TestCase,
        source_test_cases: List[TestCase]
    ) -> Dict:
        """
        Validate that all source test cases have the same role.
        
        Args:
            merged_test_case: The merged test case
            source_test_cases: List of source test cases that were merged
            
        Returns:
            Role consistency validation result
        """
        if not source_test_cases:
            return {
                "passed": True,
                "issue": None
            }
        
        # Classify roles for all source test cases
        roles = []
        for tc in source_test_cases:
            role = self.role_classifier.classify_role(tc)
            roles.append(role)
        
        # Check if all roles are the same
        unique_roles = set(roles)
        
        if len(unique_roles) > 1:
            role_counts = {role: roles.count(role) for role in unique_roles}
            return {
                "passed": False,
                "issue": f"Mixed roles detected: {role_counts}. Cannot merge admin and user test cases.",
                "roles": list(unique_roles),
                "role_counts": role_counts
            }
        
        if "unknown" in unique_roles:
            return {
                "passed": True,
                "issue": "Some test cases have unknown role classification",
                "roles": list(unique_roles)
            }
        
        return {
            "passed": True,
            "issue": None,
            "role": list(unique_roles)[0]
        }
    
    def validate_website_consistency(
        self,
        merged_test_case: TestCase,
        source_test_cases: List[TestCase]
    ) -> Dict:
        """
        Validate that all source test cases have the same website/domain.
        
        Args:
            merged_test_case: The merged test case
            source_test_cases: List of source test cases that were merged
            
        Returns:
            Website consistency validation result
        """
        if not source_test_cases:
            return {
                "passed": True,
                "issue": None
            }
        
        # Extract websites for all source test cases
        websites = []
        for tc in source_test_cases:
            website = self.website_grouper.extract_website(tc)
            websites.append(website)
        
        # Check if all websites are the same
        unique_websites = set(websites)
        
        if len(unique_websites) > 1:
            # Different websites detected
            website_counts = {website: websites.count(website) for website in unique_websites}
            return {
                "passed": False,
                "issue": f"Mixed websites detected: {website_counts}. Cannot merge test cases from different websites.",
                "websites": list(unique_websites),
                "website_counts": website_counts
            }
        
        if "unknown" in unique_websites:
            return {
                "passed": True,
                "issue": "Some test cases have unknown website classification",
                "websites": list(unique_websites)
            }
        
        return {
            "passed": True,
            "issue": None,
            "website": list(unique_websites)[0]
        }
    
    def validate_merge_safety(
        self,
        test_cases: List[TestCase]
    ) -> Dict:
        """
        Validate that test cases can be safely merged.
        
        Checks:
        - Same role (admin vs user)
        - Same website/domain
        - No conflicting state dependencies
        - No circular dependencies
        
        Args:
            test_cases: List of test cases to merge
            
        Returns:
            Merge safety validation result
        """
        if not test_cases:
            return {
                "passed": False,
                "issue": "Empty test case list"
            }
        
        if len(test_cases) == 1:
            return {
                "passed": True,
                "issue": None
            }
        
        issues = []
        
        # Check role consistency
        role_validation = self.validate_role_consistency(None, test_cases)
        if not role_validation["passed"]:
            issues.append(role_validation["issue"])
        
        # Check website consistency
        website_validation = self.validate_website_consistency(None, test_cases)
        if not website_validation["passed"]:
            issues.append(website_validation["issue"])
        
        
        prerequisite_ids = set()
        for tc in test_cases:
            if tc.prerequisite_case:
                prerequisite_ids.add(tc.prerequisite_case)
        
        test_case_ids = {tc.id for tc in test_cases}
        conflicting_deps = prerequisite_ids.intersection(test_case_ids)
        
        if conflicting_deps:
            issues.append(f"Conflicting dependencies: Test cases {conflicting_deps} are prerequisites of others in the merge group")
        
        passed = len(issues) == 0
        
        return {
            "passed": passed,
            "issues": issues,
            "role_validation": role_validation,
            "website_validation": website_validation,
            "conflicting_dependencies": list(conflicting_deps)
        }
    
    def comprehensive_validation(
        self,
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Run comprehensive validation (all levels).
        
        Args:
            original_test_cases: Original test cases
            optimized_test_cases: Optimized test cases
            
        Returns:
            Comprehensive validation result
        """
        # Run all validations
        step_validation = self.validate_step_coverage(original_test_cases, optimized_test_cases)
        flow_validation = self.validate_optimization(original_test_cases, optimized_test_cases)
        element_validation = self.validate_element_coverage(original_test_cases, optimized_test_cases)
        scenario_validation = self.validate_scenario_coverage(original_test_cases, optimized_test_cases)
        data_validation = self.validate_data_coverage(original_test_cases, optimized_test_cases)
        
        sequence_validation = self.validate_step_sequence_preservation(original_test_cases, optimized_test_cases)
        dependency_validation = self.validate_state_dependencies(original_test_cases, optimized_test_cases)
        transition_validation = self.validate_flow_transitions(original_test_cases, optimized_test_cases)
        data_combo_validation = self.validate_data_combinations(original_test_cases, optimized_test_cases)
        scenario_context_validation = self.validate_scenario_context(original_test_cases, optimized_test_cases)
        
        
        overall_valid = (
            step_validation["passed"] and
            flow_validation["is_valid"] and
            scenario_validation["passed"] and 
            sequence_validation["passed"] and 
            dependency_validation["passed"] and 
            transition_validation["passed"] and 
            scenario_context_validation["passed"] 
        )
        
        # Collect warnings and errors
        warnings = []
        errors = []
        
        if not step_validation["passed"]:
            errors.append(f"Step coverage dropped to {step_validation['coverage_percentage']:.1f}% (threshold: {step_validation['threshold']:.1f}%)")
        
        if not flow_validation["is_valid"]:
            errors.extend(flow_validation["warnings"])
        
        if not element_validation["passed"]:
            
            warnings.append(f"Element coverage: {element_validation['lost_elements_count']} elements lost (coverage: {element_validation['coverage_percentage']:.1f}%, threshold: {element_validation['threshold']:.1f}%)")
        
        if not scenario_validation["passed"]:
            errors.append(f"Lost critical scenarios: {', '.join(scenario_validation['lost_critical_scenarios'])}")
        
        if not data_validation["passed"]:
            warnings.append(f"Lost test data: {len(data_validation['lost_data_ids'])} data IDs, {len(data_validation['lost_step_data'])} step data values (step data coverage: {data_validation['step_data_coverage_percentage']:.1f}%, threshold: {data_validation.get('step_data_threshold', 90.0):.1f}%)")
        
        # Enhanced validation errors
        if not sequence_validation["passed"]:
            errors.append(f"Step sequence issues: {sequence_validation['total_issues']} broken/lost sequences")
            if sequence_validation['broken_sequences']:
                for broken in sequence_validation['broken_sequences'][:3]:  
                    errors.append(f"  - TC{broken['test_case_id']}: {broken['issue']}")
        
        if not dependency_validation["passed"]:
            errors.append(f"State dependency issues: {dependency_validation['total_issues']} broken dependencies")
            for broken in dependency_validation['broken_dependencies'][:3]:  
                errors.append(f"  - {broken['issue']}")
        
        if not transition_validation["passed"]:
            errors.append(f"Flow transition issues: {transition_validation['total_issues']} lost/broken transitions")
            if transition_validation['lost_transitions']:
                errors.append(f"  - Lost transitions: {len(transition_validation['lost_transitions'])}")
        
        if not data_combo_validation["passed"]:
            warnings.append(f"Data combination issues: {len(data_combo_validation['edge_cases_lost'])} edge case combinations lost")
        
        if not scenario_context_validation["passed"]:
            errors.append(f"Scenario context issues: {len(scenario_context_validation['lost_critical_errors'])} critical error conditions lost")
            for error_cond in scenario_context_validation['lost_critical_errors']:
                errors.append(f"  - Lost error condition: {error_cond}")
        
        return {
            "overall_valid": overall_valid,
            "step_coverage": step_validation,
            "flow_coverage": {
                "original": flow_validation["coverage_comparison"]["original"],
                "optimized": flow_validation["coverage_comparison"]["optimized"],
                "coverage_delta": flow_validation["coverage_comparison"]["coverage_delta"],
                "passed": flow_validation["is_valid"]
            },
            "element_coverage": element_validation,
            "scenario_coverage": scenario_validation,
            "data_coverage": data_validation,
            "sequence_validation": sequence_validation,
            "dependency_validation": dependency_validation,
            "transition_validation": transition_validation,
            "data_combination_validation": data_combo_validation,
            "scenario_context_validation": scenario_context_validation,
            "warnings": warnings,
            "errors": errors
        }
    
    def generate_validation_report(
        self,
        validation_result: Dict
    ) -> str:
        """
        Generate human-readable validation report.
        
        Args:
            validation_result: Result from comprehensive_validation
            
        Returns:
            Human-readable report string
        """
        report = []
        report.append("=" * 80)
        report.append("COMPREHENSIVE COVERAGE VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Overall status
        status = "✓ PASSED" if validation_result["overall_valid"] else "✗ FAILED"
        report.append(f"Overall Validation: {status}")
        report.append("")
        
        # Step coverage
        step_cov = validation_result["step_coverage"]
        report.append(f"Step Coverage:")
        report.append(f"  Original Steps: {step_cov['original_steps']}")
        report.append(f"  Optimized Steps: {step_cov['optimized_steps']}")
        report.append(f"  Coverage: {step_cov['coverage_percentage']:.1f}% (Threshold: {step_cov['threshold']:.1f}%)")
        report.append(f"  Status: {'✓ PASSED' if step_cov['passed'] else '✗ FAILED'}")
        if step_cov['lost_steps_count'] > 0:
            report.append(f"  ⚠ Lost Steps: {step_cov['lost_steps_count']}")
        report.append("")
        
        # Flow coverage
        flow_cov = validation_result["flow_coverage"]
        report.append(f"Flow Coverage:")
        report.append(f"  Original: {flow_cov['original']['coverage_percentage']:.1f}%")
        report.append(f"  Optimized: {flow_cov['optimized']['coverage_percentage']:.1f}%")
        report.append(f"  Delta: {flow_cov['coverage_delta']:+.1f}%")
        report.append(f"  Status: {'✓ PASSED' if flow_cov['passed'] else '✗ FAILED'}")
        report.append("")
        
        # Element coverage
        elem_cov = validation_result["element_coverage"]
        report.append(f"Element Coverage:")
        report.append(f"  Original Elements: {elem_cov['original_elements']}")
        report.append(f"  Optimized Elements: {elem_cov['optimized_elements']}")
        report.append(f"  Coverage: {elem_cov['coverage_percentage']:.1f}%")
        report.append(f"  Status: {'✓ PASSED' if elem_cov['passed'] else '✗ FAILED'}")
        if elem_cov['lost_elements_count'] > 0:
            report.append(f"  ⚠ Lost Elements: {elem_cov['lost_elements_count']}")
        report.append("")
        
        # Scenario coverage
        scen_cov = validation_result["scenario_coverage"]
        report.append(f"Scenario Coverage:")
        report.append(f"  Original Scenarios: {len(scen_cov['original_scenarios'])}")
        report.append(f"  Optimized Scenarios: {len(scen_cov['optimized_scenarios'])}")
        report.append(f"  Status: {'✓ PASSED' if scen_cov['passed'] else '✗ FAILED'}")
        if scen_cov['lost_critical_scenarios']:
            report.append(f"  ✗ Lost Critical Scenarios: {', '.join(scen_cov['lost_critical_scenarios'])}")
        report.append("")
        
        # Data coverage
        data_cov = validation_result["data_coverage"]
        report.append(f"Data Coverage:")
        report.append(f"  Data ID Coverage: {data_cov['data_id_coverage_percentage']:.1f}%")
        report.append(f"  Step Data Coverage: {data_cov['step_data_coverage_percentage']:.1f}%")
        report.append(f"  Status: {'✓ PASSED' if data_cov['passed'] else '✗ FAILED'}")
        report.append("")
        
        report.append("=" * 80)
        report.append("ENHANCED VALIDATION CHECKS")
        report.append("=" * 80)
        report.append("")
        
        # Step sequence validation
        seq_val = validation_result.get("sequence_validation", {})
        if seq_val:
            report.append(f"Step Sequence Preservation:")
            report.append(f"  Status: {'✓ PASSED' if seq_val.get('passed', True) else '✗ FAILED'}")
            if not seq_val.get('passed', True):
                report.append(f"  Broken Sequences: {len(seq_val.get('broken_sequences', []))}")
                report.append(f"  Lost Sequences: {len(seq_val.get('lost_sequences', []))}")
            report.append("")
        
        # State dependency validation
        dep_val = validation_result.get("dependency_validation", {})
        if dep_val:
            report.append(f"State Dependencies:")
            report.append(f"  Status: {'✓ PASSED' if dep_val.get('passed', True) else '✗ FAILED'}")
            if not dep_val.get('passed', True):
                report.append(f"  Broken Dependencies: {dep_val.get('total_issues', 0)}")
            report.append("")
        
        # Flow transition validation
        trans_val = validation_result.get("transition_validation", {})
        if trans_val:
            report.append(f"Flow Transitions:")
            report.append(f"  Status: {'✓ PASSED' if trans_val.get('passed', True) else '✗ FAILED'}")
            if not trans_val.get('passed', True):
                report.append(f"  Lost Transitions: {len(trans_val.get('lost_transitions', []))}")
                report.append(f"  Broken Chains: {len(trans_val.get('broken_chains', []))}")
            report.append("")
        
        # Data combination validation
        data_combo = validation_result.get("data_combination_validation", {})
        if data_combo:
            report.append(f"Data Combinations:")
            report.append(f"  Status: {'✓ PASSED' if data_combo.get('passed', True) else '✗ FAILED'}")
            if not data_combo.get('passed', True):
                report.append(f"  Lost Combinations: {len(data_combo.get('lost_combinations', []))}")
                report.append(f"  Edge Cases Lost: {len(data_combo.get('edge_cases_lost', []))}")
            report.append("")
        
        # Scenario context validation
        scen_ctx = validation_result.get("scenario_context_validation", {})
        if scen_ctx:
            report.append(f"Scenario Context:")
            report.append(f"  Status: {'✓ PASSED' if scen_ctx.get('passed', True) else '✗ FAILED'}")
            if not scen_ctx.get('passed', True):
                report.append(f"  Lost Error Conditions: {len(scen_ctx.get('lost_error_conditions', []))}")
                report.append(f"  Critical Errors Lost: {len(scen_ctx.get('lost_critical_errors', []))}")
            report.append("")
        
        report.append("=" * 80)
        report.append("")
        
        # Warnings and errors
        if validation_result["warnings"]:
            report.append("Warnings:")
            for warning in validation_result["warnings"]:
                report.append(f"  ⚠ {warning}")
            report.append("")
        
        if validation_result["errors"]:
            report.append("Errors:")
            for error in validation_result["errors"]:
                report.append(f"  ✗ {error}")
            report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)

