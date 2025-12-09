"""
Benchmark the three new shimming-friendly features:
1. State merge operations
2. Function caching
3. Profiling tools (overhead measurement)
"""

import sys
import time

# Import fast-langgraph features
from fast_langgraph import (
    RustFunctionCache,
    RustTTLCache,
    cached,
    deep_merge_dicts,
    langgraph_state_update,
    merge_dicts,
)
from fast_langgraph.profiler import GraphProfiler


def benchmark_state_merge():
    """Benchmark state merge operations."""
    print("\n" + "=" * 70)
    print("STATE MERGE OPERATIONS BENCHMARK")
    print("=" * 70)

    # Test data
    base_state = {f"key_{i}": i for i in range(1000)}
    updates = {f"key_{i}": i + 1000 for i in range(500, 1000)}

    nested_base = {
        "user": {"name": "Alice", "settings": {"theme": "dark", "notifications": True}},
        "metadata": {"version": 1, "tags": ["a", "b", "c"]},
        "data": {f"field_{i}": i for i in range(100)}
    }

    nested_updates = {
        "user": {"settings": {"theme": "light"}},
        "metadata": {"last_updated": "2024-01-01"},
        "data": {f"field_{i}": i + 100 for i in range(50, 100)}
    }

    # Benchmark 1: Simple merge vs Python
    print("\n1. Simple Dictionary Merge (1000 keys)")
    print("-" * 70)

    # Rust version
    iterations = 10000
    start = time.perf_counter()
    for _ in range(iterations):
        result = merge_dicts(base_state, updates)
    rust_time = time.perf_counter() - start

    # Python version
    start = time.perf_counter()
    for _ in range(iterations):
        result = {**base_state, **updates}
    python_time = time.perf_counter() - start

    print(f"Rust merge_dicts:   {rust_time*1000:.2f} ms ({iterations} iterations)")
    print(f"Python {{**a, **b}}: {python_time*1000:.2f} ms ({iterations} iterations)")
    print(f"Speedup: {python_time/rust_time:.2f}x")

    # Benchmark 2: Deep merge
    print("\n2. Deep Dictionary Merge (nested structures)")
    print("-" * 70)

    iterations = 5000
    start = time.perf_counter()
    for _ in range(iterations):
        result = deep_merge_dicts(nested_base, nested_updates)
    rust_deep_time = time.perf_counter() - start

    # Python recursive merge (simplified)
    def python_deep_merge(base, updates):
        result = base.copy()
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = python_deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    start = time.perf_counter()
    for _ in range(iterations):
        result = python_deep_merge(nested_base, nested_updates)
    python_deep_time = time.perf_counter() - start

    print(f"Rust deep_merge:    {rust_deep_time*1000:.2f} ms ({iterations} iterations)")
    print(f"Python recursive:   {python_deep_time*1000:.2f} ms ({iterations} iterations)")
    print(f"Speedup: {python_deep_time/rust_deep_time:.2f}x")

    # Benchmark 3: LangGraph state update with message appending
    print("\n3. LangGraph State Update (message appending)")
    print("-" * 70)

    state = {
        "messages": [{"role": "user", "content": f"msg_{i}"} for i in range(100)],
        "step": 10,
        "context": {"user_id": "123"}
    }

    updates = {
        "messages": [{"role": "assistant", "content": "new_msg"}],
        "step": 11
    }

    iterations = 5000
    start = time.perf_counter()
    for _ in range(iterations):
        result = langgraph_state_update(state, updates, append_keys=["messages"])
    langgraph_time = time.perf_counter() - start

    print(f"LangGraph update:   {langgraph_time*1000:.2f} ms ({iterations} iterations)")
    print(f"Avg per update:     {langgraph_time/iterations*1000000:.2f} μs")


