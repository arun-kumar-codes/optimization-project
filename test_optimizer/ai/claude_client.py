"""
Claude API client for AI-powered analysis.
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try loading from project root
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Load from current directory
        load_dotenv()


class ClaudeClient:
    """Client for interacting with Claude API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude client.
        
        Args:
            api_key: Anthropic API key (if None, will try to get from environment)
        """
        if api_key is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY not found. Please set it in .env file or environment variable."
                )
        
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet"  # Using Claude 3.5 Sonnet model
        self.rate_limit_delay = 1.0  # Delay between requests in seconds
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Implement rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    def analyze(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000
    ) -> str:
        """
        Send a prompt to Claude and get response.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            
        Returns:
            Claude's response text
        """
        self._rate_limit()
        
        try:
            messages = [{"role": "user", "content": prompt}]
            
            # System prompt should be a list or string, but API expects it as a parameter
            create_params = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": messages
            }
            if system_prompt:
                create_params["system"] = system_prompt
            
            response = self.client.messages.create(**create_params)
            
            return response.content[0].text
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            return f"Error: {str(e)}"
    
    def analyze_batch(
        self, 
        prompts: List[str], 
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000
    ) -> List[str]:
        """
        Analyze multiple prompts in batch (with rate limiting).
        
        Args:
            prompts: List of prompts
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens per response
            
        Returns:
            List of responses
        """
        responses = []
        for i, prompt in enumerate(prompts):
            print(f"Processing prompt {i+1}/{len(prompts)}...")
            response = self.analyze(prompt, system_prompt, max_tokens)
            responses.append(response)
        return responses
    
    def create_prompt_template(self, template_name: str, **kwargs) -> str:
        """
        Create a prompt from a template.
        
        Args:
            template_name: Name of the template
            **kwargs: Template variables
            
        Returns:
            Formatted prompt string
        """
        templates = {
            "semantic_analysis": """
Analyze the following test case and provide insights:

Test Case ID: {test_case_id}
Name: {name}
Description: {description}
Steps: {steps_summary}

Please provide:
1. Business purpose and value
2. Primary functionality being tested
3. User journey/story
4. Criticality level (High/Medium/Low)
5. Edge case vs happy path classification
""",
            "duplicate_analysis": """
Compare these two test cases and determine if they are semantically similar:

Test Case 1:
ID: {tc1_id}
Name: {tc1_name}
Description: {tc1_description}
Steps: {tc1_steps}

Test Case 2:
ID: {tc2_id}
Name: {tc2_name}
Description: {tc2_description}
Steps: {tc2_steps}

Provide:
1. Semantic similarity (0-100%)
2. Are they testing the same functionality?
3. Recommendation: Keep both, merge, or remove one
4. Reasoning
""",
            "optimization_recommendation": """
Given the following test case and optimization context:

Test Case ID: {test_case_id}
Name: {name}
Priority: {priority}
Pass Rate: {pass_rate}%
Duration: {duration}ms
Steps: {step_count}
Flows: {flows}

Context:
- Total test cases: {total_test_cases}
- Similar test cases found: {similar_count}
- Flow coverage: {flow_coverage}%

Provide optimization recommendation:
1. Should this test case be kept, removed, or merged?
2. Justification
3. Impact on coverage if removed
4. Priority adjustment recommendation
""",
            "gap_analysis": """
Analyze the test suite for coverage gaps:

Test Cases: {test_cases_summary}
Flows Covered: {flows_covered}
Critical Flows: {critical_flows}

Identify:
1. Missing user flows not covered
2. Critical gaps in coverage
3. Suggested new test cases
4. Test case modifications to improve coverage
"""
        }
        
        template = templates.get(template_name, "")
        return template.format(**kwargs)

