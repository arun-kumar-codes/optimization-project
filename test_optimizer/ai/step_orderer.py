"""
AI-Powered Step Orderer - Uses Claude to understand step semantics and order them correctly.
"""
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestStep
from ai.claude_client import ClaudeClient
from ai.cache_manager import AICacheManager


class AIStepOrderer:
    """Uses AI to understand step semantics and order them correctly."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI step orderer.
        
        Args:
            api_key: Claude API key (optional, will use env var if not provided)
        """
        self.claude_client = ClaudeClient(api_key)
        self.cache_manager = AICacheManager()
        self.system_prompt = """You are an expert test automation engineer specializing in web application testing.
Your task is to analyze test steps and order them logically based on:
1. Page context (which page/module each step belongs to)
2. Navigation requirements (navigate before page actions)
3. Element dependencies (click before enter, except search fields)
4. Logical flow (group steps by page/module, maintain sequence within each group)

Be precise and ensure steps are ordered correctly for execution."""
    
    def order_steps_semantically(self, steps: List[TestStep]) -> Tuple[List[TestStep], List[str]]:
        """
        Order steps semantically using AI understanding.
        
        Args:
            steps: List of unordered or partially ordered steps
            
        Returns:
            (ordered_steps, issues_found)
        """
        if not steps or len(steps) <= 1:
            return steps, []
        
        # Prepare steps summary for AI
        steps_summary = self._prepare_steps_summary(steps)
        
        # Build prompt for AI
        prompt = f"""Analyze these test steps and order them correctly for execution.

CRITICAL REQUIREMENTS:
1. Group steps by page/module (e.g., Admin, PIM, Dashboard)
2. Ensure navigation happens before page actions
3. Ensure click happens before enter (except search fields)
4. Maintain logical flow within each page/module
5. **CRITICAL: DO NOT REMOVE ANY STEPS - ONLY REORDER THEM**
6. **PRESERVE ALL STEPS**: Include ALL steps from the input in ordered_steps, just reorder them logically
7. **NO STEP REMOVAL**: Even if a step seems redundant or duplicate, include it in ordered_steps
8. Ensure logout is at the very end (if present)
9. **IMPORTANT**: Your job is ONLY to reorder steps, NOT to remove them. Every step in the input must appear in ordered_steps.

STEPS TO ORDER:
{steps_summary}

Provide the ordered steps in JSON format:
{{
  "ordered_steps": [
    {{
      "original_index": 0,
      "action": "navigateTo",
      "element": null,
      "test_data": "https://...",
      "reason": "Navigation must come first"
    }},
    ...
  ],
  "grouping": {{
    "Admin Module": [0, 1, 2],
    "PIM Module": [3, 4, 5],
    ...
  }},
  "issues_found": [
    "Step X: Enter without click before",
    ...
  ]
}}

IMPORTANT:
- Return ONLY valid JSON, no markdown formatting
- original_index refers to the index in the input steps array
- **CRITICAL: Include ALL steps from the input in ordered_steps - DO NOT skip or remove any steps**
- Group steps logically by page/module
- **Your task is ONLY to reorder steps, NOT to remove them**
- Every step in the input must have a corresponding entry in ordered_steps
- If you think a step is a duplicate, still include it - we will handle duplicate removal separately"""
        
        # Check cache first (simple file-based cache for step ordering)
        cache_key = self._get_cache_key(steps)
        cache_file = None
        if self.cache_manager.cache_dir:
            cache_file = self.cache_manager.cache_dir / f"step_ordering_{cache_key}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)
                        if "response" in cached_data:
                            return self._parse_ai_response(cached_data["response"], steps)
                except Exception as e:
                    print(f"      [AI ORDERER] Cache read failed: {e}")
        
        # Call AI
        try:
            ai_response = self.claude_client.analyze(prompt, self.system_prompt)
            
            # Cache result (simple file-based cache)
            if cache_file:
                try:
                    with open(cache_file, 'w') as f:
                        json.dump({"steps": steps_summary, "response": ai_response}, f)
                except Exception as e:
                    print(f"      [AI ORDERER] Cache save failed: {e}")
            
            return self._parse_ai_response(ai_response, steps)
        except Exception as e:
            print(f"      [AI ORDERER] Error calling AI: {e}")
            # Fallback to original order
            return steps, [f"AI ordering failed: {e}"]
    
    def _prepare_steps_summary(self, steps: List[TestStep]) -> str:
        """Prepare a summary of steps for AI analysis."""
        summary_lines = []
        for i, step in enumerate(steps):
            action = step.action_name or "unknown"
            element = step.element or "None"
            test_data = str(step.test_data or "")
            action_text = step.action or ""
            url = ""
            
            # Extract URL if navigation
            if action == "navigateTo" and step.raw_data:
                if isinstance(step.raw_data, dict):
                    event = step.raw_data.get("event", {})
                    if isinstance(event, dict):
                        url = event.get("href", "")
            
            summary_lines.append(
                f"{i}. [{action}] {action_text} | Element: {element} | "
                f"Data: {test_data[:50]} | URL: {url}"
            )
        
        return "\n".join(summary_lines)
    
    def _get_cache_key(self, steps: List[TestStep]) -> str:
        """Generate cache key for steps."""
        steps_str = "\n".join([
            f"{i}:{s.action_name}:{s.element}:{s.test_data}"
            for i, s in enumerate(steps)
        ])
        import hashlib
        return hashlib.md5(steps_str.encode()).hexdigest()
    
    def _parse_ai_response(self, ai_response: str, original_steps: List[TestStep]) -> Tuple[List[TestStep], List[str]]:
        """Parse AI response and reorder steps."""
        try:
            # Try to extract JSON from response
            json_str = self._extract_json(ai_response)
            result = json.loads(json_str)
            
            ordered_indices = result.get("ordered_steps", [])
            issues = result.get("issues_found", [])
            
            # Reorder steps based on AI's ordering
            ordered_steps = []
            seen_indices = set()
            login_complete = False  # Track if login is complete
            login_button_clicked = False  # Track if login button was clicked
            
            for step_info in ordered_indices:
                orig_idx = step_info.get("original_index")
                if orig_idx is not None and 0 <= orig_idx < len(original_steps):
                    if orig_idx not in seen_indices:
                        step = original_steps[orig_idx]
                        action_text = (step.action or "").lower()
                        element = (step.element or "").lower() if step.element else ""
                        
                        # Check if login button was clicked (this marks login completion)
                        # Match: "Click on Login", "Click Login", "Click the Login Button", etc.
                        if step.action_name == "click" and "login" in action_text:
                            login_complete = True
                            # Add this login step first
                            new_step = TestStep(
                                id=step.id,
                                position=len(ordered_steps) + 1,
                                action_name=step.action_name,
                                action=step.action,
                                element=step.element,
                                description=step.description,
                                locator=step.locator,
                                test_data=step.test_data,
                                wait_time=step.wait_time,
                                test_case_id=step.test_case_id,
                                raw_data=step.raw_data
                            )
                            ordered_steps.append(new_step)
                            seen_indices.add(orig_idx)
                            continue  # Skip to next step - login is now complete
                        
                        # DO NOT remove steps here - AI should have included all steps
                        # We'll handle duplicate removal separately if needed
                        # Just add the step to ordered_steps
                        
                        # Create new step with updated position
                        new_step = TestStep(
                            id=step.id,
                            position=len(ordered_steps) + 1,
                            action_name=step.action_name,
                            action=step.action,
                            element=step.element,
                            description=step.description,
                            locator=step.locator,
                            test_data=step.test_data,
                            wait_time=step.wait_time,
                            test_case_id=step.test_case_id,
                            raw_data=step.raw_data
                        )
                        ordered_steps.append(new_step)
                        seen_indices.add(orig_idx)
            
            # FINAL PASS: Remove any duplicate login steps that AI might have missed
            # DO NOT remove any steps - AI should have included all steps
            # Just re-number positions and return
            for idx, step in enumerate(ordered_steps, 1):
                step.position = idx
            
            return ordered_steps, issues
            
        except Exception as e:
            print(f"      [AI ORDERER] Error parsing AI response: {e}")
            print(f"      [AI ORDERER] Response: {ai_response[:500]}")
            # Fallback to original order
            return original_steps, [f"Failed to parse AI response: {e}"]
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from AI response (may be wrapped in markdown)."""
        # Try to find JSON block
        import re
        
        # Look for JSON code block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Look for JSON object directly
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        # Return as-is, let JSON parser handle it
        return text

