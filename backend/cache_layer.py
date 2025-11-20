"""
Smart caching layer for search results, embeddings, and LLM responses.
Uses diskcache for persistent storage with TTL expiration.
"""

import hashlib
import json
from typing import Any, Optional, Dict, List
from diskcache import Cache
import os

class CacheLayer:
    def __init__(self, cache_dir: str = "./cache", ttl: int = 3600):
        """
        Initialize cache layer.
        
        Args:
            cache_dir: Directory to store cache files
            ttl: Time-to-live for cache entries in seconds (default 1 hour)
        """
        self.cache_dir = cache_dir
        self.ttl = ttl
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        # Separate caches for different types of data
        self.query_cache = Cache(os.path.join(cache_dir, "queries"))
        self.embedding_cache = Cache(os.path.join(cache_dir, "embeddings"))
        self.search_cache = Cache(os.path.join(cache_dir, "search_results"))
        
        self.hits = 0
        self.misses = 0
    
    def _hash_key(self, key: str) -> str:
        """Generate a hash for the key."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def get_query_result(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Get cached result for a query.
        
        Args:
            query: The search query
            
        Returns:
            Cached result or None if not found
        """
        key = self._hash_key(query.lower().strip())
        result = self.query_cache.get(key)
        
        if result:
            self.hits += 1
        else:
            self.misses += 1
            
        return result
    
    def set_query_result(self, query: str, result: Dict[str, Any]) -> None:
        """
        Cache a query result.
        
        Args:
            query: The search query
            result: The result to cache
        """
        key = self._hash_key(query.lower().strip())
        self.query_cache.set(key, result, expire=self.ttl)
    
    def get_embeddings(self, text: str) -> Optional[List[float]]:
        """
        Get cached embeddings for text.
        
        Args:
            text: The text to get embeddings for
            
        Returns:
            Cached embeddings or None if not found
        """
        key = self._hash_key(text)
        return self.embedding_cache.get(key)
    
    def set_embeddings(self, text: str, embeddings: List[float]) -> None:
        """
        Cache embeddings for text.
        
        Args:
            text: The text
            embeddings: The embeddings to cache
        """
        key = self._hash_key(text)
        # Embeddings don't expire as frequently
        self.embedding_cache.set(key, embeddings, expire=self.ttl * 24)
    
    def get_search_results(self, query: str) -> Optional[List[Dict[str, str]]]:
        """
        Get cached search results.
        
        Args:
            query: The search query
            
        Returns:
            Cached search results or None if not found
        """
        key = self._hash_key(query.lower().strip())
        result = self.search_cache.get(key)
        
        if result:
            self.hits += 1
        else:
            self.misses += 1
            
        return result
    
    def set_search_results(self, query: str, results: List[Dict[str, str]]) -> None:
        """
        Cache search results.
        
        Args:
            query: The search query
            results: The search results to cache
        """
        key = self._hash_key(query.lower().strip())
        self.search_cache.set(key, results, expire=self.ttl)
    
    def clear_all(self) -> None:
        """Clear all caches."""
        self.query_cache.clear()
        self.embedding_cache.clear()
        self.search_cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "query_cache_size": len(self.query_cache),
            "embedding_cache_size": len(self.embedding_cache),
            "search_cache_size": len(self.search_cache)
        }
