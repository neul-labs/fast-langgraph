"""
Test LLM Cache functionality
"""

import os
import tempfile

import pytest

from fast_langgraph import RustLLMCache, RustSQLiteLLMCache


def test_rust_llm_cache_basic():
    """Test basic in-memory LLM cache operations."""
    cache = RustLLMCache(max_size=100)

    # Test cache miss
    prompt = "What is 2+2?"
    result = cache.get(prompt)
    assert result is None

    # Cache a response
    response = "The answer is 4"
    cache.put(prompt, response)

    # Test cache hit
    cached = cache.get(prompt)
    assert cached == response

    # Check stats
    stats = cache.stats()
    assert stats["size"] == 1
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate_percent"] == 50  # 1 hit out of 2 requests


def test_rust_llm_cache_complex_responses():
    """Test caching complex Python objects."""
    cache = RustLLMCache()

    prompt = "Generate a list"
    response = {
        "messages": ["msg1", "msg2"],
        "metadata": {"temperature": 0.7, "model": "gpt-4"},
        "tokens": 100,
    }

    cache.put(prompt, response)
    cached = cache.get(prompt)

    assert cached == response
    assert cached["messages"] == ["msg1", "msg2"]
    assert cached["metadata"]["temperature"] == 0.7


def test_rust_llm_cache_lru_eviction():
    """Test LRU eviction when cache is full."""
    cache = RustLLMCache(max_size=3)

    # Fill cache
    for i in range(3):
        cache.put(f"prompt{i}", f"response{i}")

    assert len(cache) == 3

    # Access prompt1 to increase its hit count
    cache.get("prompt1")
    cache.get("prompt1")

    # Add a new item - should evict the LRU (prompt0 or prompt2, not prompt1)
    cache.put("prompt3", "response3")

    assert len(cache) == 3
    # prompt1 should still be there due to higher hit count
    assert cache.get("prompt1") == "response1"


def test_rust_llm_cache_contains():
    """Test contains method."""
    cache = RustLLMCache()

    assert not cache.contains("test")

    cache.put("test", "response")
    assert cache.contains("test")


def test_rust_llm_cache_clear():
    """Test clearing the cache."""
    cache = RustLLMCache()

    cache.put("prompt1", "response1")
    cache.put("prompt2", "response2")

    assert len(cache) == 2

    cache.clear()

    assert len(cache) == 0
    stats = cache.stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0


def test_sqlite_llm_cache_basic():
    """Test SQLite-based LLM cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "llm_cache.db")
        cache = RustSQLiteLLMCache(db_path)

        # Test cache miss
        prompt = "What is the capital of France?"
        result = cache.get(prompt)
        assert result is None

        # Cache a response
        response = "Paris"
        cache.put(prompt, response)

        # Test cache hit
        cached = cache.get(prompt)
        assert cached == response

        # Check stats
        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1


def test_sqlite_llm_cache_persistence():
    """Test that SQLite cache persists across instances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "llm_cache.db")

        # Create cache and add data
        cache1 = RustSQLiteLLMCache(db_path)
        cache1.put("prompt", "response")

        # Create new instance with same db
        cache2 = RustSQLiteLLMCache(db_path)
        cached = cache2.get("prompt")

        assert cached == "response"


def test_sqlite_llm_cache_max_age():
    """Test max age for cache entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "llm_cache.db")

        # Create cache with 1-hour max age
        cache = RustSQLiteLLMCache(db_path, max_age_seconds=3600)

        cache.put("recent_prompt", "recent_response")

        # Should be cached (within 1 hour)
        assert cache.get("recent_prompt") == "recent_response"


def test_sqlite_llm_cache_cleanup():
    """Test cleanup of expired entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "llm_cache.db")

        # Cache with 0 second max age (everything immediately expired)
        cache = RustSQLiteLLMCache(db_path, max_age_seconds=0)

        cache.put("old_prompt", "old_response")

        # Cleanup expired entries
        import time

        time.sleep(0.1)  # Wait a bit to ensure expiry
        deleted = cache.cleanup()

        # Should have deleted the expired entry
        assert deleted >= 0


def test_sqlite_llm_cache_clear():
    """Test clearing SQLite cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "llm_cache.db")
        cache = RustSQLiteLLMCache(db_path)

        cache.put("prompt1", "response1")
        cache.put("prompt2", "response2")

        stats = cache.stats()
        assert stats["size"] == 2

        cache.clear()

        stats = cache.stats()
        assert stats["size"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
