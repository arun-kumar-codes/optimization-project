"""
Module for calculating similarity between test cases using multiple algorithms.
"""

from typing import Dict, Tuple, List, Optional
from Levenshtein import distance as levenshtein_distance
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.models import TestCase
from analysis.sequence_extractor import SequenceExtractor


class SimilarityAnalyzer:
    """Analyzes similarity between test cases using multiple techniques."""
    
    def __init__(self):
        self.sequence_extractor = SequenceExtractor()
    
    def calculate_sequence_similarity(
        self, 
        test_case1: TestCase, 
        test_case2: TestCase
    ) -> float:
        """
        Calculate similarity based on action sequences using Levenshtein distance.
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            
        Returns:
            Similarity score from 0.0 to 1.0 (1.0 = identical)
        """
        seq1 = self.sequence_extractor.extract_action_sequence(test_case1)
        seq2 = self.sequence_extractor.extract_action_sequence(test_case2)
        
        if not seq1 and not seq2:
            return 1.0
        if not seq1 or not seq2:
            return 0.0
        
        # Convert sequences to strings for Levenshtein
        str1 = " ".join(seq1)
        str2 = " ".join(seq2)
        
        # Calculate Levenshtein distance
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 1.0
        
        distance = levenshtein_distance(str1, str2)
        similarity = 1.0 - (distance / max_len)
        
        return max(0.0, similarity)
    
    def calculate_lcs_similarity(
        self, 
        test_case1: TestCase, 
        test_case2: TestCase
    ) -> Tuple[float, int]:
        """
        Calculate similarity using Longest Common Subsequence (LCS).
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            
        Returns:
            Tuple of (similarity_score, lcs_length)
        """
        seq1 = self.sequence_extractor.extract_action_sequence(test_case1)
        seq2 = self.sequence_extractor.extract_action_sequence(test_case2)
        
        similarity, lcs_length = self.sequence_extractor.compare_sequences(seq1, seq2)
        return similarity, lcs_length
    
    def calculate_step_level_similarity(
        self, 
        test_case1: TestCase, 
        test_case2: TestCase
    ) -> float:
        """
        Calculate similarity by comparing individual steps.
        CRITICAL: Considers URLs/websites - different websites = lower similarity.
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            
        Returns:
            Similarity score from 0.0 to 1.0
        """
        steps1 = sorted(test_case1.steps, key=lambda s: s.position)
        steps2 = sorted(test_case2.steps, key=lambda s: s.position)
        
        if not steps1 and not steps2:
            return 1.0
        if not steps1 or not steps2:
            return 0.0
        
        # Extract URLs/websites from both test cases
        urls1 = self._extract_urls_from_test_case(test_case1)
        urls2 = self._extract_urls_from_test_case(test_case2)
        domains1 = self._extract_domains(urls1)
        domains2 = self._extract_domains(urls2)
        
        website_penalty = 0.0
        if domains1 and domains2:
            if not domains1.intersection(domains2):
                website_penalty = 0.5  
            elif domains1 != domains2:
                website_penalty = 0.2 
        
        # Compare steps pairwise
        max_steps = max(len(steps1), len(steps2))
        matches = 0
        
        for i in range(min(len(steps1), len(steps2))):
            step1 = steps1[i]
            step2 = steps2[i]
            
            # Compare action name
            if step1.action_name == step2.action_name:
                matches += 0.4
            
            # Compare element
            if step1.element and step2.element:
                if step1.element.lower() == step2.element.lower():
                    matches += 0.3
            elif not step1.element and not step2.element:
                matches += 0.3
            
            # Compare description 
            if step1.description and step2.description:
                desc_sim = self._fuzzy_string_similarity(
                    step1.description, 
                    step2.description
                )
                matches += desc_sim * 0.3
            
            if step1.action_name == "navigateTo" and step2.action_name == "navigateTo":
                url1 = self._extract_url_from_step(step1)
                url2 = self._extract_url_from_step(step2)
                if url1 and url2:
                    domain1 = self._extract_domain_from_url(url1)
                    domain2 = self._extract_domain_from_url(url2)
                    if domain1 and domain2 and domain1 != domain2:
                        matches *= 0.5 
        
        similarity = matches / max_steps if max_steps > 0 else 0.0
        
        # Apply website penalty
        similarity = similarity * (1.0 - website_penalty)
        
        return min(1.0, similarity)
    
    def calculate_flow_pattern_similarity(
        self, 
        test_case1: TestCase, 
        test_case2: TestCase
    ) -> float:
        """
        Calculate similarity based on abstracted flow patterns.
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            
        Returns:
            Similarity score from 0.0 to 1.0
        """
        pattern1 = self.sequence_extractor.extract_flow_pattern(test_case1)
        pattern2 = self.sequence_extractor.extract_flow_pattern(test_case2)
        
        similarity, _ = self.sequence_extractor.compare_sequences(pattern1, pattern2)
        return similarity
    
    def calculate_comprehensive_similarity(
        self, 
        test_case1: TestCase, 
        test_case2: TestCase,
        weights: Dict[str, float] = None
    ) -> Dict[str, float]:
        """
        Calculate comprehensive similarity using multiple methods.
        CRITICAL: Applies website/URL penalty if test cases target different websites.
        
        Args:
            test_case1: First test case
            test_case2: Second test case
            weights: Optional weights for different similarity methods
            
        Returns:
            Dictionary with similarity scores for each method and overall score
        """
        if weights is None:
            weights = {
                "sequence": 0.3,
                "lcs": 0.3,
                "step_level": 0.2,
                "flow_pattern": 0.2
            }
        
        urls1 = self._extract_urls_from_test_case(test_case1)
        urls2 = self._extract_urls_from_test_case(test_case2)
        domains1 = self._extract_domains(urls1)
        domains2 = self._extract_domains(urls2)
        
        name1 = (test_case1.name or "").lower()
        name2 = (test_case2.name or "").lower()
        desc1 = (test_case1.description or "").lower()
        desc2 = (test_case2.description or "").lower()
        
        website_keyword_map = {
            "amazon": "amazon.com",
            "ebay": "ebay.com",
            "walmart": "walmart.com",
            "target": "target.com",
            "etsy": "etsy.com",
            "shopify": "shopify.com",
            "facebook": "facebook.com",
            "twitter": "twitter.com",
            "x.com": "twitter.com",  
            "linkedin": "linkedin.com",
            "instagram": "instagram.com",
            "youtube": "youtube.com",
            "google": "google.com",
            "microsoft": "microsoft.com",
            "apple": "apple.com",
            "netflix": "netflix.com",
            "spotify": "spotify.com",
            "github": "github.com",
            "stackoverflow": "stackoverflow.com",
            "reddit": "reddit.com",
            "pinterest": "pinterest.com"
        }
        
        # Extract websites from names/descriptions
        websites_in_tc1 = set()
        websites_in_tc2 = set()
        
        text1 = f"{name1} {desc1}"
        text2 = f"{name2} {desc2}"
        
        for keyword, domain in website_keyword_map.items():
            if keyword in text1:
                websites_in_tc1.add(domain)
            if keyword in text2:
                websites_in_tc2.add(domain)
        
        # Also check for domain patterns in text
        import re
        domain_pattern = r'\b([a-z0-9-]+\.(?:com|org|net|io|co|edu|gov|uk|ca|au|de|fr|jp|in))\b'
        domains_in_text1 = set(re.findall(domain_pattern, text1, re.IGNORECASE))
        domains_in_text2 = set(re.findall(domain_pattern, text2, re.IGNORECASE))
        
        # Normalize domains (remove www, lowercase)
        domains_in_text1 = {d.replace('www.', '').lower() for d in domains_in_text1}
        domains_in_text2 = {d.replace('www.', '').lower() for d in domains_in_text2}
        
        # Combine URL domains with keyword domains
        all_domains1 = domains1.union(websites_in_tc1).union(domains_in_text1)
        all_domains2 = domains2.union(websites_in_tc2).union(domains_in_text2)
        
        # Determine if different websites
        different_websites = False
        if all_domains1 and all_domains2:
            if not all_domains1.intersection(all_domains2):
                different_websites = True
        elif websites_in_tc1 and websites_in_tc2:
            if not websites_in_tc1.intersection(websites_in_tc2):
                different_websites = True
        
        # Calculate individual similarities
        seq_sim = self.calculate_sequence_similarity(test_case1, test_case2)
        lcs_sim, _ = self.calculate_lcs_similarity(test_case1, test_case2)
        step_sim = self.calculate_step_level_similarity(test_case1, test_case2)
        flow_sim = self.calculate_flow_pattern_similarity(test_case1, test_case2)
        
        # Calculate weighted overall similarity
        overall = (
            seq_sim * weights["sequence"] +
            lcs_sim * weights["lcs"] +
            step_sim * weights["step_level"] +
            flow_sim * weights["flow_pattern"]
        )
        
        if different_websites:
            overall = overall * 0.3  
        
        return {
            "overall": overall,
            "sequence_similarity": seq_sim,
            "lcs_similarity": lcs_sim,
            "step_level_similarity": step_sim,
            "flow_pattern_similarity": flow_sim,
            "different_websites": different_websites  
        }
    
    def _fuzzy_string_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate fuzzy string similarity using Levenshtein distance.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score from 0.0 to 1.0
        """
        if not str1 and not str2:
            return 1.0
        if not str1 or not str2:
            return 0.0
        
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()
        
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 1.0
        
        distance = levenshtein_distance(str1, str2)
        similarity = 1.0 - (distance / max_len)
        
        return max(0.0, similarity)
    
    def _extract_urls_from_test_case(self, test_case: TestCase) -> List[str]:
        """Extract all URLs from a test case."""
        urls = []
        for step in test_case.steps:
            url = self._extract_url_from_step(step)
            if url:
                urls.append(url)
        return urls
    
    def _extract_url_from_step(self, step) -> Optional[str]:
        """Extract URL from a step (from action, test_data, or description)."""
        import re
        
        # Check test_data first
        if step.test_data:
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            match = re.search(url_pattern, step.test_data)
            if match:
                return match.group(0)
        
        # Check action
        if step.action:
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            match = re.search(url_pattern, step.action)
            if match:
                return match.group(0)
        
        # Check description
        if step.description:
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            match = re.search(url_pattern, step.description)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_domain_from_url(self, url: str) -> Optional[str]:
        """Extract domain from URL."""
        import re
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split('/')[0]
            # Remove port if present
            domain = domain.split(':')[0]
            # Remove www. prefix for comparison
            domain = domain.replace('www.', '')
            return domain.lower() if domain else None
        except:
            # Fallback: simple regex extraction
            match = re.search(r'https?://(?:www\.)?([^/]+)', url)
            if match:
                return match.group(1).lower()
            return None
    
    def _extract_domains(self, urls: List[str]) -> set:
        """Extract unique domains from a list of URLs."""
        domains = set()
        for url in urls:
            domain = self._extract_domain_from_url(url)
            if domain:
                domains.add(domain)
        return domains
    
    def find_similar_test_cases(
        self, 
        test_cases: Dict[int, TestCase],
        threshold: float = 0.75
    ) -> List[Tuple[int, int, float]]:
        """
        Find pairs of similar test cases above a threshold.
        
        Args:
            test_cases: Dictionary of test case ID to TestCase objects
            threshold: Minimum similarity score to consider (0.0 to 1.0)
            
        Returns:
            List of tuples (test_case_id1, test_case_id2, similarity_score)
        """
        similar_pairs = []
        test_case_ids = list(test_cases.keys())
        
        # Compare all pairs
        for i in range(len(test_case_ids)):
            for j in range(i + 1, len(test_case_ids)):
                id1 = test_case_ids[i]
                id2 = test_case_ids[j]
                
                similarity_result = self.calculate_comprehensive_similarity(
                    test_cases[id1],
                    test_cases[id2]
                )
                
                overall_sim = similarity_result["overall"]
                
                if overall_sim >= threshold:
                    similar_pairs.append((id1, id2, overall_sim))
        
        # Sort by similarity (highest first)
        similar_pairs.sort(key=lambda x: x[2], reverse=True)
        
        return similar_pairs

