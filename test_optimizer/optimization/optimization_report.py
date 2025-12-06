"""
Module for generating optimization reports.
"""

import sys
from pathlib import Path
from typing import Dict, List
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase


class OptimizationReportGenerator:
    """Generates detailed optimization reports."""
    
    def generate_report(
        self,
        optimization_result: Dict,
        original_test_cases: Dict[int, TestCase],
        optimized_test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Generate comprehensive optimization report.
        
        Args:
            optimization_result: Result from optimization_engine
            original_test_cases: Original test cases
            optimized_test_cases: Optimized test cases
            
        Returns:
            Comprehensive report dictionary
        """
        # Extract key metrics
        original_count = optimization_result["original_test_cases"]
        optimized_count = optimization_result["optimized_test_cases"]
        reduction = optimization_result["reduction"]
        reduction_percentage = optimization_result["reduction_percentage"]
        
        # Generate detailed removal list
        removed_test_cases = []
        for test_id in optimization_result["test_cases_removed"]:
            if test_id in original_test_cases:
                tc = original_test_cases[test_id]
                reason = optimization_result["removal_reasons"].get(test_id, {})
                # Handle case where reason might be a string or dict
                if isinstance(reason, str):
                    reason_dict = {"reason": reason}
                elif isinstance(reason, dict):
                    reason_dict = reason
                else:
                    reason_dict = {"reason": "Unknown"}
                
                removed_test_cases.append({
                    "test_case_id": test_id,
                    "name": tc.name,
                    "priority": tc.priority,
                    "duration_ms": tc.duration,
                    "step_count": len(tc.steps),
                    "removal_reason": reason_dict.get("reason", "Unknown"),
                    "similar_to": reason_dict.get("similar_to"),
                    "similarity": reason_dict.get("similarity")
                })
        
        # Generate kept test cases list
        kept_test_cases = []
        for test_id in optimization_result["test_cases_kept"]:
            if test_id in optimized_test_cases:
                tc = optimized_test_cases[test_id]
                kept_test_cases.append({
                    "test_case_id": test_id,
                    "name": tc.name,
                    "priority": tc.priority,
                    "duration_ms": tc.duration,
                    "step_count": len(tc.steps),
                    "pass_count": tc.pass_count,
                    "fail_count": tc.fail_count
                })
        
        # Coverage comparison
        coverage_before = optimization_result["coverage"]["before"]
        coverage_after = optimization_result["coverage"]["after"]
        
        # Time savings
        time_savings = optimization_result["time_savings"]
        
        # Generate summary
        summary = {
            "optimization_successful": True,
            "test_cases_reduced": reduction,
            "reduction_percentage": reduction_percentage,
            "coverage_maintained": coverage_after["coverage_percentage"] >= 90.0,
            "critical_flows_maintained": coverage_after["critical_flows_covered"],
            "time_saved_seconds": time_savings["time_saved_seconds"],
            "time_saved_percentage": time_savings["time_saved_percentage"]
        }
        
        return {
            "summary": summary,
            "metrics": {
                "original": {
                    "test_case_count": original_count,
                    "total_flows": coverage_before["total_flows"],
                    "covered_flows": coverage_before["covered_flows"],
                    "coverage_percentage": coverage_before["coverage_percentage"],
                    "total_duration_ms": time_savings["original_time_ms"],
                    "total_duration_seconds": time_savings["original_time_ms"] / 1000
                },
                "optimized": {
                    "test_case_count": optimized_count,
                    "total_flows": coverage_after["total_flows"],
                    "covered_flows": coverage_after["covered_flows"],
                    "coverage_percentage": coverage_after["coverage_percentage"],
                    "total_duration_ms": time_savings["optimized_time_ms"],
                    "total_duration_seconds": time_savings["optimized_time_ms"] / 1000
                },
                "improvement": {
                    "test_cases_reduced": reduction,
                    "reduction_percentage": reduction_percentage,
                    "coverage_delta": coverage_after["coverage_percentage"] - coverage_before["coverage_percentage"],
                    "time_saved_ms": time_savings["time_saved_ms"],
                    "time_saved_seconds": time_savings["time_saved_seconds"],
                    "time_saved_percentage": time_savings["time_saved_percentage"]
                }
            },
            "test_cases_removed": removed_test_cases,
            "test_cases_kept": kept_test_cases,
            "coverage_analysis": {
                "before": coverage_before,
                "after": coverage_after,
                "coverage_maintained": coverage_after["coverage_percentage"] >= coverage_before["coverage_percentage"] * 0.90
            },
            "time_analysis": time_savings,
            "duplicate_analysis": {
                "exact_duplicates": len(optimization_result["duplicate_groups"]["exact_duplicates"]),
                "near_duplicates": len(optimization_result["duplicate_groups"]["near_duplicates"]),
                "highly_similar": len(optimization_result["duplicate_groups"]["highly_similar"])
            }
        }
    
    def generate_human_readable_report(
        self,
        report: Dict
    ) -> str:
        """
        Generate human-readable text report.
        
        Args:
            report: Report dictionary from generate_report
            
        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("TEST SUITE OPTIMIZATION REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Summary
        summary = report["summary"]
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Optimization Status: {'✓ SUCCESS' if summary['optimization_successful'] else '✗ FAILED'}")
        lines.append(f"Test Cases Reduced: {summary['test_cases_reduced']} ({summary['reduction_percentage']:.1f}%)")
        lines.append(f"Coverage Maintained: {'✓ Yes' if summary['coverage_maintained'] else '✗ No'}")
        lines.append(f"Critical Flows Maintained: {'✓ Yes' if summary['critical_flows_maintained'] else '✗ No'}")
        lines.append(f"Time Saved: {summary['time_saved_seconds']:.1f} seconds ({summary['time_saved_percentage']:.1f}%)")
        lines.append("")
        
        # Metrics
        metrics = report["metrics"]
        lines.append("METRICS COMPARISON")
        lines.append("-" * 80)
        lines.append(f"Original Test Cases: {metrics['original']['test_case_count']}")
        lines.append(f"Optimized Test Cases: {metrics['optimized']['test_case_count']}")
        lines.append(f"Reduction: {metrics['improvement']['test_cases_reduced']} ({metrics['improvement']['reduction_percentage']:.1f}%)")
        lines.append("")
        lines.append(f"Original Coverage: {metrics['original']['coverage_percentage']:.1f}%")
        lines.append(f"Optimized Coverage: {metrics['optimized']['coverage_percentage']:.1f}%")
        lines.append(f"Coverage Delta: {metrics['improvement']['coverage_delta']:+.1f}%")
        lines.append("")
        lines.append(f"Original Duration: {metrics['original']['total_duration_seconds']:.1f} seconds")
        lines.append(f"Optimized Duration: {metrics['optimized']['total_duration_seconds']:.1f} seconds")
        lines.append(f"Time Saved: {metrics['improvement']['time_saved_seconds']:.1f} seconds ({metrics['improvement']['time_saved_percentage']:.1f}%)")
        lines.append("")
        
        # Removed test cases
        removed = report["test_cases_removed"]
        if removed:
            lines.append("REMOVED TEST CASES")
            lines.append("-" * 80)
            for tc in removed[:10]:  # Show first 10
                lines.append(f"  Test Case {tc['test_case_id']}: {tc['name']}")
                lines.append(f"    Reason: {tc['removal_reason']}")
                if tc.get('similar_to'):
                    lines.append(f"    Similar to: Test Case {tc['similar_to']}")
                if tc.get('similarity'):
                    lines.append(f"    Similarity: {tc['similarity']:.1%}")
            if len(removed) > 10:
                lines.append(f"  ... and {len(removed) - 10} more test cases")
            lines.append("")
        
        # Kept test cases summary
        kept = report["test_cases_kept"]
        lines.append("KEPT TEST CASES")
        lines.append("-" * 80)
        lines.append(f"Total: {len(kept)} test cases")
        lines.append("")
        
        # Duplicate analysis
        dup_analysis = report["duplicate_analysis"]
        lines.append("DUPLICATE ANALYSIS")
        lines.append("-" * 80)
        lines.append(f"Exact Duplicates Found: {dup_analysis['exact_duplicates']}")
        lines.append(f"Near Duplicates Found: {dup_analysis['near_duplicates']}")
        lines.append(f"Highly Similar Found: {dup_analysis['highly_similar']}")
        lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def generate_json_report(
        self,
        report: Dict,
        output_path: str
    ):
        """
        Generate JSON report file.
        
        Args:
            report: Report dictionary
            output_path: Path to output JSON file
        """
        import json
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

