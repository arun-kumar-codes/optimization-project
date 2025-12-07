"""
Module for detecting and grouping duplicate test cases.
"""

from typing import Dict, List, Set, Tuple, Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from analysis.similarity_analyzer import SimilarityAnalyzer


class DuplicateDetector:
    """Detects duplicate and highly similar test cases using algorithms and AI."""
    
    def __init__(
        self, 
        exact_threshold: float = 1.0,
        near_duplicate_threshold: float = 0.90,
        highly_similar_threshold: float = 0.75,
        use_ai_semantic: bool = False,
        ai_semantic_analyzer = None
    ):
        """
        Initialize duplicate detector with similarity thresholds.
        
        Args:
            exact_threshold: Threshold for exact duplicates (default: 1.0 = 100%)
            near_duplicate_threshold: Threshold for near duplicates (default: 0.90 = 90%)
            highly_similar_threshold: Threshold for highly similar (default: 0.75 = 75%)
            use_ai_semantic: If True, use AI for semantic duplicate detection
            ai_semantic_analyzer: Optional SemanticAnalyzer instance for AI semantic detection
        """
        self.exact_threshold = exact_threshold
        self.near_duplicate_threshold = near_duplicate_threshold
        self.highly_similar_threshold = highly_similar_threshold
        self.similarity_analyzer = SimilarityAnalyzer()
        self.use_ai_semantic = use_ai_semantic
        self.ai_semantic_analyzer = ai_semantic_analyzer
    
    def detect_duplicates(
        self, 
        test_cases: Dict[int, TestCase],
        use_ai_semantic: Optional[bool] = None
    ) -> Dict[str, List[Dict]]:
        """
        Detect all types of duplicates and group them (algorithmic + AI semantic).
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            use_ai_semantic: Override AI semantic detection flag
            
        Returns:
            Dictionary with duplicate groups categorized by type
        """
        print(f"  [DUPLICATE DETECTOR] Starting duplicate detection on {len(test_cases)} test cases...")
        
        print(f"  [DUPLICATE DETECTOR] Step 1: Finding structural duplicates (threshold: {self.highly_similar_threshold:.0%})...")
        similar_pairs = self.similarity_analyzer.find_similar_test_cases(
            test_cases,
            threshold=self.highly_similar_threshold
        )
        print(f"  [DUPLICATE DETECTOR] Found {len(similar_pairs)} similar pairs using algorithms")
        
        
        ai_semantic_pairs = []
        if (use_ai_semantic if use_ai_semantic is not None else self.use_ai_semantic):
            if self.ai_semantic_analyzer:
                print(f"  [DUPLICATE DETECTOR] Step 2: Finding semantic duplicates using AI...")
                ai_semantic_pairs = self._find_ai_semantic_duplicates(test_cases, similar_pairs)
                print(f"  [DUPLICATE DETECTOR] AI found {len(ai_semantic_pairs)} additional semantic duplicate pairs")
            else:
                print(f"  [DUPLICATE DETECTOR] Step 2: AI semantic detection disabled (no analyzer)")
        else:
            print(f"  [DUPLICATE DETECTOR] Step 2: AI semantic detection disabled (flag=False)")
        
        print(f"  [DUPLICATE DETECTOR] Step 3: Combining algorithmic and AI results...")
        all_similar_pairs = similar_pairs.copy()
        
        algorithmic_pair_set = {(min(id1, id2), max(id1, id2)) for id1, id2, _ in similar_pairs}
        new_ai_pairs = 0
        for id1, id2, similarity in ai_semantic_pairs:
            pair_key = (min(id1, id2), max(id1, id2))
            if pair_key not in algorithmic_pair_set:
                all_similar_pairs.append((id1, id2, similarity))
                algorithmic_pair_set.add(pair_key)
                new_ai_pairs += 1
        print(f"  [DUPLICATE DETECTOR] Combined: {len(similar_pairs)} algorithmic + {new_ai_pairs} new AI = {len(all_similar_pairs)} total pairs")
        
        print(f"  [DUPLICATE DETECTOR] Step 4: Building similarity graph and finding groups...")
        exact_duplicates = []
        near_duplicates = []
        highly_similar = []
        
        # Build graph of similarities
        similarity_graph = self._build_similarity_graph(all_similar_pairs)
        print(f"  [DUPLICATE DETECTOR] Similarity graph has {len(similarity_graph)} nodes")
        
        # Find connected components (duplicate groups)
        groups = self._find_connected_components(similarity_graph, test_cases)
        print(f"  [DUPLICATE DETECTOR] Found {len(groups)} connected groups")
        
        # Step 5: Categorize groups
        print(f"  [DUPLICATE DETECTOR] Step 5: Categorizing groups...")
        for group in groups:
            group_info = self._analyze_group(group, test_cases)
            
            # Debug: Show which test cases are being compared
            if len(group_info["test_case_ids"]) > 1:
                group_ids_str = ", ".join([f"TC{tid}" for tid in group_info["test_case_ids"]])
                print(f"    Group: [{group_ids_str}] - Max similarity: {group_info['max_similarity']:.1%}, Keep: TC{group_info['recommended_keep']}")
            
            if group_info["max_similarity"] >= self.exact_threshold:
                exact_duplicates.append(group_info)
            elif group_info["max_similarity"] >= self.near_duplicate_threshold:
                near_duplicates.append(group_info)
            elif group_info["max_similarity"] >= self.highly_similar_threshold:
                highly_similar.append(group_info)
        
        print(f"  [DUPLICATE DETECTOR] Categorized: {len(exact_duplicates)} exact, {len(near_duplicates)} near, {len(highly_similar)} highly similar")
        
        return {
            "exact_duplicates": exact_duplicates,
            "near_duplicates": near_duplicates,
            "highly_similar": highly_similar,
            "total_groups": len(exact_duplicates) + len(near_duplicates) + len(highly_similar),
            "ai_semantic_pairs_found": len(ai_semantic_pairs)
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
                if len(component) > 1: 
                    components.append(component)
        
      
        all_ids = set(test_cases.keys())
        grouped_ids = set()
        for component in components:
            grouped_ids.update(component)
        
        isolated = all_ids - grouped_ids
        for test_id in isolated:
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
        
        if test_case.priority is not None:
            
            priority_score = max(0, 6 - test_case.priority) if test_case.priority > 0 else 0
            score += priority_score * 10
        
        if test_case.pass_count is not None and test_case.fail_count is not None:
            total = test_case.pass_count + test_case.fail_count
            if total > 0:
                pass_rate = test_case.pass_count / total
                score += pass_rate * 20
        
        if test_case.duration is not None:
            
            time_score = max(0, 1.0 - (test_case.duration / 300000))
            score += time_score * 5
        
        step_count = len(test_case.steps)
        step_score = min(step_count / 50.0, 1.0) 
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
    
    def _find_ai_semantic_duplicates(
        self,
        test_cases: Dict[int, TestCase],
        algorithmic_pairs: List[Tuple[int, int, float]],
        ai_similarity_threshold: float = 0.85
    ) -> List[Tuple[int, int, float]]:
        """
        Use AI to find semantic duplicates that algorithms missed.
        
        Strategy:
        - Focus on pairs with low algorithmic similarity (30-75%)
        - These might be semantic duplicates (same meaning, different words)
        - Use AI to check if they're actually duplicates
        
        Args:
            test_cases: All test cases
            algorithmic_pairs: Pairs already found by algorithms
            ai_similarity_threshold: Minimum AI similarity to consider (default: 0.85)
            
        Returns:
            List of (id1, id2, ai_similarity) tuples for semantic duplicates
        """
        if not self.ai_semantic_analyzer:
            return []
        
        semantic_pairs = []
        algorithmic_pair_set = {(min(id1, id2), max(id1, id2)) for id1, id2, _ in algorithmic_pairs}
        
        test_case_ids = list(test_cases.keys())
        candidate_pairs = []
        
        for i in range(len(test_case_ids)):
            for j in range(i + 1, len(test_case_ids)):
                id1 = test_case_ids[i]
                id2 = test_case_ids[j]
                pair_key = (min(id1, id2), max(id1, id2))
                
                if pair_key in algorithmic_pair_set:
                    continue
                
                algo_result = self.similarity_analyzer.calculate_comprehensive_similarity(
                    test_cases[id1],
                    test_cases[id2]
                )
                algo_similarity = algo_result["overall"]
                
                try:
                    from config.ai_config import AIConfig
                    min_sim = AIConfig.SEMANTIC_DUPLICATE_ALGO_SIMILARITY_MIN
                    max_sim = AIConfig.SEMANTIC_DUPLICATE_ALGO_SIMILARITY_MAX
                except ImportError:
                    min_sim = 0.30
                    max_sim = 0.75
                
               
                if min_sim <= algo_similarity < max_sim:
                    candidate_pairs.append((id1, id2, algo_similarity))
        
        
        candidate_pairs.sort(key=lambda x: x[2], reverse=True)
        
        try:
            from config.ai_config import AIConfig
            max_ai_checks = AIConfig.get_smart_candidate_limit(
                len(candidate_pairs),
                len(test_cases)
            )
        except ImportError:
            max_ai_checks = min(30, len(candidate_pairs))  # Default: top 30 candidates
        
        candidate_pairs = candidate_pairs[:max_ai_checks]
        
        print(f"  Checking {len(candidate_pairs)} candidate pairs with AI for semantic duplicates (limit: {max_ai_checks})...")
        
        for id1, id2, algo_sim in candidate_pairs:
            try:
                ai_result = self.ai_semantic_analyzer.identify_semantic_duplicates(
                    test_cases[id1],
                    test_cases[id2]
                )
                ai_similarity = ai_result.get("semantic_similarity", 0.0)
                
                if ai_similarity >= ai_similarity_threshold:
                    semantic_pairs.append((id1, id2, ai_similarity))
                    print(f"    AI found semantic duplicate: TC{id1} & TC{id2} ({ai_similarity:.1%} similar)")
            except Exception as e:
                print(f"    Warning: AI check failed for TC{id1} & TC{id2}: {e}")
                continue
        
        return semantic_pairs

