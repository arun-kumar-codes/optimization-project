"""
Module for analyzing test case dependencies.
"""

import sys
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
                dependencies.append(test_case.prerequisite_case)
        
        # Check for implicit dependencies based on flow patterns
        # If test case starts with a non-login action but needs authentication,
        # it might depend on a login test case
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
        
        # Add any remaining nodes (shouldn't happen if no cycles)
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
        
        # Find connected components (groups with dependencies)
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


