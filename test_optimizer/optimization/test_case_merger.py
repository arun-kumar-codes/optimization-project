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
        
        print(f"      [MERGER] Merging {len(test_cases)} test cases using prefix/suffix strategy...")
        source_ids = [tc.id for tc in test_cases]
        print(f"      [MERGER] Source test cases: {source_ids}")
        
        merge_points = self.prefix_analyzer.find_merge_points(test_cases)
        
        prefix_steps = merge_points["prefix"]
        unique_middles = merge_points["unique_middles"]
        suffix_steps = merge_points["suffix"]
        
        print(f"      [MERGER] Common prefix: {len(prefix_steps)} steps ({merge_points['prefix_actions']})")
        print(f"      [MERGER] Unique middle sections: {len(unique_middles)}")
        print(f"      [MERGER] Common suffix: {len(suffix_steps)} steps ({merge_points['suffix_actions']})")
        
        merged_steps = []
        position = 1
        
        for step in prefix_steps:
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
            position += 1
        
        seen_middle_signatures = set()
        for middle in unique_middles:
            middle_steps = middle["steps"]
            middle_sig = "->".join(middle["action_sequence"])
            
            if middle_sig not in seen_middle_signatures:
                for step in middle_steps:
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
                    position += 1
                seen_middle_signatures.add(middle_sig)
        
        # Add common suffix
        for step in suffix_steps:
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
            position += 1
        
        print(f"      [MERGER] Merged to {len(merged_steps)} steps (from {sum(len(tc.steps) for tc in test_cases)} total)")
        
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
            f"\n\nPreserves all unique steps using prefix/suffix strategy."
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
                "merge_strategy": "prefix_suffix",
                "prefix_length": len(prefix_steps),
                "suffix_length": len(suffix_steps),
                "unique_middle_count": len(unique_middles)
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
        
        def get_step_signature(step: TestStep) -> str:
            """Create signature for step comparison."""
            action = step.action_name or ""
            element = step.element or ""
            desc = step.description or ""
            return f"{action}|{element}|{desc}".lower()
        
        # Add steps from first test case
        position = 1
        for step in steps1:
            sig = get_step_signature(step)
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
            sig = get_step_signature(step)
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
