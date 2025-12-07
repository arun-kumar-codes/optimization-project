"""
Module for AI-powered test case optimization using Claude API.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase, TestStep
from ai.claude_client import ClaudeClient
from analysis.similarity_analyzer import SimilarityAnalyzer


class AITestCaseOptimizer:
    """Uses AI to optimize test cases and suggest combinations."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI test case optimizer.
        
        Args:
            api_key: Optional Claude API key
        """
        self.claude_client = ClaudeClient(api_key=api_key)
        self.similarity_analyzer = SimilarityAnalyzer()
    
    def optimize_test_case_with_ai(
        self,
        test_case: TestCase,
        context: Optional[Dict] = None
    ) -> TestCase:
        """
        Optimize a single test case using AI.
        
        Args:
            test_case: Test case to optimize
            context: Optional context information
            
        Returns:
            Optimized TestCase object
        """
        # Prepare test case data for AI
        test_case_data = self._prepare_test_case_for_ai(test_case)
        
        prompt = f"""You are a test case optimization expert. Analyze this test case and suggest optimizations.

Test Case:
{json.dumps(test_case_data, indent=2)}

Optimization Goals:
1. Remove redundant steps
2. Combine similar actions
3. Optimize step order
4. Maintain all functionality
5. Preserve all unique coverage

Provide optimized test case in JSON format:
{{
  "optimized_steps": [
    {{
      "position": 1,
      "action_name": "...",
      "action": "...",
      "element": "...",
      "description": "...",
      "test_data": "...",
      "wait_time": ...
    }}
  ],
  "optimizations_made": ["list of optimizations"],
  "reasoning": "explanation of changes"
}}"""

        try:
            response = self.claude_client.analyze(prompt, max_tokens=4000)
            optimized_data = self._parse_ai_response(response)
            
            # Create optimized test case
            optimized_steps = self._create_steps_from_ai_data(
                optimized_data.get("optimized_steps", []),
                test_case
            )
            
            # Create optimized test case
            optimized_test_case = TestCase(
                id=test_case.id,
                name=f"AI-Optimized: {test_case.name}",
                description=test_case.description,
                priority=test_case.priority,
                status=test_case.status,
                duration=test_case.duration,
                pass_count=test_case.pass_count,
                fail_count=test_case.fail_count,
                tags=test_case.tags,
                steps=optimized_steps,
                prerequisite_case=test_case.prerequisite_case,
                test_data_id=test_case.test_data_id,
                last_run_result=test_case.last_run_result,
                created_date=test_case.created_date,
                updated_date=test_case.updated_date,
                raw_data={
                    "ai_optimized": True,
                    "original_test_case_id": test_case.id,
                    "optimizations": optimized_data.get("optimizations_made", []),
                    "reasoning": optimized_data.get("reasoning", "")
                }
            )
            
            return optimized_test_case
            
        except Exception as e:
            print(f"AI optimization failed: {e}. Returning original test case.")
            return test_case
    
    def merge_test_cases_with_ai(
        self,
        test_cases_list: List[TestCase]
    ) -> TestCase:
        """
        Merge multiple test cases using AI to determine best approach.
        
        Args:
            test_cases_list: List of test cases to merge
            
        Returns:
            Optimized merged TestCase
        """
        if len(test_cases_list) == 0:
            raise ValueError("Cannot merge empty list of test cases")
        
        if len(test_cases_list) == 1:
            return test_cases_list[0]
        
        # Prepare test cases data for AI
        test_cases_data = [
            self._prepare_test_case_for_ai(tc) for tc in test_cases_list
        ]
        
        # Analyze similarity
        similarity_info = []
        for i in range(len(test_cases_list)):
            for j in range(i + 1, len(test_cases_list)):
                sim_result = self.similarity_analyzer.calculate_comprehensive_similarity(
                    test_cases_list[i],
                    test_cases_list[j]
                )
                similarity_info.append({
                    "test_case_1": test_cases_list[i].id,
                    "test_case_2": test_cases_list[j].id,
                    "similarity": sim_result["overall"]
                })
        
        prompt = f"""You are a test case optimization expert. Merge these test cases into one optimized test case.

Test Cases to Merge:
{json.dumps(test_cases_data, indent=2)}

Similarity Analysis:
{json.dumps(similarity_info, indent=2)}

Requirements:
1. Preserve ALL unique steps from ALL test cases
2. Remove duplicate steps
3. Maintain logical step order
4. Combine similar actions where possible
5. Preserve all test data scenarios
6. Maintain flow logic

