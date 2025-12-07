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
        
        # Check if all critical flows are still covered
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
                    # Extract from locator
                    if isinstance(step.locator, dict):
                        for key in ["label", "id", "name", "placeholder", "xpath", "selector"]:
                            if key in step.locator:
                                original_elements.add(str(step.locator[key]).lower().strip())
        
        # Extract all elements from optimized
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
        
        # Find lost elements
        lost_elements = original_elements - optimized_elements
        
        # Calculate coverage
        original_count = len(original_elements)
        optimized_count = len(optimized_elements)
        coverage_percentage = (optimized_count / original_count * 100) if original_count > 0 else 0.0
        
        # Element coverage threshold: 90% (more lenient than step coverage)
        # Elements can be lost when removing duplicates - this is acceptable
        threshold = 90.0  # 90% element coverage (lower threshold for less critical metric)
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
            # Extract scenario type from name/description
            text = f"{test_case.name} {test_case.description or ''}".lower()
            
            if any(keyword in text for keyword in ["error", "fail", "invalid", "exception"]):
                original_scenarios.add("error_scenario")
            if any(keyword in text for keyword in ["edge", "boundary", "limit", "extreme"]):
                original_scenarios.add("edge_case")
            if any(keyword in text for keyword in ["happy", "success", "valid", "normal"]):
                original_scenarios.add("happy_path")
            if any(keyword in text for keyword in ["alternative", "different", "other"]):
                original_scenarios.add("alternative_flow")
            
            # Default to happy path if no keywords
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
        
        # Find lost scenarios
        lost_scenarios = original_scenarios - optimized_scenarios
        
        # Critical scenarios must be covered
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
        
        # Extract test data from steps
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
        
        # Find lost data
        lost_data_ids = original_data_ids - optimized_data_ids
        lost_step_data = original_step_data - optimized_step_data
        
        # Calculate coverage
        data_id_coverage = (len(optimized_data_ids) / len(original_data_ids) * 100) if original_data_ids else 100.0
        step_data_coverage = (len(optimized_step_data) / len(original_step_data) * 100) if original_step_data else 100.0
        
        # Data coverage threshold: 90% (more lenient than step coverage)
        # Test data can be lost when removing duplicates - this is acceptable
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
        
        # Overall validation - CRITICAL metrics only
        # Step coverage and flow coverage are CRITICAL (must pass)
        # Element and data coverage are less critical (warnings only, don't block overall)
        overall_valid = (
            step_validation["passed"] and
            flow_validation["is_valid"] and
            scenario_validation["passed"]  # Critical scenarios must be maintained
            # Note: element_validation and data_validation are warnings, not blockers
        )
        
        # Collect warnings and errors
        warnings = []
        errors = []
        
        if not step_validation["passed"]:
            errors.append(f"Step coverage dropped to {step_validation['coverage_percentage']:.1f}% (threshold: {step_validation['threshold']:.1f}%)")
        
        if not flow_validation["is_valid"]:
            errors.extend(flow_validation["warnings"])
        
        if not element_validation["passed"]:
            # Element coverage is a warning, not an error (less critical than step coverage)
            warnings.append(f"Element coverage: {element_validation['lost_elements_count']} elements lost (coverage: {element_validation['coverage_percentage']:.1f}%, threshold: {element_validation['threshold']:.1f}%)")
        
        if not scenario_validation["passed"]:
            errors.append(f"Lost critical scenarios: {', '.join(scenario_validation['lost_critical_scenarios'])}")
        
        if not data_validation["passed"]:
            
            warnings.append(f"Lost test data: {len(data_validation['lost_data_ids'])} data IDs, {len(data_validation['lost_step_data'])} step data values (step data coverage: {data_validation['step_data_coverage_percentage']:.1f}%, threshold: {data_validation.get('step_data_threshold', 90.0):.1f}%)")
        
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

