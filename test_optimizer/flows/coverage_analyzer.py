"""
Module for analyzing flow coverage from test cases.
"""

from typing import Dict, List, Set
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from flows.flow_analyzer import FlowAnalyzer
from flows.flow_graph import FlowGraphBuilder


class CoverageAnalyzer:
    """Analyzes flow coverage from test cases."""
    
    def __init__(self):
        self.flow_analyzer = FlowAnalyzer()
        self.graph_builder = FlowGraphBuilder()
    
    def calculate_flow_coverage(
        self, 
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Calculate flow coverage metrics.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Coverage metrics dictionary
        """
        # Identify all unique flows
        all_flows = set()
        test_case_flows = {}
        
        for test_id, test_case in test_cases.items():
            flows = self.flow_analyzer.identify_flow_type(test_case)
            test_case_flows[test_id] = flows
            all_flows.update(flows)
        
        # Calculate coverage
        covered_flows = set()
        for flows in test_case_flows.values():
            covered_flows.update(flows)
        
        coverage_percentage = (len(covered_flows) / len(all_flows) * 100) if all_flows else 0.0
        
        return {
            "total_unique_flows": len(all_flows),
            "covered_flows": len(covered_flows),
            "uncovered_flows": len(all_flows - covered_flows),
            "coverage_percentage": coverage_percentage,
            "all_flows": sorted(list(all_flows)),
            "covered_flows_list": sorted(list(covered_flows)),
            "uncovered_flows_list": sorted(list(all_flows - covered_flows))
        }
    
    def create_coverage_matrix(
        self, 
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Create a coverage matrix (test case × flow).
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Coverage matrix dictionary
        """
        # Get all flows
        all_flows = set()
        for test_case in test_cases.values():
            flows = self.flow_analyzer.identify_flow_type(test_case)
            all_flows.update(flows)
        
        all_flows = sorted(list(all_flows))
        
        # Build matrix
        matrix = {}
        for test_id, test_case in test_cases.items():
            flows = self.flow_analyzer.identify_flow_type(test_case)
            matrix[test_id] = {
                flow: (1 if flow in flows else 0) for flow in all_flows
            }
        
        return {
            "flows": all_flows,
            "test_cases": sorted(test_cases.keys()),
            "matrix": matrix
        }
    
    def identify_critical_flow_coverage(
        self, 
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Identify coverage of critical flows.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Critical flow coverage dictionary
        """
        critical_flows = ["authentication", "navigation", "crud"]
        
        critical_flow_coverage = {}
        for flow in critical_flows:
            covering_test_cases = [
                test_id for test_id, test_case in test_cases.items()
                if flow in self.flow_analyzer.identify_flow_type(test_case)
            ]
            
            critical_flow_coverage[flow] = {
                "covered": len(covering_test_cases) > 0,
                "test_case_count": len(covering_test_cases),
                "test_case_ids": covering_test_cases
            }
        
        return {
            "critical_flows": critical_flows,
            "coverage": critical_flow_coverage,
            "all_critical_covered": all(
                critical_flow_coverage[flow]["covered"] 
                for flow in critical_flows
            )
        }
    
    def find_coverage_gaps(
        self, 
        test_cases: Dict[int, TestCase]
    ) -> List[Dict]:
        """
        Find gaps in flow coverage.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            List of coverage gap dictionaries
        """
        gaps = []
        
        # Build flow graph
        graph = self.graph_builder.build_graph(test_cases)
        
        # Find isolated pages (not covered by any test case)
        isolated = self.graph_builder.find_isolated_pages(graph)
        if isolated:
            gaps.append({
                "type": "isolated_pages",
                "description": "Pages that are not connected to any flow",
                "pages": isolated,
                "severity": "medium"
            })
        
        # Find dead ends
        dead_ends = self.graph_builder.find_dead_ends(graph)
        if dead_ends:
            gaps.append({
                "type": "dead_ends",
                "description": "Pages with no outgoing transitions",
                "pages": dead_ends,
                "severity": "low"
            })
        
        # Check for missing critical flows
        critical_coverage = self.identify_critical_flow_coverage(test_cases)
        for flow, coverage_info in critical_coverage["coverage"].items():
            if not coverage_info["covered"]:
                gaps.append({
                    "type": "missing_critical_flow",
                    "description": f"Missing coverage for critical flow: {flow}",
                    "flow_type": flow,
                    "severity": "high"
                })
        
        return gaps
    
    def calculate_test_case_coverage_score(
        self, 
        test_case: TestCase
    ) -> float:
        """
        Calculate a coverage score for a single test case.
        
        Args:
            test_case: The TestCase object
            
        Returns:
            Coverage score from 0.0 to 1.0
        """
        score = 0.0
        
        # Number of flows covered
        flows = self.flow_analyzer.identify_flow_type(test_case)
        flow_score = min(len(flows) / 5.0, 1.0)  # Normalize to 0-1, cap at 5 flows
        score += flow_score * 0.4
        
        # Number of steps (more comprehensive = better)
        step_count = len(test_case.steps)
        step_score = min(step_count / 30.0, 1.0)  # Normalize to 0-1, cap at 30 steps
        score += step_score * 0.3
        
        # Page transitions (more transitions = more coverage)
        transitions = self.flow_analyzer.extract_page_transitions(test_case)
        transition_score = min(len(transitions) / 10.0, 1.0)  # Normalize to 0-1, cap at 10 transitions
        score += transition_score * 0.3
        
        return min(1.0, score)
    
    def generate_coverage_report(
        self, 
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Generate a comprehensive coverage report.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Comprehensive coverage report
        """
        # Basic flow coverage
        flow_coverage = self.calculate_flow_coverage(test_cases)
        
        # Critical flow coverage
        critical_coverage = self.identify_critical_flow_coverage(test_cases)
        
        # Coverage matrix
        coverage_matrix = self.create_coverage_matrix(test_cases)
        
        # Coverage gaps
        gaps = self.find_coverage_gaps(test_cases)
        
        # Test case coverage scores
        test_case_scores = {
            test_id: self.calculate_test_case_coverage_score(test_case)
            for test_id, test_case in test_cases.items()
        }
        
        return {
            "flow_coverage": flow_coverage,
            "critical_flow_coverage": critical_coverage,
            "coverage_matrix": coverage_matrix,
            "coverage_gaps": gaps,
            "test_case_coverage_scores": test_case_scores,
            "summary": {
                "total_test_cases": len(test_cases),
                "total_flows": flow_coverage["total_unique_flows"],
                "covered_flows": flow_coverage["covered_flows"],
                "coverage_percentage": flow_coverage["coverage_percentage"],
                "all_critical_covered": critical_coverage["all_critical_covered"],
                "total_gaps": len(gaps)
            }
        }

