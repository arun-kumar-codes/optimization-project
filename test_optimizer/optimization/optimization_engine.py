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
from analysis.role_classifier import RoleClassifier
from analysis.website_grouper import WebsiteGrouper
from analysis.prefix_analyzer import PrefixAnalyzer
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
        self.role_classifier = RoleClassifier()
        self.website_grouper = WebsiteGrouper()
        self.prefix_analyzer = PrefixAnalyzer()
        self.test_case_merger = TestCaseMerger() 
        self.min_coverage = min_coverage_percentage
        self.min_step_coverage = min_step_coverage_percentage
        self.role_classifications: Dict[int, str] = {} 
        self.role_website_groups: Dict[Tuple[str, str], List[int]] = {} 
    def get_test_case_role(
        self,
        test_case_id: int
    ) -> str:
        """
        Get role classification for a test case.
        
        Args:
            test_case_id: Test case ID
            
        Returns:
            "admin", "user", or "unknown"
        """
        return self.role_classifications.get(test_case_id, "unknown")
    
    def have_same_role(
        self,
        test_case_id1: int,
        test_case_id2: int
    ) -> bool:
        """
        Check if two test cases have the same role.
        
        Args:
            test_case_id1: First test case ID
            test_case_id2: Second test case ID
            
        Returns:
            True if same role (and not "unknown"), False otherwise
        """
        role1 = self.get_test_case_role(test_case_id1)
        role2 = self.get_test_case_role(test_case_id2)
        
        return role1 == role2 and role1 != "unknown"
    
    def _perform_multi_test_case_merging(
        self,
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Perform multi-test-case merging within (role, website) groups.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Result dictionary with merged test cases
        """
        merged_count = 0
        new_test_cases = {}
        merged_groups = []
        test_cases_to_remove = set()
        
        for (role, website), test_case_ids in self.role_website_groups.items():
            # ENHANCED: Allow pairs (min_group_size=2) for maximum merging
            if len(test_case_ids) < 2:
                continue
            
            # Get test cases for this group
            group_test_cases = [test_cases[tid] for tid in test_case_ids if tid in test_cases]
            
            if len(group_test_cases) < 2:
                continue
            
            mergeable_groups = self.prefix_analyzer.find_mergeable_groups(
                {tc.id: tc for tc in group_test_cases},
                min_prefix_length=1,  # Lowered to allow login pattern detection (even 1 step)
                min_group_size=2,     # CHANGED: Allow pairs to merge
                use_flexible_login=True  
            )
            
            for merge_group in mergeable_groups:
                group_test_cases_list = merge_group["test_cases"]
                group_ids = [tc.id for tc in group_test_cases_list]
                
                # Validate merge safety (role/website consistency)
                from optimization.coverage_validator import CoverageValidator
                validator = CoverageValidator()
                safety_check = validator.validate_merge_safety(group_test_cases_list)
                
                if not safety_check["passed"]:
                    print(f"      [MULTI-MERGE] Skipping merge of {group_ids}: {safety_check['issues']}")
                    continue
                
                # CRITICAL: Validate step flow compatibility before merging
                from optimization.step_flow_validator import StepFlowValidator
                flow_validator = StepFlowValidator()
                
                # Check if test cases have compatible flows
                flow_compatible = True
                for tc in group_test_cases_list:
                    deps_issues = flow_validator.validate_step_dependencies(tc.steps)
                    if len(deps_issues) > 10:  # Too many dependency issues
                        flow_compatible = False
                        break
                
                if not flow_compatible:
                    print(f"      [MULTI-MERGE] Skipping merge of {group_ids}: Too many flow dependency issues")
                    continue
                
                # CRITICAL: Validate step coverage BEFORE merging
                # Create a test merge to check coverage impact
                try:
                    merged_tc = self.test_case_merger.merge_multiple_test_cases(group_test_cases_list)
                    
                    # Create test optimized set
                    test_optimized = {
                        tid: tc for tid, tc in test_cases.items()
                        if tid not in group_ids
                    }
                    test_optimized[merged_tc.id] = merged_tc
                    
                    # Validate coverage against baseline (original test_cases)
                    # For large merges (10+ test cases), use slightly lower threshold (95%)
                    # because some step loss is expected but still acceptable for consolidation
                    is_large_merge = len(group_ids) >= 10
                    original_threshold = self.min_step_coverage
                    
                    # Temporarily lower threshold for large merges
                    if is_large_merge:
                        self.min_step_coverage = 0.95
                    
                    coverage_check = self._validate_coverage(
                        test_cases,  # snapshot (before merge)
                        test_optimized,  # optimized (after merge)
                        test_cases  # baseline (original full suite)
                    )
                    
                    # Restore original threshold
                    if is_large_merge:
                        self.min_step_coverage = original_threshold
                    
                    if not coverage_check["passed"]:
                        print(f"      [MULTI-MERGE] Skipping merge of {group_ids}: {coverage_check.get('reason', 'Step coverage would drop below threshold')}")
                        continue
                    
                    # Coverage maintained - proceed with merge
                    new_test_cases[merged_tc.id] = merged_tc
                    test_cases_to_remove.update(group_ids)
                    merged_groups.append({
                        "source_ids": group_ids,
                        "merged_id": merged_tc.id,
                        "prefix_length": merge_group["prefix_length"],
                        "group_size": len(group_test_cases_list)
                    })
                    merged_count += 1
                    print(f"      [MULTI-MERGE] Merged {len(group_test_cases_list)} test cases (TC{group_ids}) → TC{merged_tc.id}")
                except Exception as e:
                    print(f"      [MULTI-MERGE] Failed to merge {group_ids}: {e}")
                    continue
        
        # Create updated test cases dict
        optimized_test_cases = {
            tid: tc for tid, tc in test_cases.items()
            if tid not in test_cases_to_remove
        }
        optimized_test_cases.update(new_test_cases)
        
        return {
            "merged_count": merged_count,
            "new_test_cases_count": len(new_test_cases),
            "removed_count": len(test_cases_to_remove),
            "optimized_test_cases": optimized_test_cases,
            "merged_groups": merged_groups
        }
    
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
        print(f"  [OPTIMIZATION ENGINE] Starting iterative optimization on {len(test_cases)} test cases...")
        
        print(f"  [OPTIMIZATION ENGINE] Step 0: Classifying test cases by role (admin/user)...")
        self.role_classifications = self.role_classifier.classify_test_cases(test_cases)
        role_stats = self.role_classifier.get_role_statistics(test_cases)
        print(f"    Role distribution: {role_stats['admin']} admin, {role_stats['user']} user, {role_stats['unknown']} unknown")
        print(f"    Admin: {role_stats['admin_percentage']:.1f}%, User: {role_stats['user_percentage']:.1f}%")
        
        print(f"  [OPTIMIZATION ENGINE] Step 0b: Grouping test cases by (role, website)...")
        self.role_website_groups = self.website_grouper.group_by_role_and_website(
            test_cases,
            self.role_classifications
        )
        role_website_stats = self.website_grouper.get_role_website_statistics(
            test_cases,
            self.role_classifications
        )
        print(f"    Found {role_website_stats['groups']} (role, website) groups")
        for group_key, count in list(role_website_stats['distribution'].items())[:5]:
            print(f"      - {group_key}: {count} test cases")
        
        self.test_case_merger.role_classifications = self.role_classifications
        
        print(f"  [OPTIMIZATION ENGINE] Step 1: Calculating baseline coverage...")
        baseline_coverage = self.coverage_analyzer.calculate_flow_coverage(test_cases)
        baseline_critical = self.coverage_analyzer.identify_critical_flow_coverage(test_cases)
        baseline_step_coverage = self.step_coverage_tracker.calculate_step_coverage(test_cases)
        print(f"    Baseline flow coverage: {baseline_coverage['coverage_percentage']:.1f}% ({baseline_coverage['covered_flows']}/{baseline_coverage['total_unique_flows']} flows)")
        print(f"    Baseline step coverage: {baseline_step_coverage['coverage_percentage']:.1f}% ({baseline_step_coverage['covered_steps']}/{baseline_step_coverage['total_unique_steps']} steps)")
        print(f"    Critical flows covered: {baseline_critical['all_critical_covered']}")
        
        print(f"  [OPTIMIZATION ENGINE] Building step coverage map...")
        self.step_coverage_tracker.build_step_coverage_map(test_cases)
        
        print(f"  [OPTIMIZATION ENGINE] Step 2: Multi-test-case merging (enabled - login once, run all scenarios, logout once)...")
        current_test_cases = test_cases.copy()
        multi_merged_test_cases = {}  # Track multi-merged test cases separately
        multi_merged_source_ids = set()  # Track which original test cases were merged
        multi_merge_result = self._perform_multi_test_case_merging(current_test_cases)
        if multi_merge_result["merged_count"] > 0:
            current_test_cases = multi_merge_result["optimized_test_cases"]
            # Extract multi-merged test cases (they have new IDs not in original test_cases)
            for merged_id, merged_tc in current_test_cases.items():
                if merged_id not in test_cases:  # New ID = multi-merged test case
                    multi_merged_test_cases[merged_id] = merged_tc
            # Extract source IDs that were merged (from merged_groups)
            for merged_group in multi_merge_result.get("merged_groups", []):
                source_ids = merged_group.get("source_ids", [])
                multi_merged_source_ids.update(source_ids)
            print(f"    Merged {multi_merge_result['merged_count']} groups into {multi_merge_result['new_test_cases_count']} consolidated flows")
            print(f"    Source test cases merged: {sorted(multi_merged_source_ids)}")
        else:
            print(f"    No safe multi-merge opportunities found (all skipped due to coverage validation)")
        
        print(f"  [OPTIMIZATION ENGINE] Step 3: Getting optimization candidates...")
        candidates = self._get_optimization_candidates(current_test_cases, ai_recommendations)
        print(f"    Found {len(candidates)} optimization candidates")
        if candidates:
            top_5 = [f"TC{c['test_case_id']} ({c['type']}, sim={c.get('similarity', 0):.1%}, action={c.get('action', 'unknown')})" for c in candidates[:5]]
            print(f"    Top 5 candidates: {top_5}")
            exact = sum(1 for c in candidates if c.get('type') == 'exact_duplicate')
            near = sum(1 for c in candidates if c.get('type') == 'near_duplicate')
            highly = sum(1 for c in candidates if c.get('type') == 'highly_similar')
            merge_count = sum(1 for c in candidates if c.get('action') == 'merge')
            remove_count = sum(1 for c in candidates if c.get('action') == 'remove')
            print(f"    Breakdown: {exact} exact, {near} near, {highly} highly similar | {merge_count} merge, {remove_count} remove")
        
        print(f"  [OPTIMIZATION ENGINE] Step 4: Iteratively optimizing (one at a time with rollback)...")
        # current_test_cases already set from multi-merge step
        to_remove = multi_merged_source_ids.copy()  # Start with test cases already merged in Step 2
        to_keep = set()
        to_merge = {}
        merged_test_cases = {}
        removal_reasons = {}
        skipped_candidates = []
        
        # Add removal reasons for multi-merged test cases
        for source_id in multi_merged_source_ids:
            removal_reasons[source_id] = {
                "reason": "Multi-merged",
                "action": "multi_merged"
            }
        
        print(f"    Processing {len(candidates)} candidates one by one...")
        for idx, candidate in enumerate(candidates, 1):
            test_id = candidate['test_case_id']
            keep_id = candidate.get('keep_id')
            action = candidate.get('action', 'unknown')
            sim = candidate.get('similarity', 0)
            keep_str = f"TC{keep_id}" if keep_id else "N/A"
            print(f"    [{idx}/{len(candidates)}] TC{test_id} → {action.upper()} (sim={sim:.1%}, keep={keep_str})...", end=" ")
            result = self._try_optimize(current_test_cases, candidate, test_cases)
            
            if result["coverage_maintained"]:
                current_test_cases = result["optimized_test_cases"]
                
                if result["action"] == "remove":
                    to_remove.add(candidate["test_case_id"])
                    removal_reasons[candidate["test_case_id"]] = result.get("reason", {})
                    reason_str = result.get("reason", {}).get("reason", "Unknown") if isinstance(result.get("reason"), dict) else str(result.get("reason", "Unknown"))
                    print(f"✓ REMOVED (reason: {reason_str[:50]})")
                elif result["action"] == "merge":
                    merged_id = result.get("merged_id")
                    if merged_id:
                        merged_test_cases[merged_id] = result.get("merged_test_case")
                        to_merge[merged_id] = result.get("source_ids", [])
                        source_ids_str = ", ".join([f"TC{sid}" for sid in result.get("source_ids", [])])
                        print(f"✓ MERGED → TC{merged_id} (from: {source_ids_str})")
                        for source_id in result.get("source_ids", []):
                            to_remove.add(source_id)
                            removal_reasons[source_id] = {
                                "reason": "Merged",
                                "merged_id": merged_id,
                                "action": "merged"
                            }
            else:
                reason = result.get("reason", "Coverage would be lost")
                reason_str = reason if isinstance(reason, str) else reason.get("reason", "Coverage would be lost") if isinstance(reason, dict) else str(reason)
                print(f"✗ SKIPPED (reason: {reason_str[:50]})")
                skipped_candidates.append({
                    "candidate": candidate,
                    "reason": reason
                })
        
        print(f"  [OPTIMIZATION ENGINE] Step 4: Processing exact duplicates (always safe)...")
        duplicate_groups = self.duplicate_detector.detect_duplicates(test_cases)
        exact_count = 0
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
                        if remove_id in current_test_cases:
                            del current_test_cases[remove_id]
                            exact_count += 1
        print(f"    Processed {exact_count} exact duplicates")
        
        
        if ai_recommendations:
            print(f"  [OPTIMIZATION ENGINE] Step 5: Applying AI recommendations...")
            ai_processed = 0
        if ai_recommendations:
            for test_id, recommendation in ai_recommendations.items():
                if test_id in current_test_cases and test_id not in to_remove and test_id not in to_keep:
                    action = recommendation.get("action", "keep")
                    if action == "remove":
                       
                        result = self._try_optimize(
                            current_test_cases,
                            {
                                "test_case_id": test_id,
                                "keep_id": None,
                                "similarity": 0.0,
                                "type": "ai_recommendation",
                                "priority": 2, 
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
                        to_keep.add(test_id)
                        ai_processed += 1
            print(f"    Processed {ai_processed} AI recommendations")
        else:
            print(f"  [OPTIMIZATION ENGINE] Step 5: No AI recommendations (skipped)")
        
        print(f"  [OPTIMIZATION ENGINE] Step 6: Finalizing optimized test cases...")
        all_ids = set(test_cases.keys())
        final_to_keep = all_ids - to_remove
        optimized_test_cases = {tid: current_test_cases[tid] for tid in final_to_keep if tid in current_test_cases}
        optimized_test_cases.update(merged_test_cases)  # Pair-wise merged test cases
        optimized_test_cases.update(multi_merged_test_cases)  # Multi-merged test cases
        total_merged = len(merged_test_cases) + len(multi_merged_test_cases)
        print(f"    Kept: {len(final_to_keep)} test cases")
        print(f"    Removed: {len(to_remove)} test cases")
        print(f"    Merged: {total_merged} new merged test cases ({len(multi_merged_test_cases)} multi-merge, {len(merged_test_cases)} pair-wise)")
        print(f"    Skipped: {len(skipped_candidates)} candidates (coverage would be lost)")
        
        print(f"  [OPTIMIZATION ENGINE] Step 7: Validating final coverage...")
        optimized_coverage = self.coverage_analyzer.calculate_flow_coverage(optimized_test_cases)
        optimized_critical = self.coverage_analyzer.identify_critical_flow_coverage(optimized_test_cases)
     
        step_coverage_loss = self.step_coverage_tracker.check_coverage_loss(test_cases, optimized_test_cases)
        original_step_count = step_coverage_loss["original_step_count"]
        optimized_step_count = step_coverage_loss["optimized_step_count"]
        step_coverage_pct = step_coverage_loss["coverage_percentage_after"]
        
        print(f"    Final flow coverage: {optimized_coverage['coverage_percentage']:.1f}% ({optimized_coverage['covered_flows']}/{optimized_coverage['total_unique_flows']} flows)")
        print(f"    Final step coverage: {step_coverage_pct:.1f}% ({optimized_step_count}/{original_step_count} steps) [vs original]")
        print(f"    Lost steps: {step_coverage_loss['lost_step_count']}")
        print(f"    Critical flows covered: {optimized_critical['all_critical_covered']}")
        
        print(f"  [OPTIMIZATION ENGINE] Step 8: Calculating metrics...")
        original_count = len(test_cases)
        optimized_count = len(optimized_test_cases)
        reduction = original_count - optimized_count
        reduction_percentage = (reduction / original_count * 100) if original_count > 0 else 0
        
        original_time = sum(tc.duration or 0 for tc in test_cases.values())
        optimized_time = sum(tc.duration or 0 for tc in optimized_test_cases.values())
        time_saved = original_time - optimized_time
        time_saved_percentage = (time_saved / original_time * 100) if original_time > 0 else 0
        
        return {
            "original_test_cases": original_count,
            "optimized_test_cases": optimized_count,
            "reduction": reduction,
            "reduction_percentage": reduction_percentage,
            "test_cases_kept": sorted(list(final_to_keep)),
            "test_cases_removed": sorted(list(to_remove)),
            "test_cases_merged": to_merge,
            "merged_test_cases": list(merged_test_cases.keys()),
            "merged_test_cases_dict": merged_test_cases,
            "multi_merged_test_cases_dict": multi_merged_test_cases,  # Include multi-merged test cases 
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
                        "total_unique_steps": original_step_count,
                        "covered_steps": optimized_step_count,
                        "coverage_percentage": step_coverage_pct
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
        
        baseline_coverage = self.coverage_analyzer.calculate_flow_coverage(test_cases)
        baseline_critical = self.coverage_analyzer.identify_critical_flow_coverage(test_cases)
        baseline_step_coverage = self.step_coverage_tracker.calculate_step_coverage(test_cases)
        
        self.step_coverage_tracker.build_step_coverage_map(test_cases)
        
        duplicate_groups = self.duplicate_detector.detect_duplicates(test_cases)
        
       
        to_remove = set()
        to_keep = set()
        to_merge = {}  
        merged_test_cases = {}  
        removal_reasons = {}
        
        
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
        
        
        for group in duplicate_groups["near_duplicates"]:
            keep_id = group["recommended_keep"]
            remove_ids = group["recommended_remove"]
            
            if keep_id not in to_remove:
                for remove_id in remove_ids:
                    if remove_id not in to_keep and remove_id not in to_remove:
                       
                        should_merge = self.test_case_merger.should_merge_instead_of_remove(
                            test_cases[keep_id],
                            test_cases[remove_id]
                        )
                        
                        if should_merge:
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
                                to_keep.add(keep_id)
                                removal_reasons[remove_id] = {
                                    "reason": f"Near duplicate but kept: {removal_check.get('reason', 'Unique steps not covered')}",
                                    "similar_to": keep_id,
                                    "similarity": group["max_similarity"],
                                    "action": "kept"
                                }
       
        for group in duplicate_groups["highly_similar"]:
            keep_id = group["recommended_keep"]
            remove_ids = group["recommended_remove"]
            
            if keep_id not in to_remove:
                
                for remove_id in remove_ids:
                    if remove_id not in to_keep and remove_id not in to_remove:
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
                                to_keep.add(keep_id)
                                removal_reasons[remove_id] = {
                                    "reason": f"Highly similar but kept: {removal_check.get('reason', 'Coverage would be lost')}",
                                    "similar_to": keep_id,
                                    "similarity": group["max_similarity"],
                                    "action": "kept"
                                }
        
       
        if ai_recommendations:
            for test_id, recommendation in ai_recommendations.items():
                if test_id in test_cases and test_id not in to_keep:
                    action = recommendation.get("action", "keep")
                    if action == "remove":
                        # Verify coverage impact with step-level check
                        removal_check = self._should_remove_test_case(
                            test_id,
                            None,  
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
        
       
        all_ids = set(test_cases.keys())
        final_to_keep = all_ids - to_remove
        
        optimized_test_cases = {tid: test_cases[tid] for tid in final_to_keep}
        optimized_test_cases.update(merged_test_cases) 
        optimized_coverage = self.coverage_analyzer.calculate_flow_coverage(optimized_test_cases)
        optimized_critical = self.coverage_analyzer.identify_critical_flow_coverage(optimized_test_cases)
        
        step_coverage_loss_one_pass = self.step_coverage_tracker.check_coverage_loss(test_cases, optimized_test_cases)
        original_step_count_one_pass = step_coverage_loss_one_pass["original_step_count"]
        optimized_step_count_one_pass = step_coverage_loss_one_pass["optimized_step_count"]
        step_coverage_pct_one_pass = step_coverage_loss_one_pass["coverage_percentage_after"]
        
        original_count = len(test_cases)
        optimized_count = len(optimized_test_cases)
        reduction = original_count - optimized_count
        reduction_percentage = (reduction / original_count * 100) if original_count > 0 else 0
        
        original_time = sum(tc.duration or 0 for tc in test_cases.values())
        optimized_time = sum(tc.duration or 0 for tc in optimized_test_cases.values())
        time_saved = original_time - optimized_time
        time_saved_percentage = (time_saved / original_time * 100) if original_time > 0 else 0
       
        step_coverage_loss = step_coverage_loss_one_pass
        
        return {
            "original_test_cases": original_count,
            "optimized_test_cases": optimized_count,
            "reduction": reduction,
            "reduction_percentage": reduction_percentage,
            "test_cases_kept": sorted(list(final_to_keep)),
            "test_cases_removed": sorted(list(to_remove)),
            "test_cases_merged": to_merge, 
            "merged_test_cases": list(merged_test_cases.keys()), 
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
                        "total_unique_steps": original_step_count_one_pass,
                        "covered_steps": optimized_step_count_one_pass,
                        "coverage_percentage": step_coverage_pct_one_pass
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
        
        test_set = {k: v for k, v in test_cases.items() 
                   if k != remove_id and k not in to_remove}
        
        
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
            uniqueness_result = self.step_uniqueness_analyzer.identify_unique_steps(
                test_case_to_remove,
                test_cases[keep_id]
            )
            unique_steps_count = uniqueness_result["unique_in_test_case_1"]["total"]
            
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
        
        # Detect duplicates (AI semantic already done in Phase 2b, skip here for performance)
        duplicate_groups = self.duplicate_detector.detect_duplicates(test_cases, use_ai_semantic=False)
        
        
        for group in duplicate_groups["exact_duplicates"]:
            keep_id = group["recommended_keep"]
            for remove_id in group["recommended_remove"]:
               
                if keep_id in test_cases and remove_id in test_cases:
                    unique_steps = self.step_uniqueness_analyzer.identify_unique_steps(
                        test_cases[remove_id],  
                        test_cases[keep_id]   
                    )
                    
                    unique_in_remove = unique_steps.get("unique_in_test_case_1", {})
                    unique_count = unique_in_remove.get("total", 0) if isinstance(unique_in_remove, dict) else 0
                    
                  
                    if unique_count > 0:
                        action = "merge"
                        priority = 1.5 
                    else:
                        action = "remove"
                        priority = 1  
                else:
                    action = "remove"
                    priority = 1
                
                candidates.append({
                    "test_case_id": remove_id,
                    "keep_id": keep_id,
                    "similarity": group["max_similarity"],
                    "type": "exact_duplicate",
                    "priority": priority,
                    "action": action
                })
        
        # Process near duplicates
        for group in duplicate_groups["near_duplicates"]:
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
                    "type": "near_duplicate",
                    "priority": 2,
                    "action": "merge" if should_merge else "remove"
                })
        
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
                    "priority": 3, 
                    "action": "merge" if should_merge else "remove"
                })
        
        # Enhance candidates with AI recommendations if available
        if ai_recommendations:
            for candidate in candidates:
                test_id = candidate["test_case_id"]
                if test_id in ai_recommendations:
                    ai_rec = ai_recommendations[test_id]
                    
                    if ai_rec.get("action") == "remove":
                        
                        candidate["priority"] = max(0.5, candidate["priority"] - 0.5)
                        candidate["ai_recommendation"] = "remove"
                        candidate["ai_justification"] = ai_rec.get("justification", "")
                    elif ai_rec.get("action") == "keep":
                        
                        candidate["priority"] = candidate["priority"] + 1.0
                        candidate["ai_recommendation"] = "keep"
                    elif ai_rec.get("action") == "merge":
                        if candidate["action"] != "merge":
                            candidate["action"] = "merge"
                        candidate["ai_recommendation"] = "merge"
                        candidate["ai_justification"] = ai_rec.get("justification", "")
        
        
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
            # CRITICAL: Check role and website compatibility before merging
            from optimization.coverage_validator import CoverageValidator
            validator = CoverageValidator()
            safety_check = validator.validate_merge_safety([
                current_test_cases[keep_id],
                current_test_cases[test_case_id]
            ])
            
            if not safety_check["passed"]:
                return {
                    "optimized_test_cases": snapshot,
                    "coverage_maintained": False,
                    "action": "merge",
                    "reason": f"Cannot merge: {', '.join(safety_check['issues'])}"
                }
            
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
        
        CRITICAL: Compares optimized against BASELINE (original test suite), not snapshot.
        This ensures cumulative coverage loss doesn't exceed threshold.
        
        Args:
            original: Original test cases (before this change) - snapshot
            optimized: Optimized test cases (after this change) - new state
            baseline: Baseline test cases (for comparison) - TRUE ORIGINAL
            
        Returns:
            Validation result
        """
        
        baseline_flow = self.coverage_analyzer.calculate_flow_coverage(baseline)
        optimized_flow = self.coverage_analyzer.calculate_flow_coverage(optimized)
        
        flow_maintained = optimized_flow["coverage_percentage"] >= self.min_coverage * 100
        
        
        # For multi-merge, use stricter threshold (98% instead of 95%)
        # This prevents aggressive merges that lose too many steps
        is_multi_merge = len(baseline) - len(optimized) > 2  # More than 2 test cases merged
        # Lowered from 0.98 to 0.97 for multi-merge to allow more merges while maintaining high coverage
        # For large merges, use lower threshold to allow consolidation
        # This allows consolidation of many test cases while still maintaining high coverage
        if is_multi_merge:
            # Check if this is a large merge by counting test cases
            # We can infer this from the difference in test case count
            original_count = len(original)
            optimized_count = len(optimized)
            merged_count = original_count - optimized_count + 1  # Approximate merged test cases
            if merged_count >= 20:
                step_coverage_threshold = 0.94  # Very large merges: 94%
            elif merged_count >= 10:
                step_coverage_threshold = 0.95  # Large merges: 95%
            else:
                step_coverage_threshold = 0.97  # Small merges: 97%
        else:
            step_coverage_threshold = self.min_step_coverage
        
        step_check = self.step_coverage_tracker.validate_step_coverage_maintained(
            baseline, 
            optimized,
            step_coverage_threshold
        )
        
        baseline_critical = self.coverage_analyzer.identify_critical_flow_coverage(baseline)
        optimized_critical = self.coverage_analyzer.identify_critical_flow_coverage(optimized)
        critical_maintained = optimized_critical["all_critical_covered"]
        
        passed = flow_maintained and step_check["is_maintained"] and critical_maintained
        
        reason = ""
        if not flow_maintained:
            reason = f"Flow coverage dropped to {optimized_flow['coverage_percentage']:.1f}% (baseline: {baseline_flow['coverage_percentage']:.1f}%)"
        elif not step_check["is_maintained"]:
            reason = f"Step coverage would drop to {step_check['coverage_percentage']:.1f}% (threshold: {step_check['threshold']:.1f}%) - merge would lose unique steps"
        elif not critical_maintained:
            reason = "Critical flows no longer covered"
        else:
            reason = "Coverage maintained"
        
        return {
            "passed": passed,
            "reason": reason,
            "flow_coverage": {
                "original": baseline_flow["coverage_percentage"],
                "optimized": optimized_flow["coverage_percentage"],
                "maintained": flow_maintained
            },
            "step_coverage": {
                "original": step_check.get("coverage_percentage", 100),
                "optimized": step_check["coverage_percentage"],
                "maintained": step_check["is_maintained"]
            },
            "critical_flows": {
                "original": baseline_critical["all_critical_covered"],
                "optimized": critical_maintained,
                "maintained": critical_maintained
            }
        }
    
    def _create_snapshot(self, test_cases: Dict[int, TestCase]) -> Dict[int, TestCase]:
        """Create snapshot of test cases for rollback."""
        return test_cases.copy()
