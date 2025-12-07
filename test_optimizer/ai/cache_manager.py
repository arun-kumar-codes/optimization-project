"""
caching for AI analysis results.
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from config.ai_config import AIConfig


class AICacheManager:
    """Manages caching for AI analysis results."""
    
    def __init__(self):

        self.cache_dir = AIConfig.get_cache_dir() if AIConfig.CACHE_ENABLED else None
        self.cache_file = self.cache_dir / "semantic_duplicates.json" if self.cache_dir else None
        
    def _generate_cache_key(self, test_case_id1: int, test_case_id2: int) -> str:
        
        sorted_ids = tuple(sorted([test_case_id1, test_case_id2]))
        return f"{sorted_ids[0]}_{sorted_ids[1]}"
    
    def _generate_content_hash(self, test_case1_data: Dict, test_case2_data: Dict) -> str:
        
        content_str = json.dumps({
            "name1": test_case1_data.get("name", ""),
            "desc1": test_case1_data.get("description", ""),
            "steps1": test_case1_data.get("steps_summary", ""),
            "name2": test_case2_data.get("name", ""),
            "desc2": test_case2_data.get("description", ""),
            "steps2": test_case2_data.get("steps_summary", "")
        }, sort_keys=True)
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def get_cached_result(
        self, 
        test_case_id1: int, 
        test_case_id2: int,
        test_case1_data: Dict,
        test_case2_data: Dict
    ) -> Optional[Dict]:
        """
        Get cached AI result if available and not expired.
        
        Args:
            test_case_id1: First test case ID
            test_case_id2: Second test case ID
            test_case1_data: Test case 1 data for content hash
            test_case2_data: Test case 2 data for content hash
            
        Returns:
            Cached result dict or None if not found/expired
        """
        if not AIConfig.CACHE_ENABLED or not self.cache_file or not self.cache_file.exists():
            return None
        
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            cache_key = self._generate_cache_key(test_case_id1, test_case_id2)
            
            if cache_key not in cache_data:
                return None
            
            cached_entry = cache_data[cache_key]
            
            cached_time = datetime.fromisoformat(cached_entry["timestamp"])
            expiry_time = cached_time + timedelta(days=AIConfig.CACHE_EXPIRY_DAYS)
            
            if datetime.now() > expiry_time:
                del cache_data[cache_key]
                with open(self.cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                return None
            
            content_hash = self._generate_content_hash(test_case1_data, test_case2_data)
            if cached_entry.get("content_hash") != content_hash:
                return None
            
            return cached_entry.get("result")
            
        except Exception as e:
            print(f"  [CACHE] Warning: Failed to read cache: {e}")
            return None
    
    def cache_result(
        self,
        test_case_id1: int,
        test_case_id2: int,
        test_case1_data: Dict,
        test_case2_data: Dict,
        result: Dict
    ):
        """
        Cache AI analysis result.
        
        Args:
            test_case_id1: First test case ID
            test_case_id2: Second test case ID
            test_case1_data: Test case 1 data for content hash
            test_case2_data: Test case 2 data for content hash
            result: AI analysis result to cache
        """
        if not AIConfig.CACHE_ENABLED or not self.cache_file:
            return
        
        try:
            cache_data = {}
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
            
            cache_key = self._generate_cache_key(test_case_id1, test_case_id2)
            content_hash = self._generate_content_hash(test_case1_data, test_case2_data)
            
            cache_data[cache_key] = {
                "timestamp": datetime.now().isoformat(),
                "content_hash": content_hash,
                "result": result
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            print(f"  [CACHE] Warning: Failed to write cache: {e}")
    
    def clear_cache(self):
        """Clear all cached results."""
        if self.cache_file and self.cache_file.exists():
            self.cache_file.unlink()
            print("  [CACHE] Cleared cache")

