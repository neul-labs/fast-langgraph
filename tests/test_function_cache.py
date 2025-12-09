"""
Tests for Rust function caching module.
"""

import time

import pytest

from fast_langgraph import RustFunctionCache, RustTTLCache, cached


def test_rust_function_cache_basic():
    """Test basic cache operations."""
    cache = RustFunctionCache(max_size=100)

    # Initially empty
    assert len(cache) == 0

    # Put and get
    args = (1, 2, 3)
    result = "cached_result"
    cache.put(args, result)

    retrieved = cache.get(args)
    assert retrieved == result

    # Stats
    stats = cache.stats()
    assert stats["size"] == 1
    assert stats["hits"] == 1
    assert stats["misses"] == 0
    assert stats["hit_rate"] == 1.0


def test_rust_function_cache_with_kwargs():
    """Test cache with keyword arguments."""
    cache = RustFunctionCache(max_size=100)

    args = (1, 2)
    kwargs = {"x": 10, "y": 20}
    result = "result_with_kwargs"

    cache.put(args, result, kwargs)
    retrieved = cache.get(args, kwargs)

    assert retrieved == result


def test_rust_function_cache_contains():
    """Test contains method."""
    cache = RustFunctionCache(max_size=100)

    args = (1, 2, 3)
    assert not cache.contains(args)

    cache.put(args, "result")
    assert cache.contains(args)


def test_rust_function_cache_invalidate():
    """Test invalidate method."""
    cache = RustFunctionCache(max_size=100)

    args = (1, 2, 3)
    cache.put(args, "result")

    assert cache.contains(args)
    assert cache.invalidate(args)
    assert not cache.contains(args)

    # Invalidating non-existent entry
    assert not cache.invalidate((4, 5, 6))


def test_rust_function_cache_clear():
    """Test clearing cache."""
    cache = RustFunctionCache(max_size=100)

    for i in range(10):
        cache.put((i,), f"result_{i}")

    assert len(cache) == 10

    cache.clear()
    assert len(cache) == 0

    stats = cache.stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0


def test_rust_function_cache_lru_eviction():
    """Test LRU eviction when cache is full."""
    cache = RustFunctionCache(max_size=3)

    # Fill cache
    cache.put((1,), "result_1")
    cache.put((2,), "result_2")
    cache.put((3,), "result_3")

    assert len(cache) == 3

    # Access entry 1 and 2 to increase their hit count
    cache.get((1,))
    cache.get((2,))

    # Adding a 4th entry should evict entry 3 (lowest hits)
    cache.put((4,), "result_4")

    assert len(cache) == 3
    assert cache.contains((1,))
    assert cache.contains((2,))
    assert not cache.contains((3,))  # Evicted
    assert cache.contains((4,))


def test_rust_function_cache_miss():
    """Test cache miss behavior."""
    cache = RustFunctionCache(max_size=100)

    result = cache.get((1, 2, 3))
    assert result is None

    stats = cache.stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0


def test_cached_decorator_basic():
    """Test cached decorator basic functionality."""
    call_count = 0

    @cached
    def expensive_function(x, y):
        nonlocal call_count
        call_count += 1
        return x + y

    # First call - function is executed
    result1 = expensive_function(1, 2)
    assert result1 == 3
    assert call_count == 1

    # Second call with same args - cached
    result2 = expensive_function(1, 2)
    assert result2 == 3
    assert call_count == 1  # Not called again

    # Different args - function is executed
    result3 = expensive_function(3, 4)
    assert result3 == 7
    assert call_count == 2


def test_cached_decorator_with_kwargs():
    """Test cached decorator with keyword arguments."""
    call_count = 0

    @cached
    def function_with_kwargs(x, y=10, z=20):
        nonlocal call_count
        call_count += 1
        return x + y + z

    result1 = function_with_kwargs(1, y=2, z=3)
    assert result1 == 6
    assert call_count == 1

    # Same kwargs - cached
    result2 = function_with_kwargs(1, y=2, z=3)
    assert result2 == 6
    assert call_count == 1

    # Different kwargs - not cached
    result3 = function_with_kwargs(1, y=5, z=3)
    assert result3 == 9
    assert call_count == 2


def test_cached_decorator_stats():
    """Test cached decorator statistics."""

    @cached
    def func(x):
        return x * 2

    # Generate some hits and misses
    func(1)  # miss
    func(2)  # miss
    func(1)  # hit
    func(1)  # hit
    func(3)  # miss

    stats = func.cache_stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 3
    assert stats["size"] == 3
    assert abs(stats["hit_rate"] - 0.4) < 0.01  # 2/5 = 0.4


