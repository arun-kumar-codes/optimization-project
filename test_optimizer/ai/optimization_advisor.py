"""
Module for AI-powered optimization recommendations.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from ai.claude_client import ClaudeClient


class OptimizationAdvisor:
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize optimization advisor.
        
        Args:
            api_key: Claude API key (optional)
        """
        self.claude_client = ClaudeClient(api_key)
        self.system_prompt = """You are an expert test optimization consultant.
Analyze test cases and provide recommendations for optimizing test suites while maintaining coverage.
Focus on removing duplicates, merging similar tests, and prioritizing critical tests."""
    
    def get_optimization_recommendation(
        self, 
        test_case: TestCase,
        context: Dict
    ) -> Dict:
        """
        Get optimization recommendation for a test case.
        
        Args:
            test_case: The TestCase object
            context: Context information (similar test cases, flow coverage, etc.)
            
        Returns:
            Optimization recommendation dictionary
        """
        pass_rate = None
        if test_case.pass_count is not None and test_case.fail_count is not None:
            total = test_case.pass_count + test_case.fail_count
            if total > 0:
                pass_rate = (test_case.pass_count / total) * 100
        
        similar_count = len(context.get("similar_test_cases", []))
        flow_coverage = context.get("flow_coverage", 0)
        total_test_cases = context.get("total_test_cases", 0)
        
        flows = context.get("flows", [])
        flows_str = ", ".join(flows) if flows else "Unknown"
        
        prompt = self.claude_client.create_prompt_template(
            "optimization_recommendation",
            test_case_id=test_case.id,
            name=test_case.name,
            priority=test_case.priority or "Unknown",
            pass_rate=f"{pass_rate:.1f}" if pass_rate else "Unknown",
            duration=test_case.duration or "Unknown",
            step_count=len(test_case.steps),
            flows=flows_str,
            total_test_cases=total_test_cases,
            similar_count=similar_count,
            flow_coverage=f"{flow_coverage:.1f}"
        )
        
        ai_response = self.claude_client.analyze(prompt, self.system_prompt)
        
        recommendation = self._parse_recommendation(ai_response, test_case)
        
        return recommendation
    
    def _parse_recommendation(self, response: str, test_case: TestCase) -> Dict:
        """Parse AI recommendation response."""
        response_lower = response.lower()
        
        action = "keep"
        if "remove" in response_lower and "don't remove" not in response_lower:
            action = "remove"
        elif "merge" in response_lower:
            action = "merge"
        
        justification = self._extract_justification(response)
        
        coverage_impact = self._extract_coverage_impact(response)
        
        priority_rec = self._extract_priority_recommendation(response)
        
        return {
            "test_case_id": test_case.id,
            "action": action,
            "justification": justification,
            "coverage_impact": coverage_impact,
            "priority_recommendation": priority_rec,
            "raw_response": response
        }
    
    def _extract_justification(self, text: str) -> str:
        """Extract justification from response."""
        lines = text.split("\n")
        justification_lines = []
        in_justification = False
        
        for line in lines:
            line_lower = line.lower()
            if "justification" in line_lower or "reason" in line_lower:
                in_justification = True
                if ":" in line:
                    justification_lines.append(line.split(":", 1)[1].strip())
                continue
            
            if in_justification:
                if line.strip() and not line.strip().startswith(("1.", "2.", "3.", "-")):
                    justification_lines.append(line.strip())
                elif line.strip().startswith(("1.", "2.", "3.")):
                    break
        
        if justification_lines:
            return " ".join(justification_lines)
        
        paragraphs = text.split("\n\n")
        if paragraphs:
            return paragraphs[0].strip()
        
        return "No justification provided"
    
    def _extract_coverage_impact(self, text: str) -> str:
        """Extract coverage impact assessment."""
        text_lower = text.lower()
        if "no impact" in text_lower or "minimal impact" in text_lower:
            return "Low"
        elif "significant impact" in text_lower or "high impact" in text_lower:
            return "High"
        elif "moderate impact" in text_lower or "medium impact" in text_lower:
            return "Medium"
        return "Unknown"
    
    def _extract_priority_recommendation(self, text: str) -> Optional[str]:
        """Extract priority adjustment recommendation."""
        text_lower = text.lower()
        if "increase priority" in text_lower or "raise priority" in text_lower:
            return "increase"
        elif "decrease priority" in text_lower or "lower priority" in text_lower:
            return "decrease"
        elif "maintain priority" in text_lower or "keep priority" in text_lower:
            return "maintain"
        return None
    
    def get_batch_recommendations(
        self, 
        test_cases: Dict[int, TestCase],
        duplicate_groups: Dict,
        flow_coverage: Dict,
        limit: Optional[int] = None
    ) -> Dict:
        """
        Get optimization recommendations for multiple test cases.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            duplicate_groups: Duplicate groups from Phase 2
            flow_coverage: Flow coverage information from Phase 3
            limit: Optional limit on number of test cases to analyze
            
        Returns:
            Recommendations for all test cases
        """
        recommendations = {}
        test_case_list = list(test_cases.items())
        
        if limit:
            test_case_list = test_case_list[:limit]
        
        print(f"Getting optimization recommendations for {len(test_case_list)} test cases...")
        
        similarity_map = {}
        for group_type, groups in duplicate_groups.items():
            if not isinstance(groups, list):
                continue
            for group in groups:
                test_case_ids = group.get("test_case_ids", [])
                if not isinstance(test_case_ids, list):
                    continue
                for test_id in test_case_ids:
                    if test_id not in similarity_map:
                        similarity_map[test_id] = []
                    similarity_map[test_id].extend([
                        tid for tid in test_case_ids 
                        if tid != test_id
                    ])
        
        from flows.flow_analyzer import FlowAnalyzer
        flow_analyzer = FlowAnalyzer()
        
        for test_id, test_case in test_case_list:
            print(f"  Analyzing test case {test_id}...")
            
            similar_ids = similarity_map.get(test_id, [])
            flows = flow_analyzer.identify_flow_type(test_case)
            coverage_pct = flow_coverage.get("coverage_percentage", 0)
            
            context = {
                "similar_test_cases": similar_ids,
                "flows": flows,
                "flow_coverage": coverage_pct,
                "total_test_cases": len(test_cases)
            }
            
            recommendation = self.get_optimization_recommendation(test_case, context)
            recommendations[test_id] = recommendation
        
        return {
            "recommendations": recommendations,
            "summary": self._generate_recommendation_summary(recommendations)
        }
    
    def _generate_recommendation_summary(self, recommendations: Dict) -> Dict:
        """Generate summary of recommendations."""
        action_counts = {"keep": 0, "remove": 0, "merge": 0}
        coverage_impacts = {"High": 0, "Medium": 0, "Low": 0, "Unknown": 0}
        
        for rec in recommendations.values():
            action = rec.get("action", "keep")
            impact = rec.get("coverage_impact", "Unknown")
            
            action_counts[action] = action_counts.get(action, 0) + 1
            coverage_impacts[impact] = coverage_impacts.get(impact, 0) + 1
        
        return {
            "action_distribution": action_counts,
            "coverage_impact_distribution": coverage_impacts,
            "total_recommendations": len(recommendations)
        }


