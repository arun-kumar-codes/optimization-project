
import os
from pathlib import Path
from typing import Optional


class AIConfig:
    """Configuration for AI analysis settings."""
    
    # Rate limiting settings
    RATE_LIMIT_DELAY = float(os.getenv("AI_RATE_LIMIT_DELAY", "12.0"))  # Seconds between requests (API limit: 5/min = 12s)
    
    # Semantic duplicate detection settings
    SEMANTIC_DUPLICATE_CANDIDATE_LIMIT = int(os.getenv("AI_SEMANTIC_CANDIDATE_LIMIT", "30"))  # Max candidates to check
    SEMANTIC_DUPLICATE_SIMILARITY_THRESHOLD = float(os.getenv("AI_SEMANTIC_THRESHOLD", "0.85"))  # Min similarity to consider duplicate
    SEMANTIC_DUPLICATE_ALGO_SIMILARITY_MIN = float(os.getenv("AI_SEMANTIC_ALGO_MIN", "0.30"))  # Min algorithmic similarity to check
    SEMANTIC_DUPLICATE_ALGO_SIMILARITY_MAX = float(os.getenv("AI_SEMANTIC_ALGO_MAX", "0.75"))  # Max algorithmic similarity to check
    
    # Caching settings
    CACHE_ENABLED = os.getenv("AI_CACHE_ENABLED", "true").lower() == "true"
    
    _test_optimizer_root = Path(__file__).parent.parent
    CACHE_DIR = _test_optimizer_root / ".ai_cache"
    CACHE_EXPIRY_DAYS = int(os.getenv("AI_CACHE_EXPIRY_DAYS", "30"))  # Cache results for 30 days
    
    PHASE4_ENABLED = os.getenv("AI_PHASE4_ENABLED", "false").lower() == "true"  # Disabled by default
    
    @classmethod
    def get_cache_dir(cls) -> Path:
        """Get cache directory, creating it if needed."""
        if cls.CACHE_ENABLED:
            cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return cls.CACHE_DIR
    
    @classmethod
    def get_smart_candidate_limit(cls, total_candidates: int, total_test_cases: int) -> int:
        """
        Calculate smart candidate limit based on test suite size.
        Scales with number of test cases for future growth.
        
        Args:
            total_candidates: Total number of candidate pairs
            total_test_cases: Total number of test cases
            
        Returns:
            Smart limit based on test suite size
        """
        base_limit = cls.SEMANTIC_DUPLICATE_CANDIDATE_LIMIT
        
        # Scale with test suite size
        # For small suites (<50): use base limit
        # For medium suites (50-100): increase by 50%
        # For large suites (100-200): increase by 100%
        # For very large suites (>200): increase by 150%
        if total_test_cases < 50:
            multiplier = 1.0
        elif total_test_cases < 100:
            multiplier = 1.5
        elif total_test_cases < 200:
            multiplier = 2.0
        else:
            multiplier = 2.5
        
        smart_limit = int(base_limit * multiplier)
        
        return min(smart_limit, total_candidates)

