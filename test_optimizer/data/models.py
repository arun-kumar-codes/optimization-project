"""
Data models for representing test cases and test steps.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class TestStep:
    """Represents a single test step."""
    id: int
    position: int
    action_name: str
    action: str
    element: Optional[str] = None
    description: Optional[str] = None
    locator: Optional[Dict[str, Any]] = None
    test_data: Optional[str] = None
    wait_time: Optional[int] = None
    test_case_id: Optional[int] = None
    raw_data: Optional[Dict[str, Any]] = None  # Store original JSON for reference


@dataclass
class TestCase:
    """Represents a test case with its metadata and steps."""
    id: int
    name: str
    description: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    duration: Optional[int] = None  # in milliseconds
    pass_count: Optional[int] = None
    fail_count: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    steps: List[TestStep] = field(default_factory=list)
    prerequisite_case: Optional[int] = None
    test_data_id: Optional[int] = None
    last_run_result: Optional[str] = None
    created_date: Optional[int] = None
    updated_date: Optional[int] = None
    raw_data: Optional[Dict[str, Any]] = None  # Store original JSON for reference
    
    def get_step_count(self) -> int:
        """Get the number of steps in this test case."""
        return len(self.steps)
    
    def get_action_sequence(self) -> List[str]:
        """Get the sequence of action names from steps."""
        return [step.action_name for step in sorted(self.steps, key=lambda s: s.position)]
    
    def get_total_wait_time(self) -> int:
        """Calculate total wait time from all steps."""
        return sum(step.wait_time or 0 for step in self.steps)


@dataclass
class TestFlow:
    """Represents a user flow as a sequence of steps."""
    flow_id: str
    name: str
    steps: List[TestStep] = field(default_factory=list)
    test_case_ids: List[int] = field(default_factory=list)
    flow_type: Optional[str] = None  # e.g., "login", "search", "form_submission"
    description: Optional[str] = None
    
    def get_action_sequence(self) -> List[str]:
        """Get the sequence of action names from steps."""
        return [step.action_name for step in sorted(self.steps, key=lambda s: s.position)]