Generate merged test case in JSON format:
{{
  "name": "merged test case name",
  "description": "merged description",
  "steps": [
    {{
      "position": 1,
      "action_name": "...",
      "action": "...",
      "element": "...",
      "description": "...",
      "test_data": "...",
      "wait_time": ...
    }}
  ],
  "source_test_case_ids": [list of source IDs],
  "coverage_maintained": true,
  "reasoning": "explanation of merge strategy"
}}"""

        try:
            response = self.claude_client.analyze(prompt, max_tokens=8000)
            merged_data = self._parse_ai_response(response)
            
            # Generate new ID
            source_ids = [tc.id for tc in test_cases_list]
            new_id = 20000 + hash(tuple(source_ids)) % 80000  # Range: 20000-99999
            
            # Create merged steps
            merged_steps = self._create_steps_from_ai_data(
                merged_data.get("steps", []),
                test_cases_list[0]  # Use first as template
            )
            
            # Create merged test case
            merged_test_case = TestCase(
                id=new_id,
                name=merged_data.get("name", f"Merged: {test_cases_list[0].name}"),
                description=merged_data.get("description", "AI-merged test case"),
                priority=min(tc.priority or 5 for tc in test_cases_list),
                status=test_cases_list[0].status or "READY",
                duration=sum(tc.duration or 0 for tc in test_cases_list),
                tags=list(set(tag for tc in test_cases_list for tag in (tc.tags or []))),
                steps=merged_steps,
                raw_data={
                    "ai_merged": True,
                    "source_test_case_ids": source_ids,
                    "coverage_maintained": merged_data.get("coverage_maintained", True),
                    "reasoning": merged_data.get("reasoning", "")
                }
            )
            
            return merged_test_case
            
        except Exception as e:
            print(f"AI merging failed: {e}. Using rule-based merging.")
            from optimization.test_case_merger import TestCaseMerger
            merger = TestCaseMerger()
            return merger.merge_test_cases_intelligently(test_cases_list)
    
    def generate_optimized_test_suite_with_ai(
        self,
        all_test_cases: Dict[int, TestCase],
        similarity_analysis: Optional[Dict] = None
    ) -> List[TestCase]:
        """
        Generate optimized test suite using AI analysis.
        
        Args:
            all_test_cases: Dictionary of all test cases
            similarity_analysis: Optional pre-computed similarity analysis
            
        Returns:
            List of optimized test cases
        """
        test_cases_summary = []
        for tc_id, tc in list(all_test_cases.items())[:20]:  # Limit to 20 for AI
            test_cases_summary.append({
                "id": tc_id,
                "name": tc.name,
                "step_count": len(tc.steps),
                "actions": [s.action_name for s in sorted(tc.steps, key=lambda s: s.position)[:10]]
            })
        
        prompt = f"""You are a test case optimization expert. Analyze this test suite and suggest optimizations.

Test Suite Summary:
{json.dumps(test_cases_summary, indent=2)}

Optimization Goals:
1. Identify redundant test cases
2. Suggest which test cases should be merged
3. Suggest which test cases can be removed
4. Maintain 100% step coverage
5. Optimize test suite size

Provide optimization recommendations in JSON format:
{{
  "recommendations": [
    {{
      "action": "merge" | "remove" | "keep",
      "test_case_ids": [list of IDs],
      "reasoning": "explanation",
      "estimated_coverage_impact": "maintained" | "reduced"
    }}
  ],
  "optimized_test_suite_size": estimated_count,
  "coverage_maintained": true
}}"""

        try:
            response = self.claude_client.analyze(prompt, max_tokens=4000)
            recommendations = self._parse_ai_response(response)
            
           
            return list(all_test_cases.values())
            
        except Exception as e:
            print(f"AI suite optimization failed: {e}")
            return list(all_test_cases.values())
    
    def ai_suggest_test_case_combinations(
        self,
        test_cases: Dict[int, TestCase]
    ) -> List[Dict]:
        """
        AI suggests which test cases should be combined.
        
        Args:
            test_cases: Dictionary of test cases
            
        Returns:
            List of combination suggestions
        """
        # Prepare summary
        test_cases_summary = []
        for tc_id, tc in list(test_cases.items())[:15]:  # Limit for AI
            test_cases_summary.append({
                "id": tc_id,
                "name": tc.name,
                "step_count": len(tc.steps),
                "first_actions": [s.action_name for s in sorted(tc.steps, key=lambda s: s.position)[:5]]
            })
        
        prompt = f"""Analyze these test cases and suggest which ones should be combined.

