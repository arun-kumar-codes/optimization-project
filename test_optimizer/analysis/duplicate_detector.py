"""
Module for detecting and grouping duplicate test cases.
"""

from typing import Dict, List, Set, Tuple
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from analysis.similarity_analyzer import SimilarityAnalyzer


class DuplicateDetector:
    """Detects duplicate and highly similar test cases."""
    
    def __init__(
        self, 
        exact_threshold: float = 1.0,
        near_duplicate_threshold: float = 0.90,
        highly_similar_threshold: float = 0.75
    ):
        """
        Initialize duplicate detector with similarity thresholds.
        
        Args:
            exact_threshold: Threshold for exact duplicates (default: 1.0 = 100%)
            near_duplicate_threshold: Threshold for near duplicates (default: 0.90 = 90%)
            highly_similar_threshold: Threshold for highly similar (default: 0.75 = 75%)
        """
        self.exact_threshold = exact_threshold
        self.near_duplicate_threshold = near_duplicate_threshold
        self.highly_similar_threshold = highly_similar_threshold
        self.similarity_analyzer = SimilarityAnalyzer()
    
    def detect_duplicates(
        self, 
        test_cases: Dict[int, TestCase]
    ) -> Dict[str, List[Dict]]:
        """
        Detect all types of duplicates and group them.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            Dictionary with duplicate groups categorized by type
        """
        # Find all similar pairs
        similar_pairs = self.similarity_analyzer.find_similar_test_cases(
            test_cases,
            threshold=self.highly_similar_threshold
        )
        
        # Group into clusters
        exact_duplicates = []
        near_duplicates = []
        highly_similar = []
        
        # Build graph of similarities
        similarity_graph = self._build_similarity_graph(similar_pairs)
        
        # Find connected components (duplicate groups)
        groups = self._find_connected_components(similarity_graph, test_cases)
        
        # Categorize groups
        for group in groups:
            group_info = self._analyze_group(group, test_cases)
            
            if group_info["max_similarity"] >= self.exact_threshold:
                exact_duplicates.append(group_info)
            elif group_info["max_similarity"] >= self.near_duplicate_threshold:
                near_duplicates.append(group_info)
            elif group_info["max_similarity"] >= self.highly_similar_threshold:
                highly_similar.append(group_info)
        
        return {
            "exact_duplicates": exact_duplicates,
            "near_duplicates": near_duplicates,
            "highly_similar": highly_similar,
            "total_groups": len(exact_duplicates) + len(near_duplicates) + len(highly_similar)
        }
    
    def _build_similarity_graph(
        self, 
        similar_pairs: List[Tuple[int, int, float]]
    ) -> Dict[int, List[Tuple[int, float]]]:
        """
        Build a graph representation of similarities.
        
        Args:
            similar_pairs: List of (id1, id2, similarity) tuples
            
        Returns:
            Graph as dictionary: {test_case_id: [(connected_id, similarity), ...]}
        """
        graph = {}
        
        for id1, id2, similarity in similar_pairs:
            if id1 not in graph:
                graph[id1] = []
            if id2 not in graph:
                graph[id2] = []
            
            graph[id1].append((id2, similarity))
            graph[id2].append((id1, similarity))
        
        return graph
    
    def _find_connected_components(
        self, 
        graph: Dict[int, List[Tuple[int, float]]],
        test_cases: Dict[int, TestCase]
    ) -> List[Set[int]]:
        """
        Find connected components in the similarity graph (duplicate groups).
        
        Args:
            graph: Similarity graph
            test_cases: All test cases
            
        Returns:
            List of sets, each set contains test case IDs in the same group
        """
        visited = set()
        components = []
        
        def dfs(node: int, component: Set[int]):
            """Depth-first search to find connected component."""
            if node in visited:
                return
            visited.add(node)
            component.add(node)
            
            if node in graph:
                for neighbor, _ in graph[node]:
                    if neighbor not in visited:
                        dfs(neighbor, component)
        
        # Find all components
        for node in graph.keys():
            if node not in visited:
                component = set()
                dfs(node, component)
                if len(component) > 1:  # Only groups with 2+ test cases
                    components.append(component)
        
        # Also include isolated test cases (no duplicates found)
        all_ids = set(test_cases.keys())
        grouped_ids = set()
        for component in components:
            grouped_ids.update(component)
        
        isolated = all_ids - grouped_ids
        for test_id in isolated:
            # Create singleton group for isolated test cases
            components.append({test_id})
        
        return components
    
    def _analyze_group(
        self, 
        group: Set[int], 
        test_cases: Dict[int, TestCase]
    ) -> Dict:
        """
        Analyze a duplicate group and determine which test case to keep.
        
        Args:
            group: Set of test case IDs in the group
            test_cases: All test cases
            
        Returns:
            Dictionary with group analysis
        """
        group_list = list(group)
        
        if len(group_list) == 1:
            # Singleton group
            test_id = group_list[0]
            test_case = test_cases[test_id]
            return {
                "test_case_ids": group_list,
                "recommended_keep": test_id,
                "recommended_remove": [],
                "max_similarity": 0.0,
                "average_similarity": 0.0,
                "reason": "No duplicates found"
            }
        
        # Calculate similarities within group
        similarities = []
        for i in range(len(group_list)):
            for j in range(i + 1, len(group_list)):
                id1 = group_list[i]
                id2 = group_list[j]
                result = self.similarity_analyzer.calculate_comprehensive_similarity(
                    test_cases[id1],
                    test_cases[id2]
                )
                similarities.append(result["overall"])
        
        max_sim = max(similarities) if similarities else 0.0
        avg_sim = sum(similarities) / len(similarities) if similarities else 0.0
        
        # Determine which test case to keep
        recommended_keep = self._select_best_representative(group_list, test_cases)
        recommended_remove = [tid for tid in group_list if tid != recommended_keep]
        
        return {
            "test_case_ids": group_list,
            "recommended_keep": recommended_keep,
            "recommended_remove": recommended_remove,
            "max_similarity": max_sim,
            "average_similarity": avg_sim,
            "reason": self._get_recommendation_reason(recommended_keep, test_cases[recommended_keep])
        }
    
    def _select_best_representative(
        self, 
        group: List[int], 
        test_cases: Dict[int, TestCase]
    ) -> int:
        """
        Select the best test case to keep from a duplicate group.
        
        Criteria (in order of priority):
        1. Higher priority (lower number = higher priority)
        2. Better pass rate (if available)
        3. Shorter duration (faster execution)
        4. More steps (more comprehensive)
        5. Lower ID (arbitrary tie-breaker)
        
        Args:
            group: List of test case IDs in the group
            test_cases: All test cases
            
        Returns:
            Test case ID to keep
        """
        best_id = group[0]
        best_score = self._calculate_quality_score(test_cases[best_id])
        
        for test_id in group[1:]:
            score = self._calculate_quality_score(test_cases[test_id])
            if score > best_score:
                best_score = score
                best_id = test_id
        
        return best_id
    
    def _calculate_quality_score(self, test_case: TestCase) -> float:
        """
        Calculate a quality score for a test case (higher is better).
        
        Args:
            test_case: The TestCase object
            
        Returns:
            Quality score
        """
        score = 0.0
        
        # Priority (lower number = higher priority, so invert)
        if test_case.priority is not None:
            # Priority 1 = best, Priority 5 = worst
            # Convert: 1 -> 5 points, 2 -> 4 points, etc.
            priority_score = max(0, 6 - test_case.priority) if test_case.priority > 0 else 0
            score += priority_score * 10
        
        # Pass rate (if available)
        if test_case.pass_count is not None and test_case.fail_count is not None:
            total = test_case.pass_count + test_case.fail_count
            if total > 0:
                pass_rate = test_case.pass_count / total
                score += pass_rate * 20
        
        # Execution time (shorter is better, so invert)
        if test_case.duration is not None:
            # Normalize: shorter duration = higher score
            # Assuming max duration of 300000ms (5 minutes)
            time_score = max(0, 1.0 - (test_case.duration / 300000))
            score += time_score * 5
        
        # Number of steps (more comprehensive = better, but cap at reasonable limit)
        step_count = len(test_case.steps)
        step_score = min(step_count / 50.0, 1.0)  # Normalize to 0-1, cap at 50 steps
        score += step_score * 3
        
        return score
    
    def _get_recommendation_reason(self, test_id: int, test_case: TestCase) -> str:
        """
        Generate a human-readable reason for keeping a test case.
        
        Args:
            test_id: Test case ID
            test_case: The TestCase object
            
        Returns:
            Reason string
        """
        reasons = []
        
        if test_case.priority is not None:
            reasons.append(f"Priority {test_case.priority}")
        
        if test_case.pass_count is not None and test_case.fail_count is not None:
            total = test_case.pass_count + test_case.fail_count
            if total > 0:
                pass_rate = (test_case.pass_count / total) * 100
                reasons.append(f"{pass_rate:.1f}% pass rate")
        
        if test_case.duration is not None:
            duration_sec = test_case.duration / 1000
            reasons.append(f"{duration_sec:.1f}s execution time")
        
        if reasons:
            return ", ".join(reasons)
        return "Selected as representative"

