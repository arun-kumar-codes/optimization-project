"""
Module for semantic analysis of test cases using Claude API.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from ai.claude_client import ClaudeClient


class SemanticAnalyzer:
    """Performs semantic analysis on test cases using AI."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize semantic analyzer.
        
        Args:
            api_key: Claude API key (optional)
        """
        self.claude_client = ClaudeClient(api_key)
        self.system_prompt = """You are an expert test automation analyst. 
Analyze test cases and provide insights about their business value, purpose, and criticality.
Be concise and specific in your analysis."""
    
    def analyze_test_case(self, test_case: TestCase) -> Dict:
        """
        Perform semantic analysis on a single test case.
        
        Args:
            test_case: The TestCase object
            
        Returns:
            Analysis dictionary
        """
        # Prepare steps summary
        steps_summary = self._prepare_steps_summary(test_case)
        
        # Create prompt
        prompt = self.claude_client.create_prompt_template(
            "semantic_analysis",
            test_case_id=test_case.id,
            name=test_case.name,
            description=test_case.description or "No description",
            steps_summary=steps_summary
        )
        
        # Get AI analysis
        ai_response = self.claude_client.analyze(prompt, self.system_prompt)
        
        # Parse response
        analysis = self._parse_analysis_response(ai_response, test_case)
        
        return analysis
    
    def _prepare_steps_summary(self, test_case: TestCase) -> str:
        """Prepare a summary of test steps."""
        if not test_case.steps:
            return "No steps"
        
        steps_list = []
        for i, step in enumerate(sorted(test_case.steps, key=lambda s: s.position)[:10], 1):
            step_desc = f"{i}. {step.action_name}"
            if step.element:
                step_desc += f" on {step.element}"
            if step.description:
                step_desc += f": {step.description[:50]}"
            steps_list.append(step_desc)
        
        if len(test_case.steps) > 10:
            steps_list.append(f"... and {len(test_case.steps) - 10} more steps")
        
        return "\n".join(steps_list)
    
    def _parse_analysis_response(self, response: str, test_case: TestCase) -> Dict:
        """Parse AI response into structured format."""
        # Try to extract structured information from response
        analysis = {
            "test_case_id": test_case.id,
            "raw_response": response,
            "business_purpose": self._extract_field(response, "purpose", "Business purpose"),
            "functionality": self._extract_field(response, "functionality", "functionality"),
            "user_journey": self._extract_field(response, "journey", "User journey"),
            "criticality": self._extract_criticality(response),
            "classification": self._extract_classification(response),
            "business_value": self._extract_business_value(response)
        }
        
        return analysis
    
    def _extract_field(self, text: str, keyword: str, label: str) -> str:
        """Extract a field from AI response."""
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        # Try to find the field
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if keyword_lower in line.lower() or label.lower() in line.lower():
                # Get the next line or rest of current line
                if ":" in line:
                    return line.split(":", 1)[1].strip()
                elif i + 1 < len(lines):
                    return lines[i + 1].strip()
        
        return "Not specified"
    
    def _extract_criticality(self, text: str) -> str:
        """Extract criticality level from response."""
        text_lower = text.lower()
        if "high" in text_lower and "critical" in text_lower:
            return "High"
        elif "medium" in text_lower:
            return "Medium"
        elif "low" in text_lower:
            return "Low"
        return "Medium"  # Default
    
    def _extract_classification(self, text: str) -> str:
        """Extract edge case vs happy path classification."""
        text_lower = text.lower()
        if "edge case" in text_lower or "edge" in text_lower:
            return "Edge Case"
        elif "happy path" in text_lower or "happy" in text_lower:
            return "Happy Path"
        return "General"
    
    def _extract_business_value(self, text: str) -> str:
        """Extract business value assessment."""
        # Look for value indicators
        text_lower = text.lower()
        if any(word in text_lower for word in ["critical", "essential", "important", "high value"]):
            return "High"
        elif any(word in text_lower for word in ["moderate", "medium", "standard"]):
            return "Medium"
        elif any(word in text_lower for word in ["low", "nice to have", "optional"]):
            return "Low"
        return "Medium"
    
    def identify_semantic_duplicates(
        self, 
        test_case1: TestCase, 
        test_case2: TestCase
    ) -> Dict:
        """
        Identify if two test cases are semantically duplicates.
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            
        Returns:
            Semantic duplicate analysis
        """
        steps1 = self._prepare_steps_summary(test_case1)
        steps2 = self._prepare_steps_summary(test_case2)
        
        prompt = self.claude_client.create_prompt_template(
            "duplicate_analysis",
            tc1_id=test_case1.id,
            tc1_name=test_case1.name,
            tc1_description=test_case1.description or "No description",
            tc1_steps=steps1,
            tc2_id=test_case2.id,
            tc2_name=test_case2.name,
            tc2_description=test_case2.description or "No description",
            tc2_steps=steps2
        )
        
        ai_response = self.claude_client.analyze(prompt, self.system_prompt)
        
        # Parse response
        similarity_score = self._extract_similarity_score(ai_response)
        recommendation = self._extract_recommendation(ai_response)
        
        return {
            "test_case_1": test_case1.id,
            "test_case_2": test_case2.id,
            "semantic_similarity": similarity_score,
            "recommendation": recommendation,
            "reasoning": ai_response
        }
    
    def _extract_similarity_score(self, text: str) -> float:
        """Extract similarity score from response."""
        import re
        # Look for percentage
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
        if match:
            return float(match.group(1)) / 100.0
        
        # Look for decimal
        match = re.search(r'(\d+\.\d+)', text)
        if match:
            score = float(match.group(1))
            if score > 1.0:
                return score / 100.0
            return score
        
        return 0.5  # Default
    
    def _extract_recommendation(self, text: str) -> str:
        """Extract recommendation from response."""
        text_lower = text.lower()
        if "keep both" in text_lower:
            return "keep_both"
        elif "merge" in text_lower:
            return "merge"
        elif "remove" in text_lower:
            return "remove_one"
        return "keep_both"  # Default
    
    def analyze_all_test_cases(
        self, 
        test_cases: Dict[int, TestCase],
        limit: Optional[int] = None
    ) -> Dict:
        """
        Analyze all test cases semantically.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            limit: Optional limit on number of test cases to analyze
            
        Returns:
            Analysis results for all test cases
        """
        results = {}
        test_case_list = list(test_cases.items())
        
        if limit:
            test_case_list = test_case_list[:limit]
        
        print(f"Analyzing {len(test_case_list)} test cases with AI...")
        
        for test_id, test_case in test_case_list:
            print(f"  Analyzing test case {test_id}...")
            analysis = self.analyze_test_case(test_case)
            results[test_id] = analysis
        
        return {
            "analyses": results,
            "total_analyzed": len(results),
            "summary": self._generate_summary(results)
        }
    
    def _generate_summary(self, results: Dict) -> Dict:
        """Generate summary statistics from analyses."""
        criticality_counts = {"High": 0, "Medium": 0, "Low": 0}
        classification_counts = {"Edge Case": 0, "Happy Path": 0, "General": 0}
        value_counts = {"High": 0, "Medium": 0, "Low": 0}
        
        for analysis in results.values():
            criticality = analysis.get("criticality", "Medium")
            classification = analysis.get("classification", "General")
            value = analysis.get("business_value", "Medium")
            
            criticality_counts[criticality] = criticality_counts.get(criticality, 0) + 1
            classification_counts[classification] = classification_counts.get(classification, 0) + 1
            value_counts[value] = value_counts.get(value, 0) + 1
        
        return {
            "criticality_distribution": criticality_counts,
            "classification_distribution": classification_counts,
            "business_value_distribution": value_counts
        }


