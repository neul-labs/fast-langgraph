"""
Example usage of fast function caching.

This demonstrates how to use the Rust-based function caching
for memoization of expensive computations.
"""

import time
from fast_langgraph import RustFunctionCache, cached, RustTTLCache


def example_manual_cache():
    """Using RustFunctionCache manually."""
    print("=" * 60)
    print("Manual Function Cache Usage")
    print("=" * 60)

    cache = RustFunctionCache(max_size=100)

    def expensive_computation(x, y):
        """Simulate expensive computation."""
        time.sleep(0.1)
        return x * y + x + y

    # First call - cache miss
    print("First call (cache miss):")
    start = time.perf_counter()
    args = (10, 20)
    result = cache.get(args)
    if result is None:
        result = expensive_computation(*args)
        cache.put(args, result)
    elapsed = time.perf_counter() - start
    print(f"  Result: {result}, Time: {elapsed*1000:.2f} ms")

    # Second call - cache hit
    print("Second call (cache hit):")
    start = time.perf_counter()
    result = cache.get(args)
    elapsed = time.perf_counter() - start
    print(f"  Result: {result}, Time: {elapsed*1000:.2f} ms")

    # Cache stats
    print(f"\nCache stats: {cache.stats()}")
    print()


def example_decorator_basic():
    """Using the @cached decorator."""
    print("=" * 60)
    print("Cached Decorator - Basic Usage")
    print("=" * 60)

    @cached
    def fibonacci(n):
        """Compute fibonacci number (inefficient recursive version)."""
        if n <= 1:
            return n
        return fibonacci(n - 1) + fibonacci(n - 2)

    # First call
    print("Computing fibonacci(30)...")
    start = time.perf_counter()
    result = fibonacci(30)
    elapsed = time.perf_counter() - start
    print(f"Result: {result}, Time: {elapsed*1000:.2f} ms")

    # Second call (cached)
    print("\nComputing fibonacci(30) again (cached)...")
    start = time.perf_counter()
    result = fibonacci(30)
    elapsed = time.perf_counter() - start
    print(f"Result: {result}, Time: {elapsed*1000:.2f} ms")

    # Stats
    print(f"\nCache stats: {fibonacci.cache_stats()}")
    print()


def example_decorator_with_kwargs():
    """Using cached decorator with keyword arguments."""
    print("=" * 60)
    print("Cached Decorator - With Keyword Arguments")
    print("=" * 60)

    @cached
    def complex_calculation(x, y=10, z=20, multiplier=1.0):
        """Simulate complex calculation."""
        time.sleep(0.05)
        return (x + y + z) * multiplier

    # Different argument combinations
    print("Call 1: complex_calculation(5)")
    start = time.perf_counter()
    result1 = complex_calculation(5)
    elapsed = time.perf_counter() - start
    print(f"  Result: {result1}, Time: {elapsed*1000:.2f} ms")

    print("\nCall 2: complex_calculation(5, y=15)")
    start = time.perf_counter()
    result2 = complex_calculation(5, y=15)
    elapsed = time.perf_counter() - start
    print(f"  Result: {result2}, Time: {elapsed*1000:.2f} ms")

    print("\nCall 3: complex_calculation(5) - cached from Call 1")
    start = time.perf_counter()
    result3 = complex_calculation(5)
    elapsed = time.perf_counter() - start
    print(f"  Result: {result3}, Time: {elapsed*1000:.2f} ms")

    print(f"\nCache stats: {complex_calculation.cache_stats()}")
    print()


def example_custom_cache_size():
    """Using cached decorator with custom cache size."""
    print("=" * 60)
    print("Cached Decorator - Custom Cache Size")
    print("=" * 60)

    @cached(max_size=3)
    def compute(x):
        time.sleep(0.01)
        return x * 2

    # Fill cache beyond capacity
    print("Computing values 1-5...")
    for i in range(1, 6):
        result = compute(i)
        print(f"  compute({i}) = {result}")

    # Check which values are still cached
    print("\nChecking cache (LRU eviction):")
    for i in range(1, 6):
        start = time.perf_counter()
        result = compute(i)
        elapsed = time.perf_counter() - start
        cached_str = "CACHED" if elapsed < 0.005 else "COMPUTED"
        print(f"  compute({i}): {cached_str} ({elapsed*1000:.2f} ms)")

    print(f"\nCache stats: {compute.cache_stats()}")
    print()