Test Cases:
{json.dumps(test_cases_summary, indent=2)}

Provide suggestions in JSON format:
{{
  "suggestions": [
    {{
      "test_case_ids": [list of IDs to combine],
      "reasoning": "why they should be combined",
      "estimated_steps_after_merge": number,
      "coverage_impact": "maintained" | "improved" | "reduced"
    }}
  ]
}}"""

        try:
            response = self.claude_client.analyze(prompt, max_tokens=3000)
            suggestions = self._parse_ai_response(response)
            return suggestions.get("suggestions", [])
            
        except Exception as e:
            print(f"AI combination suggestions failed: {e}")
            return []
    
    def ai_optimize_step_sequence(
        self,
        steps: List[TestStep]
    ) -> List[TestStep]:
        """
        AI optimizes step order and removes redundancies.
        
        Args:
            steps: List of steps to optimize
            
        Returns:
            Optimized list of steps
        """
        if not steps:
            return steps
        
        # Prepare steps data
        steps_data = []
        for step in steps[:50]:  # Limit for AI
            steps_data.append({
                "position": step.position,
                "action_name": step.action_name,
                "action": step.action,
                "element": step.element,
                "description": step.description,
                "test_data": step.test_data,
                "wait_time": step.wait_time
            })
        
        prompt = f"""Optimize this test step sequence.

Steps:
{json.dumps(steps_data, indent=2)}

Optimization Goals:
1. Remove redundant steps
2. Combine similar consecutive actions
3. Optimize wait times
4. Maintain logical flow
5. Preserve all functionality

Provide optimized steps in JSON format:
{{
  "optimized_steps": [
    {{
      "position": 1,
      "action_name": "...",
      "action": "...",
      "element": "...",
      "description": "...",
      "test_data": "...",
      "wait_time": ...
    }}
  ],
  "optimizations": ["list of changes made"]
}}"""

        try:
            response = self.claude_client.analyze(prompt, max_tokens=4000)
            optimized_data = self._parse_ai_response(response)
            
            # Create optimized steps
            optimized_steps = self._create_steps_from_ai_data(
                optimized_data.get("optimized_steps", []),
                steps[0] if steps else None
            )
            
            return optimized_steps
            
        except Exception as e:
            print(f"AI step optimization failed: {e}. Returning original steps.")
            return steps
    
    def _prepare_test_case_for_ai(self, test_case: TestCase) -> Dict:
        """Prepare test case data for AI analysis."""
        steps_data = []
        for step in sorted(test_case.steps, key=lambda s: s.position)[:30]:  # Limit steps
            steps_data.append({
                "position": step.position,
                "action_name": step.action_name,
                "action": step.action,
                "element": step.element,
                "description": step.description,
                "test_data": step.test_data,
                "wait_time": step.wait_time
            })
        
        return {
            "id": test_case.id,
            "name": test_case.name,
            "description": test_case.description,
            "priority": test_case.priority,
            "step_count": len(test_case.steps),
            "steps": steps_data
        }
    
    def _parse_ai_response(self, response: str) -> Dict:
        """Parse AI response JSON."""
        try:
           
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                # Try to find JSON object
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end] if start >= 0 and end > start else response
            
            return json.loads(json_str)
            
        except Exception as e:
            print(f"Failed to parse AI response: {e}")
            print(f"Response: {response[:500]}")
            return {}
    
    def _create_steps_from_ai_data(
        self,
        steps_data: List[Dict],
        template_test_case: Optional[TestCase] = None
    ) -> List[TestStep]:
        """Create TestStep objects from AI-generated data."""
        steps = []
        
        for i, step_data in enumerate(steps_data, start=1):
            # Use template step if available for missing fields
            template_step = None
            if template_test_case and template_test_case.steps:
                template_step = template_test_case.steps[0]
            
            step = TestStep(
                id=step_data.get("id", i * 1000), 
                position=step_data.get("position", i),
                action_name=step_data.get("action_name", ""),
                action=step_data.get("action", step_data.get("action_name", "")),
                element=step_data.get("element"),
                description=step_data.get("description"),
                test_data=step_data.get("test_data"),
                wait_time=step_data.get("wait_time", template_step.wait_time if template_step else None),
                test_case_id=None,
                raw_data=step_data
            )
            steps.append(step)
        
        return steps


