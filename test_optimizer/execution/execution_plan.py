"""
Module for generating comprehensive execution plans.
"""

import sys
from pathlib import Path
from typing import Dict, List
import json
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from execution.execution_scheduler import ExecutionScheduler


class ExecutionPlanGenerator:
    """Generates comprehensive execution plans."""
    
    def __init__(self):
        self.scheduler = ExecutionScheduler()
    
    def generate_execution_plan(
        self,
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Generate comprehensive execution plan.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Comprehensive execution plan
        """
        # Get execution schedule
        schedule = self.scheduler.schedule_execution(test_cases)
        
        # Get checkpoint recommendations
        checkpoints = self.scheduler.get_checkpoint_recommendations(
            schedule["execution_order"],
            schedule["estimated_times"]
        )
        
        # Identify rollback points (critical state changes)
        rollback_points = self._identify_rollback_points(
            test_cases,
            schedule["execution_order"]
        )
        
        # Generate plan by priority category
        plan_by_category = self._organize_by_category(
            test_cases,
            schedule
        )
        
        return {
            "execution_order": schedule["execution_order"],
            "parallel_groups": schedule["parallel_groups"],
            "priorities": schedule["priorities"],
            "priority_categories": schedule["priority_categories"],
            "estimated_times": schedule["estimated_times"],
            "checkpoints": checkpoints,
            "rollback_points": rollback_points,
            "plan_by_category": plan_by_category,
            "summary": {
                "total_test_cases": len(test_cases),
                "total_execution_time_seconds": schedule["estimated_times"]["total_time_seconds"],
                "total_execution_time_minutes": schedule["estimated_times"]["total_time_minutes"],
                "smoke_tests": len(schedule["priority_categories"]["smoke"]),
                "high_priority_tests": len(schedule["priority_categories"]["high"]),
                "medium_priority_tests": len(schedule["priority_categories"]["medium"]),
                "low_priority_tests": len(schedule["priority_categories"]["low"]),
                "parallel_groups_count": len(schedule["parallel_groups"])
            }
        }
    
    def _identify_rollback_points(
        self,
        test_cases: Dict[int, TestCase],
        execution_order: List[int]
    ) -> List[Dict]:
        """
        Identify rollback points (critical state changes).
        
        Args:
            test_cases: All test cases
            execution_order: Execution order
            
        Returns:
            List of rollback points
        """
        rollback_points = []
        
        from flows.flow_analyzer import FlowAnalyzer
        flow_analyzer = FlowAnalyzer()
        
        for i, test_id in enumerate(execution_order):
            if test_id in test_cases:
                test_case = test_cases[test_id]
                flows = flow_analyzer.identify_flow_type(test_case)
                
                # Check for critical state changes
                if "crud" in flows and any("delete" in step.action.lower() or "remove" in step.action.lower() 
                                          for step in test_case.steps):
                    rollback_points.append({
                        "test_case_id": test_id,
                        "position": i + 1,
                        "type": "data_deletion",
                        "description": f"Test case {test_id} performs data deletion - rollback recommended before this point",
                        "criticality": "High"
                    })
                elif "crud" in flows and any("create" in step.action.lower() or "add" in step.action.lower() 
                                            for step in test_case.steps):
                    rollback_points.append({
                        "test_case_id": test_id,
                        "position": i + 1,
                        "type": "data_creation",
                        "description": f"Test case {test_id} creates new data - consider rollback point",
                        "criticality": "Medium"
                    })
        
        return rollback_points
    
    def _organize_by_category(
        self,
        test_cases: Dict[int, TestCase],
        schedule: Dict
    ) -> Dict:
        """
        Organize execution plan by priority category.
        
        Args:
            test_cases: All test cases
            schedule: Execution schedule
            
        Returns:
            Organized plan by category
        """
        plan_by_category = {}
        
        for category in ["smoke", "high", "medium", "low"]:
            category_tests = schedule["priority_categories"][category]
            plan_by_category[category] = {
                "test_case_ids": category_tests,
                "test_cases": [
                    {
                        "id": tid,
                        "name": test_cases[tid].name if tid in test_cases else "Unknown",
                        "priority_score": schedule["priorities"].get(tid, 0),
                        "duration_seconds": (test_cases[tid].duration or 0) / 1000 if tid in test_cases else 0
                    }
                    for tid in category_tests
                ],
                "total_count": len(category_tests),
                "estimated_time_seconds": sum(
                    (test_cases[tid].duration or 0) / 1000 
                    for tid in category_tests if tid in test_cases
                )
            }
        
        return plan_by_category
    
    def export_execution_plan(
        self,
        plan: Dict,
        output_path: str
    ):
        """
        Export execution plan to JSON file.
        
        Args:
            plan: Execution plan dictionary
            output_path: Path to output JSON file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2, default=str)
    
    def generate_human_readable_plan(
        self,
        plan: Dict
    ) -> str:
        """
        Generate human-readable execution plan.
        
        Args:
            plan: Execution plan dictionary
            
        Returns:
            Formatted text plan
        """
        lines = []
        lines.append("=" * 80)
        lines.append("TEST EXECUTION PLAN")
        lines.append("=" * 80)
        lines.append("")
        
        # Summary
        summary = plan["summary"]
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total Test Cases: {summary['total_test_cases']}")
        lines.append(f"Estimated Execution Time: {summary['total_execution_time_minutes']:.1f} minutes")
        lines.append(f"Smoke Tests: {summary['smoke_tests']}")
        lines.append(f"High Priority: {summary['high_priority_tests']}")
        lines.append(f"Medium Priority: {summary['medium_priority_tests']}")
        lines.append(f"Low Priority: {summary['low_priority_tests']}")
        lines.append(f"Parallel Groups: {summary['parallel_groups_count']}")
        lines.append("")
        
        # Execution order
        lines.append("EXECUTION ORDER")
        lines.append("-" * 80)
        for i, test_id in enumerate(plan["execution_order"][:20], 1):
            priority = plan["priorities"].get(test_id, 0)
            lines.append(f"{i:3d}. Test Case {test_id:3d} (Priority: {priority:.1f})")
        if len(plan["execution_order"]) > 20:
            lines.append(f"... and {len(plan['execution_order']) - 20} more test cases")
        lines.append("")
        
        # Checkpoints
        if plan["checkpoints"]:
            lines.append("CHECKPOINTS")
            lines.append("-" * 80)
            for checkpoint in plan["checkpoints"][:5]:
                lines.append(f"  Position {checkpoint['position']}: Test Case {checkpoint['test_case_id']}")
                lines.append(f"    Time: {checkpoint['cumulative_time_seconds']:.1f} seconds")
                lines.append(f"    Reason: {checkpoint['reason']}")
            lines.append("")
        
        # Rollback points
        if plan["rollback_points"]:
            lines.append("ROLLBACK POINTS")
            lines.append("-" * 80)
            for rollback in plan["rollback_points"][:5]:
                lines.append(f"  Position {rollback['position']}: Test Case {rollback['test_case_id']}")
                lines.append(f"    Type: {rollback['type']}")
                lines.append(f"    Criticality: {rollback['criticality']}")
            lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)