def example_cache_management():
    """Demonstrating cache management operations."""
    print("=" * 60)
    print("Cache Management Operations")
    print("=" * 60)

    @cached
    def expensive_func(x):
        time.sleep(0.05)
        return x ** 2

    # Populate cache
    print("Populating cache...")
    for i in range(5):
        expensive_func(i)

    print(f"Initial stats: {expensive_func.cache_stats()}")

    # Check if value is cached
    print(f"\nIs expensive_func(2) cached? {expensive_func.cache_contains(2)}")
    print(f"Is expensive_func(10) cached? {expensive_func.cache_contains(10)}")

    # Clear cache
    print("\nClearing cache...")
    expensive_func.cache_clear()
    print(f"Stats after clear: {expensive_func.cache_stats()}")
    print()


def example_ttl_cache():
    """Using TTL (Time-To-Live) cache."""
    print("=" * 60)
    print("TTL Cache - Time-Based Expiration")
    print("=" * 60)

    cache = RustTTLCache(max_size=100, ttl=2.0)  # 2 second TTL

    # Store value
    args = (42,)
    result = "expensive_result"
    cache.put(args, result)

    print("Value stored in cache")
    print(f"Immediate retrieval: {cache.get(args)}")

    # Wait a bit
    print("\nWaiting 1 second...")
    time.sleep(1.0)
    print(f"After 1 second: {cache.get(args)}")

    # Wait for expiration
    print("\nWaiting 1.5 more seconds (total 2.5s)...")
    time.sleep(1.5)
    result = cache.get(args)
    print(f"After expiration: {result}")

    print(f"\nCache stats: {cache.stats()}")
    print()


def example_ttl_cleanup():
    """Demonstrating manual cleanup of expired entries."""
    print("=" * 60)
    print("TTL Cache - Manual Cleanup")
    print("=" * 60)

    cache = RustTTLCache(max_size=100, ttl=0.5)  # 500ms TTL

    # Add multiple entries
    print("Adding 10 entries...")
    for i in range(10):
        cache.put((i,), f"value_{i}")

    print(f"Initial size: {cache.stats()['size']}")

    # Wait for expiration
    print("\nWaiting for expiration...")
    time.sleep(0.6)

    # Manual cleanup
    cleaned = cache.cleanup()
    print(f"Cleaned {cleaned} expired entries")
    print(f"New size: {cache.stats()['size']}")
    print()


def example_performance_benefit():
    """Demonstrate performance benefits of caching."""
    print("=" * 60)
    print("Performance Benefits Demonstration")
    print("=" * 60)

    def slow_function(n):
        """Intentionally slow function."""
        time.sleep(0.01)
        total = 0
        for i in range(n):
            total += i
        return total

    # Without caching
    print("Without caching (5 calls):")
    start = time.perf_counter()
    for _ in range(5):
        result = slow_function(1000)
    no_cache_time = time.perf_counter() - start
    print(f"  Time: {no_cache_time*1000:.2f} ms")

    # With caching
    @cached
    def cached_slow_function(n):
        return slow_function(n)

    print("\nWith caching (5 calls):")
    start = time.perf_counter()
    for _ in range(5):
        result = cached_slow_function(1000)
    cached_time = time.perf_counter() - start
    print(f"  Time: {cached_time*1000:.2f} ms")

    print(f"\nSpeedup: {no_cache_time/cached_time:.2f}x")
    print(f"Cache stats: {cached_slow_function.cache_stats()}")
    print()


def example_llm_response_caching():
    """Example of caching LLM responses (simulated)."""
    print("=" * 60)
    print("LLM Response Caching Pattern")
    print("=" * 60)

    @cached(max_size=1000)
    def call_llm(prompt, model="gpt-4", temperature=0.7):
        """Simulate LLM API call."""
        print(f"  [API CALL] Calling {model} with prompt: '{prompt[:30]}...'")
        time.sleep(0.1)  # Simulate API latency
        return f"Response to: {prompt}"

    # First call - hits API
    print("First call:")
    response1 = call_llm("What is the capital of France?")
    print(f"  Response: {response1}")

    # Second call with same args - cached
    print("\nSecond call (same prompt):")
    response2 = call_llm("What is the capital of France?")
    print(f"  Response: {response2}")

    # Different prompt
    print("\nThird call (different prompt):")
    response3 = call_llm("What is the capital of Spain?")
    print(f"  Response: {response3}")

    print(f"\nCache stats: {call_llm.cache_stats()}")
    print(f"Cache saved 1 LLM API call!")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Fast LangGraph Function Caching Examples")
    print("=" * 60 + "\n")

    example_manual_cache()
    example_decorator_basic()
    example_decorator_with_kwargs()
    example_custom_cache_size()
    example_cache_management()
    example_ttl_cache()
    example_ttl_cleanup()
    example_performance_benefit()
    example_llm_response_caching()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
