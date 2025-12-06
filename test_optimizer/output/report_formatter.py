"""
Module for formatting human-readable reports.
"""

import sys
from pathlib import Path
from typing import Dict
sys.path.insert(0, str(Path(__file__).parent.parent))


class ReportFormatter:
    """Formats reports in human-readable formats."""
    
    def format_optimization_report(
        self,
        optimization_report: Dict
    ) -> str:
        """
        Format optimization report as markdown.
        
        Args:
            optimization_report: Report dictionary
            
        Returns:
            Markdown formatted report
        """
        lines = []
        lines.append("# Test Suite Optimization Report")
        lines.append("")
        
        summary = optimization_report.get("summary", {})
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Status**: {'✓ SUCCESS' if summary.get('optimization_successful') else '✗ FAILED'}")
        lines.append(f"- **Test Cases Reduced**: {summary.get('test_cases_reduced', 0)} ({summary.get('reduction_percentage', 0):.1f}%)")
        lines.append(f"- **Coverage Maintained**: {'✓ Yes' if summary.get('coverage_maintained') else '✗ No'}")
        lines.append(f"- **Time Saved**: {summary.get('time_saved_seconds', 0):.1f} seconds ({summary.get('time_saved_percentage', 0):.1f}%)")
        lines.append("")
        
        # Metrics
        metrics = optimization_report.get("metrics", {})
        lines.append("## Metrics Comparison")
        lines.append("")
        lines.append("| Metric | Original | Optimized | Improvement |")
        lines.append("|--------|----------|-----------|-------------|")
        lines.append(f"| Test Cases | {metrics.get('original', {}).get('test_case_count', 0)} | {metrics.get('optimized', {}).get('test_case_count', 0)} | {metrics.get('improvement', {}).get('reduction_percentage', 0):.1f}% reduction |")
        lines.append(f"| Coverage | {metrics.get('original', {}).get('coverage_percentage', 0):.1f}% | {metrics.get('optimized', {}).get('coverage_percentage', 0):.1f}% | {metrics.get('improvement', {}).get('coverage_delta', 0):+.1f}% |")
        lines.append(f"| Duration | {metrics.get('original', {}).get('total_duration_seconds', 0):.1f}s | {metrics.get('optimized', {}).get('total_duration_seconds', 0):.1f}s | {metrics.get('improvement', {}).get('time_saved_seconds', 0):.1f}s saved |")
        lines.append("")
        
        return "\n".join(lines)
    
    def format_execution_plan(
        self,
        execution_plan: Dict
    ) -> str:
        """
        Format execution plan as markdown.
        
        Args:
            execution_plan: Execution plan dictionary
            
        Returns:
            Markdown formatted plan
        """
        lines = []
        lines.append("# Test Execution Plan")
        lines.append("")
        
        summary = execution_plan.get("summary", {})
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Test Cases**: {summary.get('total_test_cases', 0)}")
        lines.append(f"- **Estimated Time**: {summary.get('total_execution_time_minutes', 0):.1f} minutes")
        lines.append(f"- **Smoke Tests**: {summary.get('smoke_tests', 0)}")
        lines.append(f"- **High Priority**: {summary.get('high_priority_tests', 0)}")
        lines.append(f"- **Parallel Groups**: {summary.get('parallel_groups_count', 0)}")
        lines.append("")
        
        # Execution order
        lines.append("## Execution Order")
        lines.append("")
        execution_order = execution_plan.get("execution_order", [])
        for i, test_id in enumerate(execution_order[:20], 1):
            priority = execution_plan.get("priorities", {}).get(test_id, 0)
            lines.append(f"{i}. Test Case {test_id} (Priority: {priority:.1f})")
        
        if len(execution_order) > 20:
            lines.append(f"... and {len(execution_order) - 20} more")
        lines.append("")
        
        return "\n".join(lines)


