"""
Module for analyzing test case dependencies.
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from flows.flow_analyzer import FlowAnalyzer


class DependencyAnalyzer:
    """Analyzes dependencies between test cases."""
    
    def __init__(self):
        self.flow_analyzer = FlowAnalyzer()
    
    def analyze_dependencies(
        self,
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Analyze all dependencies between test cases.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Dependency analysis dictionary
        """
        dependencies = {}
        dependents = {}  # Reverse mapping: which test cases depend on this one
        
        for test_id, test_case in test_cases.items():
            deps = self._get_dependencies(test_case, test_cases)
            dependencies[test_id] = deps
            
            # Build reverse mapping
            for dep_id in deps:
                if dep_id not in dependents:
                    dependents[dep_id] = []
                dependents[dep_id].append(test_id)
        
        # Detect circular dependencies
        circular = self._detect_circular_dependencies(dependencies)
        
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(dependencies)
        
        return {
            "dependencies": dependencies,
            "dependents": dependents,
            "circular_dependencies": circular,
            "dependency_graph": dependency_graph,
            "summary": {
                "total_test_cases": len(test_cases),
                "test_cases_with_dependencies": len([tid for tid, deps in dependencies.items() if deps]),
                "total_dependencies": sum(len(deps) for deps in dependencies.values()),
                "circular_dependency_count": len(circular)
            }
        }
    
    def _get_dependencies(
        self,
        test_case: TestCase,
        all_test_cases: Dict[int, TestCase]
    ) -> List[int]:
        """
        Get dependencies for a single test case.
        Validates entity relationships to ensure dependencies only exist when
        test cases operate on the same entity/data.
        
        Args:
            test_case: The test case to analyze
            all_test_cases: All test cases
            
        Returns:
            List of test case IDs this test case depends on
        """
        dependencies = []
        
        # Check explicit prerequisite
        if test_case.prerequisite_case:
            if test_case.prerequisite_case in all_test_cases:
                prerequisite = all_test_cases[test_case.prerequisite_case]
                
                # CRITICAL: Only enforce dependency if they operate on same entity/data
                if self._check_entity_relationship(test_case, prerequisite):
                    dependencies.append(test_case.prerequisite_case)
                else:
                    # Different entities - no real dependency, can run in parallel
                    print(f"  [DEPENDENCY] TC{test_case.id} has prerequisite TC{prerequisite.id} but operates on different entity/data - dependency ignored")
        
        
        flows = self.flow_analyzer.identify_flow_type(test_case)
        
        if "authentication" not in flows:
            # Check if first steps suggest it needs login
            if test_case.steps:
                first_steps = sorted(test_case.steps, key=lambda s: s.position)[:3]
                first_actions = [step.action_name for step in first_steps]
                
                # If doesn't start with login, might need a login test case first
                if "navigateto" not in first_actions and "login" not in [s.action.lower() for s in first_steps]:
                    # Look for login test cases
                    for other_id, other_tc in all_test_cases.items():
                        other_flows = self.flow_analyzer.identify_flow_type(other_tc)
                        if "authentication" in other_flows and other_tc.id != test_case.id:
                            # Potential dependency, but not explicit
                            # We'll mark it as a soft dependency
                            pass
        
        return dependencies
    
    def _extract_entity_identifiers(self, test_case: TestCase) -> Set[str]:
        """
        Extract entity identifiers from a test case.
        Entity identifiers include: test_data_id, step test_data values, 
        and entity references from steps (user IDs, account numbers, etc.).
        
        Args:
            test_case: The test case to analyze
            
        Returns:
            Set of entity identifier strings (normalized, lowercase)
        """
        entities = set()
        
        # 1. Test data ID
        if test_case.test_data_id:
            entities.add(f"data_id_{test_case.test_data_id}")
        
        # 2. Step-level test data
        for step in test_case.steps:
            if step.test_data:
                # Normalize test data (lowercase, strip whitespace)
                normalized = str(step.test_data).lower().strip()
                if normalized:
                    entities.add(f"test_data_{normalized}")
        
        # 3. Extract entity references from step descriptions and test data
        # Look for patterns like: user IDs, email addresses, account numbers, etc.
        # Check test case name and description
        text_to_check = f"{test_case.name} {test_case.description or ''}"
        
        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text_to_check, re.IGNORECASE)
        for email in emails:
            entities.add(f"email_{email.lower()}")
        
        # User ID patterns (e.g., "user123", "user_123", "User A", "userA")
        user_pattern = r'\b(?:user|usr)[\s_-]?([A-Za-z0-9]+)\b'
        user_ids = re.findall(user_pattern, text_to_check, re.IGNORECASE)
        for user_id in user_ids:
            entities.add(f"user_{user_id.lower()}")
        
        # Account number patterns (e.g., "account123", "acc_456")
        account_pattern = r'\b(?:account|acc)[\s_-]?([A-Za-z0-9]+)\b'
        account_ids = re.findall(account_pattern, text_to_check, re.IGNORECASE)
        for account_id in account_ids:
            entities.add(f"account_{account_id.lower()}")
        
        # Check step descriptions and test data
        for step in test_case.steps:
            step_text = f"{step.description or ''} {step.test_data or ''}"
            
            # Extract emails from steps
            step_emails = re.findall(email_pattern, step_text, re.IGNORECASE)
            for email in step_emails:
                entities.add(f"email_{email.lower()}")
            
            # Extract user IDs from steps
            step_users = re.findall(user_pattern, step_text, re.IGNORECASE)
            for user_id in step_users:
                entities.add(f"user_{user_id.lower()}")
            
            # Extract account numbers from steps
            step_accounts = re.findall(account_pattern, step_text, re.IGNORECASE)
            for account_id in step_accounts:
                entities.add(f"account_{account_id.lower()}")
        
        return entities
    
    def _check_entity_relationship(
        self,
        test_case: TestCase,
        prerequisite: TestCase
    ) -> bool:
        """
        Check if two test cases operate on the same entity/data.
        
        If test cases operate on different entities, they don't have a real
        dependency and can run in parallel or in any order.
        
        Args:
            test_case: The dependent test case
            prerequisite: The prerequisite test case
            
        Returns:
            True if they operate on same entity (real dependency exists)
            False if they operate on different entities (no dependency)
        """
        # Extract entity identifiers from both test cases
        tc1_entities = self._extract_entity_identifiers(test_case)
        tc2_entities = self._extract_entity_identifiers(prerequisite)
        
        # If neither has entity identifiers, assume dependency exists (safe default)
        if not tc1_entities and not tc2_entities:
            return True
        
        # If one has identifiers but the other doesn't, check if it's a generic operation
        # Generic operations (like login) don't need entity matching
        if not tc1_entities or not tc2_entities:
            # Check if prerequisite is a generic operation (like authentication)
            prereq_flows = self.flow_analyzer.identify_flow_type(prerequisite)
            if "authentication" in prereq_flows or "navigation" in prereq_flows:
                # Generic operations don't require entity matching
                return True
            # Otherwise, if one has entities and other doesn't, likely different entities
            return False
        
        # Check for entity overlap
        entity_overlap = tc1_entities.intersection(tc2_entities)
        
        # If there's overlap, they operate on same entity
        if entity_overlap:
            return True
        
        # Check if test_data_id is different (strong indicator of different entities)
        if test_case.test_data_id and prerequisite.test_data_id:
            if test_case.test_data_id != prerequisite.test_data_id:
                # Different test data sets - likely different entities
                return False
        
        # If no overlap and both have identifiers, they operate on different entities
        # No dependency needed
        return False
    
    def _detect_circular_dependencies(
        self,
        dependencies: Dict[int, List[int]]
    ) -> List[List[int]]:
        """
        Detect circular dependencies.
        
        Args:
            dependencies: Dependency dictionary
            
        Returns:
            List of circular dependency chains
        """
        circular = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: int, path: List[int]):
            """Depth-first search to detect cycles."""
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                if cycle not in circular:
                    circular.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for dep in dependencies.get(node, []):
                dfs(dep, path.copy())
            
            rec_stack.remove(node)
        
        for test_id in dependencies.keys():
            if test_id not in visited:
                dfs(test_id, [])
        
        return circular
    
    def _build_dependency_graph(
        self,
        dependencies: Dict[int, List[int]]
    ) -> Dict[int, Dict]:
        """
        Build a dependency graph structure.
        
        Args:
            dependencies: Dependency dictionary
            
        Returns:
            Graph structure dictionary
        """
        graph = {}
        
        for test_id, deps in dependencies.items():
            graph[test_id] = {
                "dependencies": deps,
                "dependency_count": len(deps),
                "is_leaf": len(deps) == 0,  # No dependencies
                "is_root": not any(test_id in other_deps for other_deps in dependencies.values())
            }
        
        return graph
    
    def get_execution_order(
        self,
        dependencies: Dict[int, List[int]]
    ) -> List[int]:
        """
        Get execution order respecting dependencies (topological sort).
        
        Args:
            dependencies: Dependency dictionary
            
        Returns:
            Ordered list of test case IDs
        """
        # Topological sort
        in_degree = {tid: 0 for tid in dependencies.keys()}
        
        # Calculate in-degrees
        for deps in dependencies.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] = in_degree.get(dep, 0) + 1
        
        # Find nodes with no incoming edges
        queue = [tid for tid, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            # Sort queue by test case ID for deterministic order
            queue.sort()
            node = queue.pop(0)
            result.append(node)
            
            # Reduce in-degree of dependent nodes
            for test_id, deps in dependencies.items():
                if node in deps:
                    in_degree[test_id] -= 1
                    if in_degree[test_id] == 0:
                        queue.append(test_id)
        
      
        remaining = [tid for tid in dependencies.keys() if tid not in result]
        result.extend(remaining)
        
        return result
    
    def get_independent_groups(
        self,
        dependencies: Dict[int, List[int]]
    ) -> List[List[int]]:
        """
        Get groups of test cases that can run in parallel (no dependencies between them).
        
        Args:
            dependencies: Dependency dictionary
            
        Returns:
            List of groups, each group can run in parallel
        """
        # Build dependency graph
        graph = {}
        for test_id in dependencies.keys():
            graph[test_id] = set(dependencies.get(test_id, []))
        
        # Find connected component
        visited = set()
        groups = []
        
        def dfs(node: int, component: Set[int]):
            """Depth-first search to find connected component."""
            if node in visited:
                return
            visited.add(node)
            component.add(node)
            
            # Add dependencies
            for dep in graph.get(node, []):
                dfs(dep, component)
            
            # Add dependents
            for other_id, deps in graph.items():
                if node in deps:
                    dfs(other_id, component)
        
        # Find all components
        for test_id in graph.keys():
            if test_id not in visited:
                component = set()
                dfs(test_id, component)
                groups.append(list(component))
        
        return groups


