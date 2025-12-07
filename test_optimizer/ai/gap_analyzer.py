"""
Module for AI-powered gap analysis in test coverage.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from ai.claude_client import ClaudeClient


class GapAnalyzer:
    """Identifies gaps in test coverage using AI."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize gap analyzer.
        
        Args:
            api_key: Claude API key (optional)
        """
        self.claude_client = ClaudeClient(api_key)
        self.system_prompt = """You are an expert test coverage analyst.
Analyze test suites to identify missing user flows, gaps in coverage, and suggest improvements.
Focus on critical business flows and edge cases."""
    
    def identify_coverage_gaps(
        self, 
        test_cases: Dict[int, TestCase],
        flow_coverage: Dict,
        critical_flows: List[str]
    ) -> Dict:
        """
        Identify coverage gaps in the test suite.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            flow_coverage: Flow coverage information from Phase 3
            critical_flows: List of critical flow types
            
        Returns:
            Gap analysis dictionary
        """
        test_cases_summary = self._prepare_test_cases_summary(test_cases)
        
        flows_covered = flow_coverage.get("all_flows", [])
        flows_covered_str = ", ".join(flows_covered) if flows_covered else "None"
        critical_flows_str = ", ".join(critical_flows) if critical_flows else "None"
        
        prompt = self.claude_client.create_prompt_template(
            "gap_analysis",
            test_cases_summary=test_cases_summary,
            flows_covered=flows_covered_str,
            critical_flows=critical_flows_str
        )
        
        ai_response = self.claude_client.analyze(prompt, self.system_prompt)
        
        gaps = self._parse_gap_analysis(ai_response)
        
        return {
            "identified_gaps": gaps,
            "raw_response": ai_response,
            "summary": self._generate_gap_summary(gaps)
        }
    
    def _prepare_test_cases_summary(self, test_cases: Dict[int, TestCase]) -> str:
        """Prepare a summary of test cases for AI analysis."""
        summary_lines = []
        
        from flows.flow_analyzer import FlowAnalyzer
        flow_analyzer = FlowAnalyzer()
        
        flow_groups = {}
        for test_id, test_case in test_cases.items():
            flows = flow_analyzer.identify_flow_type(test_case)
            for flow in flows:
                if flow not in flow_groups:
                    flow_groups[flow] = []
                flow_groups[flow].append(f"TC{test_id}: {test_case.name}")
        
        for flow_type, test_list in flow_groups.items():
            summary_lines.append(f"{flow_type.upper()}: {len(test_list)} test cases")
            summary_lines.append(f"  Examples: {', '.join(test_list[:5])}")
            if len(test_list) > 5:
                summary_lines.append(f"  ... and {len(test_list) - 5} more")
        
        return "\n".join(summary_lines)
    
    def _parse_gap_analysis(self, response: str) -> List[Dict]:
        """Parse AI gap analysis response."""
        gaps = []
        lines = response.split("\n")
        
        current_gap = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line[0].isdigit() or line.startswith("-") or line.startswith("*"):
                if current_gap:
                    gaps.append(current_gap)
                
                gap_text = line.lstrip("0123456789.-* ").strip()
                current_gap = {
                    "type": "missing_flow",
                    "description": gap_text,
                    "severity": "Medium"
                }
            elif current_gap:
                if ":" in line:
                    parts = line.split(":", 1)
                    key = parts[0].strip().lower()
                    value = parts[1].strip()
                    
                    if "severity" in key or "priority" in key:
                        current_gap["severity"] = value
                    elif "type" in key or "category" in key:
                        current_gap["type"] = value
                    else:
                        current_gap["description"] += f" {value}"
                else:
                    current_gap["description"] += f" {line}"
        
        if current_gap:
            gaps.append(current_gap)
        
        if not gaps:
            gaps.append({
                "type": "general",
                "description": response[:500], 
                "severity": "Medium"
            })
        
        return gaps
    
    def _generate_gap_summary(self, gaps: List[Dict]) -> Dict:
        """Generate summary of identified gaps."""
        severity_counts = {"High": 0, "Medium": 0, "Low": 0}
        type_counts = {}
        
        for gap in gaps:
            severity = gap.get("severity", "Medium")
            gap_type = gap.get("type", "general")
            
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            type_counts[gap_type] = type_counts.get(gap_type, 0) + 1
        
        return {
            "total_gaps": len(gaps),
            "severity_distribution": severity_counts,
            "type_distribution": type_counts
        }
    
    def suggest_new_test_cases(
        self, 
        gaps: List[Dict],
        existing_test_cases: Dict[int, TestCase]
    ) -> List[Dict]:
        """
        Suggest new test cases to fill coverage gaps.
        
        Args:
            gaps: List of identified gaps
            existing_test_cases: Existing test cases
            
        Returns:
            List of suggested test cases
        """
        suggestions = []
        
        high_severity_gaps = [g for g in gaps if g.get("severity") == "High"]
        
        for gap in high_severity_gaps[:5]: 
            suggestion = {
                "suggested_name": self._generate_test_case_name(gap),
                "description": gap.get("description", ""),
                "priority": "High" if gap.get("severity") == "High" else "Medium",
                "flow_type": gap.get("type", "general"),
                "reason": f"Fills gap: {gap.get('description', '')[:100]}"
            }
            suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_test_case_name(self, gap: Dict) -> str:
        description = gap.get("description", "")
        gap_type = gap.get("type", "general")
        
        # Try to extract key words
        words = description.split()[:5]
        name = " ".join(words).title()
        
        if not name or len(name) < 10:
            name = f"Test {gap_type.replace('_', ' ').title()}"
        
        return name
    
    def suggest_test_case_modifications(
        self, 
        test_case: TestCase,
        gap_context: Dict
    ) -> Dict:
        """
        Suggest modifications to existing test case to improve coverage.
        
        Args:
            test_case: The TestCase object
            gap_context: Context about coverage gaps
            
        Returns:
            Modification suggestions
        """
       
        return {
            "test_case_id": test_case.id,
            "suggested_modifications": [
                "Add edge case validation",
                "Include error handling scenarios",
                "Extend to cover additional user flows"
            ],
            "reason": "To improve coverage of identified gaps"
        }