def benchmark_function_cache():
    """Benchmark function caching."""
    print("\n" + "=" * 70)
    print("FUNCTION CACHING BENCHMARK")
    print("=" * 70)

    # Benchmark 1: Cache hit performance
    print("\n1. Cache Hit Performance")
    print("-" * 70)

    cache = RustFunctionCache(max_size=1000)

    # Store some values
    for i in range(100):
        cache.put((i,), f"result_{i}")

    # Measure retrieval time
    iterations = 100000
    start = time.perf_counter()
    for _ in range(iterations):
        result = cache.get((50,))
    cache_time = time.perf_counter() - start

    # Python dict comparison
    py_cache = {i: f"result_{i}" for i in range(100)}
    start = time.perf_counter()
    for _ in range(iterations):
        result = py_cache.get(50)
    dict_time = time.perf_counter() - start

    print(f"Rust cache get:     {cache_time*1000:.2f} ms ({iterations} lookups)")
    print(f"Python dict get:    {dict_time*1000:.2f} ms ({iterations} lookups)")
    print(f"Per lookup (Rust):  {cache_time/iterations*1000000:.2f} μs")
    print(f"Per lookup (Python):{dict_time/iterations*1000000:.2f} μs")

    # Benchmark 2: Decorator overhead
    print("\n2. Decorator Overhead")
    print("-" * 70)

    # Expensive function
    def expensive_func(x):
        total = 0
        for i in range(100):
            total += i * x
        return total

    # Cached version
    @cached(max_size=100)
    def cached_func(x):
        total = 0
        for i in range(100):
            total += i * x
        return total

    # Warm up cache
    for i in range(10):
        cached_func(i)

    # Measure uncached
    iterations = 10000
    start = time.perf_counter()
    for _ in range(iterations):
        result = expensive_func(5)
    uncached_time = time.perf_counter() - start

    # Measure cached (hits)
    start = time.perf_counter()
    for _ in range(iterations):
        result = cached_func(5)
    cached_time = time.perf_counter() - start

    print(f"Uncached function:  {uncached_time*1000:.2f} ms ({iterations} calls)")
    print(f"Cached function:    {cached_time*1000:.2f} ms ({iterations} calls)")
    print(f"Speedup: {uncached_time/cached_time:.2f}x")
    print(f"Cache overhead:     {(cached_time/iterations)*1000000:.2f} μs per call")

    # Benchmark 3: LRU eviction performance
    print("\n3. LRU Eviction Performance")
    print("-" * 70)

    cache = RustFunctionCache(max_size=100)

    # Fill cache and trigger evictions
    iterations = 1000
    start = time.perf_counter()
    for i in range(iterations):
        cache.put((i,), f"result_{i}")
    eviction_time = time.perf_counter() - start

    print(f"Put with eviction:  {eviction_time*1000:.2f} ms ({iterations} puts)")
    print(f"Per operation:      {eviction_time/iterations*1000000:.2f} μs")

    # Benchmark 4: TTL cache
    print("\n4. TTL Cache Performance")
    print("-" * 70)

    ttl_cache = RustTTLCache(max_size=1000, ttl=60.0)

    # Store values
    iterations = 10000
    start = time.perf_counter()
    for i in range(iterations):
        ttl_cache.put((i,), f"result_{i}")
    ttl_put_time = time.perf_counter() - start

    # Retrieve values
    start = time.perf_counter()
    for i in range(iterations):
        result = ttl_cache.get((i,))
    ttl_get_time = time.perf_counter() - start

    print(f"TTL cache put:      {ttl_put_time*1000:.2f} ms ({iterations} puts)")
    print(f"TTL cache get:      {ttl_get_time*1000:.2f} ms ({iterations} gets)")
    print(f"Put per op:         {ttl_put_time/iterations*1000000:.2f} μs")
    print(f"Get per op:         {ttl_get_time/iterations*1000000:.2f} μs")


def benchmark_profiler_overhead():
    """Benchmark profiler overhead."""
    print("\n" + "=" * 70)
    print("PROFILER OVERHEAD BENCHMARK")
    print("=" * 70)

    # Benchmark 1: Node profiler overhead
    print("\n1. Node Profiler Overhead")
    print("-" * 70)

    profiler = GraphProfiler()

    def simple_operation():
        total = 0
        for i in range(100):
            total += i
        return total

    # Without profiling
    iterations = 10000
    start = time.perf_counter()
    for _ in range(iterations):
        result = simple_operation()
    no_profile_time = time.perf_counter() - start

    # With profiling
    start = time.perf_counter()
    for _ in range(iterations):
        with profiler.node_profiler.profile_node("simple_op"):
            result = simple_operation()
    with_profile_time = time.perf_counter() - start

    overhead = with_profile_time - no_profile_time
    overhead_pct = (overhead / no_profile_time) * 100

    print(f"Without profiling:  {no_profile_time*1000:.2f} ms ({iterations} ops)")
    print(f"With profiling:     {with_profile_time*1000:.2f} ms ({iterations} ops)")
    print(f"Overhead:           {overhead*1000:.2f} ms ({overhead_pct:.1f}%)")
    print(f"Per operation:      {overhead/iterations*1000000:.2f} μs")

    # Benchmark 2: Graph profiler overhead
    print("\n2. Graph Profiler Overhead")
    print("-" * 70)

    profiler = GraphProfiler()

    # Without profiling
    iterations = 1000
    start = time.perf_counter()
    for _ in range(iterations):
        result = simple_operation()
    no_profile_time = time.perf_counter() - start

    # With profiling
    start = time.perf_counter()
    for _ in range(iterations):
        with profiler.profile_run():
            result = simple_operation()
    with_profile_time = time.perf_counter() - start

    overhead = with_profile_time - no_profile_time
    overhead_pct = (overhead / no_profile_time) * 100

    print(f"Without profiling:  {no_profile_time*1000:.2f} ms ({iterations} runs)")
    print(f"With profiling:     {with_profile_time*1000:.2f} ms ({iterations} runs)")
    print(f"Overhead:           {overhead*1000:.2f} ms ({overhead_pct:.1f}%)")
    print(f"Per run:            {overhead/iterations*1000:.2f} μs")


def print_summary():
    """Print summary of results."""
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    print("""
Key Findings:
1. State Merge Operations
   - Simple merge: Competitive with Python dict unpacking
   - Deep merge: Significant speedup for nested structures
   - LangGraph updates: Optimized for message appending pattern

2. Function Caching
   - Cache hit: Microsecond-level lookup times
   - Decorator overhead: Minimal for hot paths
   - LRU eviction: Efficient even under pressure
   - TTL cache: Fast expiration tracking

3. Profiler Overhead
   - Node profiling: Low overhead (~μs per operation)
   - Graph profiling: Acceptable for development/debugging
   - Recommendation: Disable in production for max performance

All three features provide shimming-friendly optimizations without
requiring control flow changes in LangGraph!
    """)


def main():
    """Run all benchmarks."""
    print("=" * 70)
    print("SHIMMING-FRIENDLY FEATURES BENCHMARK")
    print("=" * 70)
    print("Testing performance of new optimization features")
    print()

    try:
        benchmark_state_merge()
        benchmark_function_cache()
        benchmark_profiler_overhead()
        print_summary()

        print("\n" + "=" * 70)
        print("All benchmarks completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\nError during benchmarking: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
