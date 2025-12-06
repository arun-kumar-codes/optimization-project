"""
Module for scheduling test case execution order.
"""

import sys
from pathlib import Path
from typing import Dict, List
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from execution.dependency_analyzer import DependencyAnalyzer
from execution.priority_calculator import PriorityCalculator
from flows.flow_classifier import FlowClassifier


class ExecutionScheduler:
    """Schedules test case execution order."""
    
    def __init__(self):
        self.dependency_analyzer = DependencyAnalyzer()
        self.priority_calculator = PriorityCalculator()
        self.flow_classifier = FlowClassifier()
    
    def schedule_execution(
        self,
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Generate execution schedule for test cases.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Execution schedule dictionary
        """
        # Analyze dependencies
        dependency_analysis = self.dependency_analyzer.analyze_dependencies(test_cases)
        
        # Calculate priorities
        priorities = self.priority_calculator.calculate_priorities(test_cases)
        priority_categories = self.priority_calculator.categorize_priorities(priorities)
        
        # Classify by flow
        flow_classifications = self.flow_classifier.classify_all_test_cases(test_cases)
        
        # Generate execution order
        execution_order = self._generate_execution_order(
            test_cases,
            dependency_analysis,
            priorities,
            priority_categories
        )
        
        # Group for parallel execution
        parallel_groups = self._identify_parallel_groups(
            test_cases,
            dependency_analysis,
            execution_order
        )
        
        # Calculate estimated times
        estimated_times = self._calculate_estimated_times(test_cases, execution_order)
        
        return {
            "execution_order": execution_order,
            "parallel_groups": parallel_groups,
            "priorities": priorities,
            "priority_categories": priority_categories,
            "estimated_times": estimated_times,
            "dependency_analysis": dependency_analysis,
            "flow_classifications": flow_classifications
        }
    
    def _generate_execution_order(
        self,
        test_cases: Dict[int, TestCase],
        dependency_analysis: Dict,
        priorities: Dict[int, float],
        priority_categories: Dict[str, List[int]]
    ) -> List[int]:
        """
        Generate execution order respecting dependencies and priorities.
        
        Args:
            test_cases: All test cases
            dependency_analysis: Dependency analysis result
            priorities: Priority scores
            priority_categories: Priority categories
            
        Returns:
            Ordered list of test case IDs
        """
        # Start with dependency-based order
        dependency_order = self.dependency_analyzer.get_execution_order(
            dependency_analysis["dependencies"]
        )
        
        # Reorder within dependency constraints by priority
        execution_order = []
        remaining = set(dependency_order)
        
        # Process by priority category
        for category in ["smoke", "high", "medium", "low"]:
            category_tests = priority_categories[category]
            
            # Filter to tests that are ready (dependencies satisfied)
            ready_tests = []
            for test_id in category_tests:
                if test_id in remaining:
                    deps = dependency_analysis["dependencies"].get(test_id, [])
                    if all(dep in execution_order for dep in deps):
                        ready_tests.append(test_id)
            
            # Sort by priority score (highest first)
            ready_tests.sort(key=lambda tid: priorities[tid], reverse=True)
            execution_order.extend(ready_tests)
            remaining -= set(ready_tests)
        
        # Add any remaining tests
        remaining_list = [tid for tid in dependency_order if tid in remaining]
        execution_order.extend(remaining_list)
        
        return execution_order
    
    def _identify_parallel_groups(
        self,
        test_cases: Dict[int, TestCase],
        dependency_analysis: Dict,
        execution_order: List[int]
    ) -> List[List[int]]:
        """
        Identify groups of test cases that can run in parallel.
        
        Args:
            test_cases: All test cases
            dependency_analysis: Dependency analysis
            execution_order: Execution order
            
        Returns:
            List of groups, each group can run in parallel
        """
        parallel_groups = []
        processed = set()
        
        # Group by dependency level
        dependency_levels = {}
        for test_id in execution_order:
            deps = dependency_analysis["dependencies"].get(test_id, [])
            if not deps:
                level = 0
            else:
                level = max(dependency_levels.get(dep, 0) for dep in deps) + 1
            dependency_levels[test_id] = level
        
        # Group tests at the same dependency level
        max_level = max(dependency_levels.values()) if dependency_levels else 0
        
        for level in range(max_level + 1):
            level_tests = [tid for tid, lvl in dependency_levels.items() if lvl == level]
            if level_tests:
                # Further group by flow type to avoid conflicts
                flow_groups = {}
                for test_id in level_tests:
                    flows = self.flow_classifier.classify_test_case(test_cases[test_id])
                    primary_flow = flows["primary_flow"]
                    if primary_flow not in flow_groups:
                        flow_groups[primary_flow] = []
                    flow_groups[primary_flow].append(test_id)
                
                # Each flow group can potentially run in parallel
                for flow, group in flow_groups.items():
                    if len(group) > 1:
                        parallel_groups.append(group)
                    else:
                        parallel_groups.append(group)
        
        return parallel_groups
    
    def _calculate_estimated_times(
        self,
        test_cases: Dict[int, TestCase],
        execution_order: List[int]
    ) -> Dict:
        """
        Calculate estimated execution times.
        
        Args:
            test_cases: All test cases
            execution_order: Execution order
            
        Returns:
            Time estimates dictionary
        """
        total_time = 0
        cumulative_times = {}
        
        for test_id in execution_order:
            if test_id in test_cases:
                duration = test_cases[test_id].duration or 0
                total_time += duration
                cumulative_times[test_id] = {
                    "test_case_id": test_id,
                    "duration_ms": duration,
                    "duration_seconds": duration / 1000,
                    "cumulative_time_ms": total_time,
                    "cumulative_time_seconds": total_time / 1000
                }
        
        return {
            "total_time_ms": total_time,
            "total_time_seconds": total_time / 1000,
            "total_time_minutes": total_time / 60000,
            "per_test_case": cumulative_times
        }
    
    def get_checkpoint_recommendations(
        self,
        execution_order: List[int],
        estimated_times: Dict,
        checkpoint_interval_seconds: int = 300
    ) -> List[Dict]:
        """
        Get checkpoint recommendations (where to stop if failures occur).
        
        Args:
            execution_order: Execution order
            estimated_times: Time estimates
            checkpoint_interval_seconds: Interval for checkpoints in seconds
            
        Returns:
            List of checkpoint recommendations
        """
        checkpoints = []
        per_test = estimated_times.get("per_test_case", {})
        interval_ms = checkpoint_interval_seconds * 1000
        
        cumulative = 0
        for test_id in execution_order:
            if test_id in per_test:
                test_info = per_test[test_id]
                cumulative = test_info["cumulative_time_ms"]
                
                # Check if we've passed a checkpoint interval
                checkpoint_count = int(cumulative / interval_ms)
                if checkpoint_count > len(checkpoints):
                    checkpoints.append({
                        "test_case_id": test_id,
                        "position": execution_order.index(test_id) + 1,
                        "cumulative_time_seconds": cumulative / 1000,
                        "reason": f"Checkpoint after {checkpoint_count * checkpoint_interval_seconds} seconds"
                    })
        
        return checkpoints


