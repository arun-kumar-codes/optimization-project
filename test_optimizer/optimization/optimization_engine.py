"""
Module for optimizing test suite by removing duplicates while maintaining coverage.
Enhanced with step-level uniqueness and coverage checks.
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from analysis.duplicate_detector import DuplicateDetector
from analysis.step_uniqueness_analyzer import StepUniquenessAnalyzer
from flows.coverage_analyzer import CoverageAnalyzer
from flows.flow_analyzer import FlowAnalyzer
from optimization.step_coverage_tracker import StepCoverageTracker
from optimization.test_case_merger import TestCaseMerger


class OptimizationEngine:
    """Main engine for optimizing test suite with step-level safety checks."""
    
    def __init__(
        self,
        exact_threshold: float = 1.0,
        near_duplicate_threshold: float = 0.90,
        highly_similar_threshold: float = 0.75,
        min_coverage_percentage: float = 0.90,
        min_step_coverage_percentage: float = 0.95
    ):
        """
        Initialize optimization engine.
        
        Args:
            exact_threshold: Threshold for exact duplicates
            near_duplicate_threshold: Threshold for near duplicates
            highly_similar_threshold: Threshold for highly similar
            min_coverage_percentage: Minimum flow coverage to maintain (0.0 to 1.0)
            min_step_coverage_percentage: Minimum step coverage to maintain (0.0 to 1.0)
        """
        self.duplicate_detector = DuplicateDetector(
            exact_threshold,
            near_duplicate_threshold,
            highly_similar_threshold
        )
        self.coverage_analyzer = CoverageAnalyzer()
        self.flow_analyzer = FlowAnalyzer()
        self.step_uniqueness_analyzer = StepUniquenessAnalyzer()
        self.step_coverage_tracker = StepCoverageTracker()
        self.test_case_merger = TestCaseMerger()
        self.min_coverage = min_coverage_percentage
        self.min_step_coverage = min_step_coverage_percentage
    
    def optimize_test_suite(
        self,
        test_cases: Dict[int, TestCase],
        ai_recommendations: Dict = None,
        use_iterative: bool = True
    ) -> Dict:
        """
        Optimize test suite by removing duplicates while maintaining coverage.
        Enhanced with step-level checks and iterative optimization.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            ai_recommendations: Optional AI recommendations from Phase 4
            use_iterative: If True, use iterative optimization (one at a time with rollback)
            
        Returns:
            Optimization result dictionary
        """
        if use_iterative:
            return self.optimize_test_suite_iteratively(test_cases, ai_recommendations)
        
        # Original one-pass optimization (fallback)
        return self._optimize_test_suite_one_pass(test_cases, ai_recommendations)
    
    def optimize_test_suite_iteratively(
        self,
        test_cases: Dict[int, TestCase],
        ai_recommendations: Dict = None
    ) -> Dict:
        """
        Optimize test suite iteratively - one change at a time with rollback.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            ai_recommendations: Optional AI recommendations
            
        Returns:
            Optimization result dictionary
        """
        # Step 1: Calculate baseline coverage
        baseline_coverage = self.coverage_analyzer.calculate_flow_coverage(test_cases)
        baseline_critical = self.coverage_analyzer.identify_critical_flow_coverage(test_cases)
        baseline_step_coverage = self.step_coverage_tracker.calculate_step_coverage(test_cases)
        
        # Build step coverage map
        self.step_coverage_tracker.build_step_coverage_map(test_cases)
        
        # Step 2: Get optimization candidates (sorted by priority)
        candidates = self._get_optimization_candidates(test_cases, ai_recommendations)
        
        # Step 3: Iteratively optimize (one at a time with rollback)
        current_test_cases = test_cases.copy()
        to_remove = set()
        to_keep = set()
        to_merge = {}
        merged_test_cases = {}
        removal_reasons = {}
        skipped_candidates = []
        
        for candidate in candidates:
            # Try optimization
            result = self._try_optimize(current_test_cases, candidate, test_cases)
            
            if result["coverage_maintained"]:
                # Apply change
                current_test_cases = result["optimized_test_cases"]
                
                if result["action"] == "remove":
                    to_remove.add(candidate["test_case_id"])
                    removal_reasons[candidate["test_case_id"]] = result.get("reason", {})
                elif result["action"] == "merge":
                    merged_id = result.get("merged_id")
                    if merged_id:
                        merged_test_cases[merged_id] = result.get("merged_test_case")
                        to_merge[merged_id] = result.get("source_ids", [])
                        for source_id in result.get("source_ids", []):
                            to_remove.add(source_id)
                            removal_reasons[source_id] = {
                                "reason": "Merged",
                                "merged_id": merged_id,
                                "action": "merged"
                            }
            else:
                # Skip this candidate
                skipped_candidates.append({
                    "candidate": candidate,
                    "reason": result.get("reason", "Coverage would be lost")
                })
        
        # Step 4: Process exact duplicates (always safe)
        duplicate_groups = self.duplicate_detector.detect_duplicates(test_cases)
        for group in duplicate_groups["exact_duplicates"]:
            keep_id = group["recommended_keep"]
            remove_ids = group["recommended_remove"]
            
            if keep_id not in to_remove:
                to_keep.add(keep_id)
                for remove_id in remove_ids:
                    if remove_id not in to_remove:
                        to_remove.add(remove_id)
                        removal_reasons[remove_id] = {
                            "reason": "Exact duplicate",
                            "similar_to": keep_id,
                            "similarity": group["max_similarity"]
                        }
                        # Remove from current set
                        if remove_id in current_test_cases:
                            del current_test_cases[remove_id]
        
        # Process exact duplicates (100% similar - safe to remove)
        for group in duplicate_groups["exact_duplicates"]:
            keep_id = group["recommended_keep"]
            remove_ids = group["recommended_remove"]
            
            to_keep.add(keep_id)
            for remove_id in remove_ids:
                to_remove.add(remove_id)
                removal_reasons[remove_id] = {
                    "reason": "Exact duplicate",
                    "similar_to": keep_id,
                    "similarity": group["max_similarity"]
                }
        
        # Step 5: Apply AI recommendations for test cases not in duplicate groups
        if ai_recommendations:
            for test_id, recommendation in ai_recommendations.items():
                if test_id in current_test_cases and test_id not in to_remove and test_id not in to_keep:
                    action = recommendation.get("action", "keep")
                    if action == "remove":
                        # Try to remove based on AI recommendation
                        result = self._try_optimize(
                            current_test_cases,
                            {
                                "test_case_id": test_id,
                                "keep_id": None,
                                "similarity": 0.0,
                                "type": "ai_recommendation",
                                "priority": 2,  # Medium priority
                                "action": "remove"
                            },
                            test_cases
                        )
                        if result["coverage_maintained"]:
                            current_test_cases = result["optimized_test_cases"]
                            to_remove.add(test_id)
                            removal_reasons[test_id] = {
                                "reason": "AI recommendation: " + recommendation.get("justification", ""),
                                "similar_to": None,
                                "similarity": None,
                                "action": "ai_recommended_remove"
                            }
                    elif action == "keep":
                        # Explicitly keep this test case
                        to_keep.add(test_id)
        
        # Step 6: Finalize optimized test cases
        all_ids = set(test_cases.keys())
        final_to_keep = all_ids - to_remove
        optimized_test_cases = {tid: current_test_cases[tid] for tid in final_to_keep if tid in current_test_cases}
        optimized_test_cases.update(merged_test_cases)  # Add merged test cases
        
        # Step 7: Validate final coverage
        optimized_coverage = self.coverage_analyzer.calculate_flow_coverage(optimized_test_cases)
        optimized_critical = self.coverage_analyzer.identify_critical_flow_coverage(optimized_test_cases)
        optimized_step_coverage = self.step_coverage_tracker.calculate_step_coverage(optimized_test_cases)
        
        # Step 8: Calculate metrics
        original_count = len(test_cases)
        optimized_count = len(optimized_test_cases)
        reduction = original_count - optimized_count
        reduction_percentage = (reduction / original_count * 100) if original_count > 0 else 0
        
        # Calculate time savings
        original_time = sum(tc.duration or 0 for tc in test_cases.values())
        optimized_time = sum(tc.duration or 0 for tc in optimized_test_cases.values())
        time_saved = original_time - optimized_time
        time_saved_percentage = (time_saved / original_time * 100) if original_time > 0 else 0
        
        # Step coverage loss analysis
        step_coverage_loss = self.step_coverage_tracker.check_coverage_loss(
            test_cases,
            optimized_test_cases
        )
        
        return {
            "original_test_cases": original_count,
            "optimized_test_cases": optimized_count,
            "reduction": reduction,
            "reduction_percentage": reduction_percentage,
            "test_cases_kept": sorted(list(final_to_keep)),
            "test_cases_removed": sorted(list(to_remove)),
            "test_cases_merged": to_merge,
            "merged_test_cases": list(merged_test_cases.keys()),
            "merged_test_cases_dict": merged_test_cases,  # Full merged test cases for output
            "removal_reasons": removal_reasons,
            "skipped_candidates": len(skipped_candidates),
            "coverage": {
                "before": {
                    "total_flows": baseline_coverage["total_unique_flows"],
                    "covered_flows": baseline_coverage["covered_flows"],
                    "coverage_percentage": baseline_coverage["coverage_percentage"],
                    "critical_flows_covered": baseline_critical["all_critical_covered"],
                    "step_coverage": {
                        "total_unique_steps": baseline_step_coverage["total_unique_steps"],
                        "coverage_percentage": baseline_step_coverage["coverage_percentage"]
                    }
                },
                "after": {
                    "total_flows": optimized_coverage["total_unique_flows"],
                    "covered_flows": optimized_coverage["covered_flows"],
                    "coverage_percentage": optimized_coverage["coverage_percentage"],
                    "critical_flows_covered": optimized_critical["all_critical_covered"],
                    "step_coverage": {
                        "total_unique_steps": optimized_step_coverage["total_unique_steps"],
                        "coverage_percentage": optimized_step_coverage["coverage_percentage"]
                    }
                }
            },
            "step_coverage_loss": {
                "lost_step_count": step_coverage_loss["lost_step_count"],
                "coverage_percentage_after": step_coverage_loss["coverage_percentage_after"],
                "coverage_maintained": step_coverage_loss["coverage_maintained"]
            },
            "time_savings": {
                "original_time_ms": original_time,
                "optimized_time_ms": optimized_time,
                "time_saved_ms": time_saved,
                "time_saved_percentage": time_saved_percentage,
                "time_saved_seconds": time_saved / 1000 if time_saved else 0
            },
            "duplicate_groups": duplicate_groups
        }
    
    def _optimize_test_suite_one_pass(
        self,
        test_cases: Dict[int, TestCase],
        ai_recommendations: Dict = None
    ) -> Dict:
        """
        Original one-pass optimization (for backward compatibility).
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            ai_recommendations: Optional AI recommendations
            
        Returns:
            Optimization result dictionary
        """
        # Step 1: Calculate baseline coverage (flow and step level)
        baseline_coverage = self.coverage_analyzer.calculate_flow_coverage(test_cases)
        baseline_critical = self.coverage_analyzer.identify_critical_flow_coverage(test_cases)
        baseline_step_coverage = self.step_coverage_tracker.calculate_step_coverage(test_cases)
        
        # Build step coverage map
        self.step_coverage_tracker.build_step_coverage_map(test_cases)
        
        # Step 2: Detect duplicates
        duplicate_groups = self.duplicate_detector.detect_duplicates(test_cases)
        
        # Step 3: Identify test cases to merge or remove (with step-level checks)
        to_remove = set()
        to_keep = set()
        to_merge = {}  # {merged_id: [source_ids]}
        merged_test_cases = {}  # {merged_id: TestCase}
        removal_reasons = {}
        
        # Process exact duplicates (100% similar - safe to remove)
        for group in duplicate_groups["exact_duplicates"]:
            keep_id = group["recommended_keep"]
            remove_ids = group["recommended_remove"]
            
            to_keep.add(keep_id)
            for remove_id in remove_ids:
                to_remove.add(remove_id)
                removal_reasons[remove_id] = {
                    "reason": "Exact duplicate",
                    "similar_to": keep_id,
                    "similarity": group["max_similarity"]
                }
        
        # Process near duplicates (>90% similar) - CHECK FOR MERGING FIRST
        for group in duplicate_groups["near_duplicates"]:
            keep_id = group["recommended_keep"]
            remove_ids = group["recommended_remove"]
            
            # Check if keep_id is already marked for removal
            if keep_id not in to_remove:
                # Check each removal candidate individually
                for remove_id in remove_ids:
                    if remove_id not in to_keep and remove_id not in to_remove:
                        # Check if should merge instead of remove
                        should_merge = self.test_case_merger.should_merge_instead_of_remove(
                            test_cases[keep_id],
                            test_cases[remove_id]
                        )
                        
                        if should_merge:
                            # Merge test cases
                            merged_id = self.test_case_merger.generate_merged_test_case_id([keep_id, remove_id])
                            merged_tc = self.test_case_merger.generate_merged_test_case(
                                test_cases[keep_id],
                                test_cases[remove_id],
                                merged_id
                            )
                            
                            merged_test_cases[merged_id] = merged_tc
                            to_merge[merged_id] = [keep_id, remove_id]
                            to_remove.add(keep_id)
                            to_remove.add(remove_id)
                            
                            removal_reasons[remove_id] = {
                                "reason": "Merged with similar test case",
                                "merged_with": keep_id,
                                "merged_id": merged_id,
                                "similarity": group["max_similarity"],
                                "action": "merged"
                            }
                            removal_reasons[keep_id] = {
                                "reason": "Merged with similar test case",
                                "merged_with": remove_id,
                                "merged_id": merged_id,
                                "similarity": group["max_similarity"],
                                "action": "merged"
                            }
                        else:
                            # Check if safe to remove with step-level validation
                            removal_check = self._should_remove_test_case(
                                remove_id,
                                keep_id,
                                test_cases,
                                to_remove,
                                to_keep
                            )
                            
                            if removal_check["can_remove"]:
                                to_keep.add(keep_id)
                                to_remove.add(remove_id)
                                removal_reasons[remove_id] = {
                                    "reason": "Near duplicate (>90% similar)",
                                    "similar_to": keep_id,
                                    "similarity": group["max_similarity"],
                                    "unique_steps_lost": removal_check.get("unique_steps_lost", 0),
                                    "step_coverage_maintained": removal_check.get("step_coverage_maintained", True)
                                }
                            else:
                                # Don't remove - unique steps not covered
                                to_keep.add(keep_id)
                                removal_reasons[remove_id] = {
                                    "reason": f"Near duplicate but kept: {removal_check.get('reason', 'Unique steps not covered')}",
                                    "similar_to": keep_id,
                                    "similarity": group["max_similarity"],
                                    "action": "kept"
                                }
        
        # Process highly similar (>75% similar) - CHECK FOR MERGING FIRST
        for group in duplicate_groups["highly_similar"]:
            keep_id = group["recommended_keep"]
            remove_ids = group["recommended_remove"]
            
            # Only remove if keep_id is not already removed
            if keep_id not in to_remove:
                # Check EACH test case individually (not just first one)
                for remove_id in remove_ids:
                    if remove_id not in to_keep and remove_id not in to_remove:
                        # Check if should merge instead of remove
                        should_merge = self.test_case_merger.should_merge_instead_of_remove(
                            test_cases[keep_id],
                            test_cases[remove_id]
                        )
                        
                        if should_merge:
                            # Merge test cases
                            merged_id = self.test_case_merger.generate_merged_test_case_id([keep_id, remove_id])
                            merged_tc = self.test_case_merger.generate_merged_test_case(
                                test_cases[keep_id],
                                test_cases[remove_id],
                                merged_id
                            )
                            
                            merged_test_cases[merged_id] = merged_tc
                            to_merge[merged_id] = [keep_id, remove_id]
                            to_remove.add(keep_id)
                            to_remove.add(remove_id)
                            
                            removal_reasons[remove_id] = {
                                "reason": "Merged with similar test case",
                                "merged_with": keep_id,
                                "merged_id": merged_id,
                                "similarity": group["max_similarity"],
                                "action": "merged"
                            }
                            removal_reasons[keep_id] = {
                                "reason": "Merged with similar test case",
                                "merged_with": remove_id,
                                "merged_id": merged_id,
                                "similarity": group["max_similarity"],
                                "action": "merged"
                            }
                        else:
                            # Comprehensive check before removing
                            removal_check = self._should_remove_test_case(
                                remove_id,
                                keep_id,
                                test_cases,
                                to_remove,
                                to_keep
                            )
                            
                            if removal_check["can_remove"]:
                                to_keep.add(keep_id)
                                to_remove.add(remove_id)
                                removal_reasons[remove_id] = {
                                    "reason": "Highly similar (>75% similar)",
                                    "similar_to": keep_id,
                                    "similarity": group["max_similarity"],
                                    "unique_steps_lost": removal_check.get("unique_steps_lost", 0),
                                    "step_coverage_maintained": removal_check.get("step_coverage_maintained", True)
                                }
                            else:
                                # Don't remove - coverage would be lost
                                to_keep.add(keep_id)
                                removal_reasons[remove_id] = {
                                    "reason": f"Highly similar but kept: {removal_check.get('reason', 'Coverage would be lost')}",
                                    "similar_to": keep_id,
                                    "similarity": group["max_similarity"],
                                    "action": "kept"
                                }
        
        # Step 4: Apply AI recommendations if available (with step-level validation)
        if ai_recommendations:
            for test_id, recommendation in ai_recommendations.items():
                if test_id in test_cases and test_id not in to_keep:
                    action = recommendation.get("action", "keep")
                    if action == "remove":
                        # Verify coverage impact with step-level check
                        removal_check = self._should_remove_test_case(
                            test_id,
                            None,  # No specific similar test case
                            test_cases,
                            to_remove,
                            to_keep
                        )
                        
                        if removal_check["can_remove"]:
                            to_remove.add(test_id)
                            removal_reasons[test_id] = {
                                "reason": "AI recommendation: " + recommendation.get("justification", ""),
                                "similar_to": None,
                                "similarity": None,
                                "unique_steps_lost": removal_check.get("unique_steps_lost", 0),
                                "step_coverage_maintained": removal_check.get("step_coverage_maintained", True)
                            }
        
        # Step 5: Add merged test cases to optimized set
        # Step 6: Ensure all test cases are either kept or removed
        all_ids = set(test_cases.keys())
        final_to_keep = all_ids - to_remove
        
        # Step 7: Validate coverage (flow and step level)
        # Include merged test cases in optimized set
        optimized_test_cases = {tid: test_cases[tid] for tid in final_to_keep}
        optimized_test_cases.update(merged_test_cases)  # Add merged test cases
        optimized_coverage = self.coverage_analyzer.calculate_flow_coverage(optimized_test_cases)
        optimized_critical = self.coverage_analyzer.identify_critical_flow_coverage(optimized_test_cases)
        optimized_step_coverage = self.step_coverage_tracker.calculate_step_coverage(optimized_test_cases)
        
        # Step 8: Calculate metrics
        original_count = len(test_cases)
        optimized_count = len(optimized_test_cases)
        reduction = original_count - optimized_count
        reduction_percentage = (reduction / original_count * 100) if original_count > 0 else 0
        
        # Calculate time savings (estimate)
        original_time = sum(tc.duration or 0 for tc in test_cases.values())
        optimized_time = sum(tc.duration or 0 for tc in optimized_test_cases.values())
        time_saved = original_time - optimized_time
        time_saved_percentage = (time_saved / original_time * 100) if original_time > 0 else 0
        
        # Step coverage loss analysis
        step_coverage_loss = self.step_coverage_tracker.check_coverage_loss(
            test_cases,
            optimized_test_cases
        )
        
        return {
            "original_test_cases": original_count,
            "optimized_test_cases": optimized_count,
            "reduction": reduction,
            "reduction_percentage": reduction_percentage,
            "test_cases_kept": sorted(list(final_to_keep)),
            "test_cases_removed": sorted(list(to_remove)),
            "test_cases_merged": to_merge,  # {merged_id: [source_ids]}
            "merged_test_cases": list(merged_test_cases.keys()),  # List of merged test case IDs
            "removal_reasons": removal_reasons,
            "coverage": {
                "before": {
                    "total_flows": baseline_coverage["total_unique_flows"],
                    "covered_flows": baseline_coverage["covered_flows"],
                    "coverage_percentage": baseline_coverage["coverage_percentage"],
                    "critical_flows_covered": baseline_critical["all_critical_covered"],
                    "step_coverage": {
                        "total_unique_steps": baseline_step_coverage["total_unique_steps"],
                        "coverage_percentage": baseline_step_coverage["coverage_percentage"]
                    }
                },
                "after": {
                    "total_flows": optimized_coverage["total_unique_flows"],
                    "covered_flows": optimized_coverage["covered_flows"],
                    "coverage_percentage": optimized_coverage["coverage_percentage"],
                    "critical_flows_covered": optimized_critical["all_critical_covered"],
                    "step_coverage": {
                        "total_unique_steps": optimized_step_coverage["total_unique_steps"],
                        "coverage_percentage": optimized_step_coverage["coverage_percentage"]
                    }
                }
            },
            "step_coverage_loss": {
                "lost_step_count": step_coverage_loss["lost_step_count"],
                "coverage_percentage_after": step_coverage_loss["coverage_percentage_after"],
                "coverage_maintained": step_coverage_loss["coverage_maintained"]
            },
            "time_savings": {
                "original_time_ms": original_time,
                "optimized_time_ms": optimized_time,
                "time_saved_ms": time_saved,
                "time_saved_percentage": time_saved_percentage,
                "time_saved_seconds": time_saved / 1000 if time_saved else 0
            },
            "duplicate_groups": duplicate_groups
        }
    
    def _should_remove_test_case(
        self,
        remove_id: int,
        keep_id: Optional[int],
        test_cases: Dict[int, TestCase],
        to_remove: Set[int],
        to_keep: Set[int]
    ) -> Dict:
        """
        Comprehensive check before removing a test case.
        
        Args:
            remove_id: Test case ID to potentially remove
            keep_id: Test case ID to keep (if similar pair)
            test_cases: All test cases
            to_remove: Set of test cases already marked for removal
            to_keep: Set of test cases already marked to keep
            
        Returns:
            Dictionary with removal decision and details
        """
        if remove_id not in test_cases:
            return {
                "can_remove": False,
                "reason": "Test case not found"
            }
        
        test_case_to_remove = test_cases[remove_id]
        
        # Create test set without this test case
        test_set = {k: v for k, v in test_cases.items() 
                   if k != remove_id and k not in to_remove}
        
        # If we have a similar test case to keep, ensure it's in the set
        if keep_id and keep_id in test_cases:
            test_set[keep_id] = test_cases[keep_id]
        
        # Check flow coverage
        flow_coverage = self.coverage_analyzer.calculate_flow_coverage(test_set)
        flow_coverage_maintained = flow_coverage["coverage_percentage"] >= self.min_coverage * 100
        
        # Check step coverage
        step_coverage_check = self.step_coverage_tracker.validate_step_coverage_maintained(
            test_cases,
            test_set,
            self.min_step_coverage
        )
        
        # Identify unique steps in test case to remove
        unique_steps_info = None
        if keep_id and keep_id in test_cases:
            # Compare with similar test case
            uniqueness_result = self.step_uniqueness_analyzer.identify_unique_steps(
                test_case_to_remove,
                test_cases[keep_id]
            )
            unique_steps_count = uniqueness_result["unique_in_test_case_1"]["total"]
            
            # Check if unique steps are covered elsewhere
            unique_steps = uniqueness_result["unique_in_test_case_1"]["exact"] + \
                          uniqueness_result["unique_in_test_case_1"]["fuzzy"]
            coverage_info = self.step_uniqueness_analyzer.check_step_coverage(
                unique_steps,
                test_set
            )
            
            unique_steps_info = {
                "unique_steps_count": unique_steps_count,
                "unique_steps_covered_elsewhere": coverage_info["all_covered"],
                "coverage_percentage": coverage_info["coverage_percentage"]
            }
        else:
            # No similar test case - check uniqueness against all others
            uniqueness_score = self.step_uniqueness_analyzer.calculate_step_uniqueness_score(
                test_case_to_remove,
                test_cases
            )
            unique_steps_info = {
                "uniqueness_score": uniqueness_score,
                "unique_steps_count": len(test_case_to_remove.steps) if uniqueness_score > 0.5 else 0
            }
        
        # Decision logic
        can_remove = (
            flow_coverage_maintained and
            step_coverage_check["is_maintained"] and
            (unique_steps_info is None or 
             unique_steps_info.get("unique_steps_covered_elsewhere", True) or
             unique_steps_info.get("uniqueness_score", 0) < 0.3)
        )
        
        reason = ""
        if not flow_coverage_maintained:
            reason = "Flow coverage would drop below threshold"
        elif not step_coverage_check["is_maintained"]:
            reason = f"Step coverage would drop to {step_coverage_check['coverage_percentage']:.1f}% (threshold: {step_coverage_check['threshold']:.1f}%)"
        elif unique_steps_info and not unique_steps_info.get("unique_steps_covered_elsewhere", True):
            reason = f"Has {unique_steps_info.get('unique_steps_count', 0)} unique steps not covered elsewhere"
        else:
            reason = "Safe to remove"
        
        return {
            "can_remove": can_remove,
            "reason": reason,
            "flow_coverage_maintained": flow_coverage_maintained,
            "step_coverage_maintained": step_coverage_check["is_maintained"],
            "step_coverage_percentage": step_coverage_check["coverage_percentage"],
            "unique_steps_lost": unique_steps_info.get("unique_steps_count", 0) if unique_steps_info else 0,
            "unique_steps_info": unique_steps_info
        }
    
    def _identify_unique_steps(
        self,
        test_case1: TestCase,
        test_case2: TestCase
    ) -> Dict:
        """
        Identify unique steps between two test cases.
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            
        Returns:
            Dictionary with unique steps information
        """
        return self.step_uniqueness_analyzer.identify_unique_steps(test_case1, test_case2)
    
    def _check_step_coverage(
        self,
        unique_steps: List,
        other_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Check if unique steps are covered by other test cases.
        
        Args:
            unique_steps: List of unique steps
            other_test_cases: Other test cases to check
            
        Returns:
            Coverage information
        """
        return self.step_uniqueness_analyzer.check_step_coverage(unique_steps, other_test_cases)
    
    def _validate_step_coverage(
        self,
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Validate step coverage for a set of test cases.
        
        Args:
            test_cases: Dictionary of test cases
            
        Returns:
            Step coverage metrics
        """
        return self.step_coverage_tracker.calculate_step_coverage(test_cases)
    
    def _get_optimization_candidates(
        self,
        test_cases: Dict[int, TestCase],
        ai_recommendations: Dict = None
    ) -> List[Dict]:
        """
        Get all optimization candidates sorted by priority.
        
        Args:
            test_cases: Dictionary of all test cases
            
        Returns:
            List of candidate dictionaries sorted by priority
        """
        candidates = []
        
        # Detect duplicates
        duplicate_groups = self.duplicate_detector.detect_duplicates(test_cases)
        
        # Process exact duplicates (highest priority - safest)
        for group in duplicate_groups["exact_duplicates"]:
            keep_id = group["recommended_keep"]
            for remove_id in group["recommended_remove"]:
                candidates.append({
                    "test_case_id": remove_id,
                    "keep_id": keep_id,
                    "similarity": group["max_similarity"],
                    "type": "exact_duplicate",
                    "priority": 1,  # Highest priority
                    "action": "remove"
                })
        
        # Process near duplicates
        for group in duplicate_groups["near_duplicates"]:
            keep_id = group["recommended_keep"]
            for remove_id in group["recommended_remove"]:
                # Check if should merge
                should_merge = self.test_case_merger.should_merge_instead_of_remove(
                    test_cases[keep_id],
                    test_cases[remove_id]
                )
                
                candidates.append({
                    "test_case_id": remove_id,
                    "keep_id": keep_id,
                    "similarity": group["max_similarity"],
                    "type": "near_duplicate",
                    "priority": 2,
                    "action": "merge" if should_merge else "remove"
                })
        
        # Process highly similar
        for group in duplicate_groups["highly_similar"]:
            keep_id = group["recommended_keep"]
            for remove_id in group["recommended_remove"]:
                should_merge = self.test_case_merger.should_merge_instead_of_remove(
                    test_cases[keep_id],
                    test_cases[remove_id]
                )
                
                candidates.append({
                    "test_case_id": remove_id,
                    "keep_id": keep_id,
                    "similarity": group["max_similarity"],
                    "type": "highly_similar",
                    "priority": 3,  # Lower priority
                    "action": "merge" if should_merge else "remove"
                })
        
        # Enhance candidates with AI recommendations if available
        if ai_recommendations:
            for candidate in candidates:
                test_id = candidate["test_case_id"]
                if test_id in ai_recommendations:
                    ai_rec = ai_recommendations[test_id]
                    # Adjust priority based on AI recommendation
                    if ai_rec.get("action") == "remove":
                        # AI says remove - increase priority (make it higher priority)
                        candidate["priority"] = max(0.5, candidate["priority"] - 0.5)
                        candidate["ai_recommendation"] = "remove"
                        candidate["ai_justification"] = ai_rec.get("justification", "")
                    elif ai_rec.get("action") == "keep":
                        # AI says keep - decrease priority (make it lower priority)
                        candidate["priority"] = candidate["priority"] + 1.0
                        candidate["ai_recommendation"] = "keep"
                    elif ai_rec.get("action") == "merge":
                        # AI suggests merge - adjust action
                        if candidate["action"] != "merge":
                            candidate["action"] = "merge"
                        candidate["ai_recommendation"] = "merge"
                        candidate["ai_justification"] = ai_rec.get("justification", "")
        
        # Sort by priority (1 = highest), then by similarity (higher = safer)
        candidates.sort(key=lambda x: (x["priority"], -x["similarity"]))
        
        return candidates
    
    def _try_optimize(
        self,
        current_test_cases: Dict[int, TestCase],
        candidate: Dict,
        original_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Try one optimization and return result with coverage check.
        
        Args:
            current_test_cases: Current state of test cases
            candidate: Optimization candidate
            original_test_cases: Original test cases (for baseline)
            
        Returns:
            Result dictionary with coverage check
        """
        # Create snapshot
        snapshot = current_test_cases.copy()
        
        test_case_id = candidate["test_case_id"]
        keep_id = candidate.get("keep_id")
        action = candidate.get("action", "remove")
        
        if test_case_id not in current_test_cases:
            return {
                "optimized_test_cases": snapshot,
                "coverage_maintained": False,
                "reason": "Test case not found in current set",
                "action": action
            }
        
        # Try optimization
        if action == "merge" and keep_id and keep_id in current_test_cases:
            # Try merging
            try:
                merged_id = self.test_case_merger.generate_merged_test_case_id([keep_id, test_case_id])
                merged_tc = self.test_case_merger.generate_merged_test_case(
                    current_test_cases[keep_id],
                    current_test_cases[test_case_id],
                    merged_id
                )
                
                # Create optimized set
                optimized = {k: v for k, v in current_test_cases.items() 
                           if k != test_case_id and k != keep_id}
                optimized[merged_id] = merged_tc
                
                # Validate coverage
                coverage_check = self._validate_coverage(snapshot, optimized, original_test_cases)
                
                if coverage_check["passed"]:
                    return {
                        "optimized_test_cases": optimized,
                        "coverage_maintained": True,
                        "action": "merge",
                        "merged_id": merged_id,
                        "merged_test_case": merged_tc,
                        "source_ids": [keep_id, test_case_id],
                        "reason": "Merged successfully"
                    }
                else:
                    return {
                        "optimized_test_cases": snapshot,
                        "coverage_maintained": False,
                        "action": "merge",
                        "reason": coverage_check["reason"]
                    }
            except Exception as e:
                return {
                    "optimized_test_cases": snapshot,
                    "coverage_maintained": False,
                    "action": "merge",
                    "reason": f"Merge failed: {str(e)}"
                }
        
        else:
            # Try removal
            optimized = {k: v for k, v in current_test_cases.items() 
                        if k != test_case_id}
            
            # Ensure keep_id is in optimized set
            if keep_id and keep_id in current_test_cases:
                optimized[keep_id] = current_test_cases[keep_id]
            
            # Validate coverage
            coverage_check = self._validate_coverage(snapshot, optimized, original_test_cases)
            
            if coverage_check["passed"]:
                return {
                    "optimized_test_cases": optimized,
                    "coverage_maintained": True,
                    "action": "remove",
                    "reason": "Removed successfully"
                }
            else:
                return {
                    "optimized_test_cases": snapshot,
                    "coverage_maintained": False,
                    "action": "remove",
                    "reason": coverage_check["reason"]
                }
    
    def _validate_coverage(
        self,
        original: Dict[int, TestCase],
        optimized: Dict[int, TestCase],
        baseline: Dict[int, TestCase]
    ) -> Dict:
        """
        Comprehensive coverage validation.
        
        Args:
            original: Original test cases (before this change)
            optimized: Optimized test cases (after this change)
            baseline: Baseline test cases (for comparison)
            
        Returns:
            Validation result
        """
        # Check flow coverage
        original_flow = self.coverage_analyzer.calculate_flow_coverage(original)
        optimized_flow = self.coverage_analyzer.calculate_flow_coverage(optimized)
        
        flow_maintained = optimized_flow["coverage_percentage"] >= self.min_coverage * 100
        
        # Check step coverage
        step_check = self.step_coverage_tracker.validate_step_coverage_maintained(
            original,
            optimized,
            self.min_step_coverage
        )
        
        # Check critical flows
        original_critical = self.coverage_analyzer.identify_critical_flow_coverage(original)
        optimized_critical = self.coverage_analyzer.identify_critical_flow_coverage(optimized)
        critical_maintained = optimized_critical["all_critical_covered"]
        
        passed = flow_maintained and step_check["is_maintained"] and critical_maintained
        
        reason = ""
        if not flow_maintained:
            reason = f"Flow coverage dropped to {optimized_flow['coverage_percentage']:.1f}%"
        elif not step_check["is_maintained"]:
            reason = f"Step coverage dropped to {step_check['coverage_percentage']:.1f}%"
        elif not critical_maintained:
            reason = "Critical flows no longer covered"
        else:
            reason = "Coverage maintained"
        
        return {
            "passed": passed,
            "reason": reason,
            "flow_coverage": {
                "original": original_flow["coverage_percentage"],
                "optimized": optimized_flow["coverage_percentage"],
                "maintained": flow_maintained
            },
            "step_coverage": {
                "original": step_check.get("coverage_percentage", 100),
                "optimized": step_check["coverage_percentage"],
                "maintained": step_check["is_maintained"]
            },
            "critical_flows": {
                "original": original_critical["all_critical_covered"],
                "optimized": critical_maintained,
                "maintained": critical_maintained
            }
        }
    
    def _create_snapshot(self, test_cases: Dict[int, TestCase]) -> Dict[int, TestCase]:
        """Create snapshot of test cases for rollback."""
        return test_cases.copy()
