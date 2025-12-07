"""
Module for building flow graphs from test cases.
"""

from typing import Dict, List, Set, Tuple, Optional
import networkx as nx
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from flows.flow_analyzer import FlowAnalyzer


class FlowGraphBuilder:
    """Builds directed graphs representing user flows."""
    
    def __init__(self):
        self.flow_analyzer = FlowAnalyzer()
        self.graph = nx.DiGraph()
    
    def build_graph(self, test_cases: Dict[int, TestCase]) -> nx.DiGraph:
        """
        Build a directed graph of user flows.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            
        Returns:
            NetworkX directed graph
        """
        self.graph = nx.DiGraph()
        
        for test_id, test_case in test_cases.items():
            # Extract pages/URLs from test case
            pages = self._extract_pages(test_case)
            
            # Add pages as nodes
            for page in pages:
                if page not in self.graph:
                    self.graph.add_node(page, test_cases=set())
                self.graph.nodes[page]["test_cases"].add(test_id)
            
            # Add transitions as edges
            transitions = self.flow_analyzer.extract_page_transitions(test_case)
            for transition in transitions:
                from_page = transition["from"]
                to_page = transition["to"]
                
                if from_page and to_page:
                    if not self.graph.has_edge(from_page, to_page):
                        self.graph.add_edge(from_page, to_page, weight=0, test_cases=set())
                    
                    # Increment weight (frequency)
                    self.graph[from_page][to_page]["weight"] += 1
                    self.graph[from_page][to_page]["test_cases"].add(test_id)
        
        return self.graph
    
    def _extract_pages(self, test_case: TestCase) -> List[str]:
        """Extract unique pages/URLs from a test case."""
        pages = set()
        
        for step in test_case.steps:
            if step.action_name == "navigateto":
                url = self.flow_analyzer._extract_url_from_step(step)
                if url:
                    
                    normalized = self._normalize_url(url)
                    pages.add(normalized)
            elif step.action_name in ["click", "navigate"]:
                if step.element:
                    
                    pass
        
        return list(pages)
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing query params and fragments."""
        if "?" in url:
            url = url.split("?")[0]
        if "#" in url:
            url = url.split("#")[0]
        return url.rstrip("/")
    
    def identify_critical_paths(self, graph: nx.DiGraph, top_n: int = 10) -> List[Dict]:
        """
        Identify critical paths in the flow graph.
        
        Args:
            graph: The flow graph
            top_n: Number of top paths to return
            
        Returns:
            List of critical path dictionaries
        """
        critical_paths = []
        
        # Calculate path criticality based on edge weights and node importance
        for edge in graph.edges(data=True):
            from_node = edge[0]
            to_node = edge[1]
            weight = edge[2].get("weight", 0)
            test_cases = edge[2].get("test_cases", set())
            
           
            criticality = weight * 0.6 + len(test_cases) * 0.4
            
            critical_paths.append({
                "from": from_node,
                "to": to_node,
                "weight": weight,
                "test_case_count": len(test_cases),
                "test_case_ids": list(test_cases),
                "criticality_score": criticality
            })
        
        # Sort by criticality
        critical_paths.sort(key=lambda x: x["criticality_score"], reverse=True)
        
        return critical_paths[:top_n]
    
    def find_flow_coverage(self, graph: nx.DiGraph) -> Dict:
        """
        Analyze flow coverage from the graph.
        
        Args:
            graph: The flow graph
            
        Returns:
            Coverage analysis dictionary
        """
        total_nodes = graph.number_of_nodes()
        total_edges = graph.number_of_edges()
        
        # Count nodes with different frequencies
        high_frequency_nodes = 0  # Used by 3+ test cases
        medium_frequency_nodes = 0  # Used by 2 test cases
        low_frequency_nodes = 0  # Used by 1 test case
        
        for node in graph.nodes():
            test_case_count = len(graph.nodes[node].get("test_cases", set()))
            if test_case_count >= 3:
                high_frequency_nodes += 1
            elif test_case_count == 2:
                medium_frequency_nodes += 1
            else:
                low_frequency_nodes += 1
        
        # Count edges with different frequencies
        high_frequency_edges = 0
        medium_frequency_edges = 0
        low_frequency_edges = 0
        
        for edge in graph.edges(data=True):
            weight = edge[2].get("weight", 0)
            if weight >= 3:
                high_frequency_edges += 1
            elif weight == 2:
                medium_frequency_edges += 1
            else:
                low_frequency_edges += 1
        
        return {
            "total_pages": total_nodes,
            "total_transitions": total_edges,
            "high_frequency_pages": high_frequency_nodes,
            "medium_frequency_pages": medium_frequency_nodes,
            "low_frequency_pages": low_frequency_nodes,
            "high_frequency_transitions": high_frequency_edges,
            "medium_frequency_transitions": medium_frequency_edges,
            "low_frequency_transitions": low_frequency_edges
        }
    
    def get_page_flow_map(self, graph: nx.DiGraph) -> Dict[str, List[str]]:
        """
        Get a map of pages to their outgoing flows.
        
        Args:
            graph: The flow graph
            
        Returns:
            Dictionary mapping page to list of destination pages
        """
        flow_map = {}
        
        for node in graph.nodes():
            successors = list(graph.successors(node))
            if successors:
                flow_map[node] = successors
        
        return flow_map
    
    def find_dead_ends(self, graph: nx.DiGraph) -> List[str]:
        """
        Find dead-end pages (pages with no outgoing edges).
        
        Args:
            graph: The flow graph
            
        Returns:
            List of dead-end page URLs
        """
        dead_ends = []
        
        for node in graph.nodes():
            if graph.out_degree(node) == 0:
                dead_ends.append(node)
        
        return dead_ends
    
    def find_isolated_pages(self, graph: nx.DiGraph) -> List[str]:
        """
        Find isolated pages (pages with no connections).
        
        Args:
            graph: The flow graph
            
        Returns:
            List of isolated page URLs
        """
        isolated = []
        
        for node in graph.nodes():
            if graph.degree(node) == 0:
                isolated.append(node)
        
        return isolated