def test_cached_decorator_clear():
    """Test clearing decorator cache."""
    call_count = 0

    @cached
    def func(x):
        nonlocal call_count
        call_count += 1
        return x * 2

    func(1)
    func(1)
    assert call_count == 1  # Cached

    func.cache_clear()

    func(1)
    assert call_count == 2  # Called again after clear


def test_cached_decorator_contains():
    """Test checking if result is cached."""

    @cached
    def func(x, y=10):
        return x + y

    func(1, y=5)

    assert func.cache_contains(1, y=5)
    assert not func.cache_contains(2, y=5)


def test_cached_decorator_wrapped():
    """Test access to wrapped function."""

    def original_func(x):
        return x * 2

    decorated = cached(original_func)

    assert decorated.__wrapped__ is original_func


def test_ttl_cache_basic():
    """Test TTL cache basic operations."""
    cache = RustTTLCache(max_size=100, ttl=1.0)  # 1 second TTL

    args = (1, 2, 3)
    result = "cached_result"

    cache.put(args, result)
    retrieved = cache.get(args)

    assert retrieved == result


def test_ttl_cache_expiration():
    """Test TTL cache expiration."""
    cache = RustTTLCache(max_size=100, ttl=0.1)  # 100ms TTL

    args = (1, 2, 3)
    cache.put(args, "result")

    # Should be cached immediately
    assert cache.get(args) == "result"

    # Wait for expiration
    time.sleep(0.15)

    # Should be expired now
    result = cache.get(args)
    assert result is None


def test_ttl_cache_cleanup():
    """Test manual cleanup of expired entries."""
    cache = RustTTLCache(max_size=100, ttl=0.1)

    # Add some entries
    for i in range(5):
        cache.put((i,), f"result_{i}")

    stats = cache.stats()
    assert stats["size"] == 5

    # Wait for expiration
    time.sleep(0.15)

    # Clean up expired entries
    cleaned = cache.cleanup()
    assert cleaned == 5

    stats = cache.stats()
    assert stats["size"] == 0


def test_ttl_cache_stats():
    """Test TTL cache statistics."""
    cache = RustTTLCache(max_size=100, ttl=10.0)

    cache.put((1,), "result_1")
    cache.put((2,), "result_2")

    cache.get((1,))  # hit
    cache.get((1,))  # hit
    cache.get((3,))  # miss

    stats = cache.stats()
    assert stats["size"] == 2
    assert stats["max_size"] == 100
    assert stats["ttl"] == 10.0
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert abs(stats["hit_rate"] - 2.0 / 3.0) < 0.01


def test_ttl_cache_lru_eviction():
    """Test LRU eviction in TTL cache when full."""
    cache = RustTTLCache(max_size=3, ttl=10.0)

    # Fill cache
    cache.put((1,), "result_1")
    cache.put((2,), "result_2")
    cache.put((3,), "result_3")

    # Access some entries to increase hit count
    cache.get((1,))
    cache.get((2,))

    # Add 4th entry - should evict least used (entry 3)
    cache.put((4,), "result_4")

    assert cache.get((1,)) == "result_1"
    assert cache.get((2,)) == "result_2"
    assert cache.get((3,)) is None  # Evicted
    assert cache.get((4,)) == "result_4"


def test_cache_with_complex_objects():
    """Test caching with complex Python objects."""
    cache = RustFunctionCache(max_size=100)

    # Dict result
    args = (1,)
    result = {"key": "value", "nested": {"a": 1, "b": 2}}
    cache.put(args, result)
    retrieved = cache.get(args)
    assert retrieved == result

    # List result
    args = (2,)
    result = [1, 2, {"x": 10}]
    cache.put(args, result)
    retrieved = cache.get(args)
    assert retrieved == result


def test_cached_decorator_custom_size():
    """Test cached decorator with custom cache size."""

    @cached(max_size=2)
    def func(x):
        return x * 2

    func(1)
    func(2)
    func(3)  # Should evict one entry

    stats = func.cache_stats()
    assert stats["max_size"] == 2
    assert stats["size"] == 2


def test_cache_repr():
    """Test string representation of caches."""
    cache = RustFunctionCache(max_size=100)
    cache.put((1,), "result")
    cache.get((1,))  # hit
    cache.get((2,))  # miss

    repr_str = repr(cache)
    assert "RustFunctionCache" in repr_str
    assert "size=1/100" in repr_str
    assert "hits=1" in repr_str
    assert "misses=1" in repr_str


def test_decorator_repr():
    """Test string representation of decorated function."""

    @cached
    def my_function(x):
        return x * 2

    # The wrapper preserves the function name
    repr_str = repr(my_function)
    assert "my_function" in repr_str or "wrapper" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
