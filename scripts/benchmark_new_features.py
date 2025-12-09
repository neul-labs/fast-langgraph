"""
Benchmark new features: SQLite Checkpointer and LLM Cache
"""

import os
import statistics
import sys
import tempfile
import time
from typing import Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fast_langgraph import (
    RustCheckpointer,
    RustLLMCache,
    RustSQLiteCheckpointer,
    RustSQLiteLLMCache,
)


def benchmark_checkpoint_put(checkpointer, num_ops: int = 100) -> float:
    """Benchmark checkpoint PUT operations."""
    checkpoint_data = {
        "channel_values": {
            "messages": ["msg_" + str(i) for i in range(10)],
            "counter": 42,
            "data": "x" * 100,
        },
        "channel_versions": {
            "messages": 1,
            "counter": 1,
            "data": 1,
        },
        "versions_seen": {
            "task1": {"messages": 1, "counter": 0},
        },
        "step": 1,
    }

    times = []
    for i in range(num_ops):
        start = time.perf_counter()
        checkpointer.put(f"thread{i%10}", f"checkpoint{i}", checkpoint_data)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)  # Convert to ms

    return statistics.mean(times)


def benchmark_checkpoint_get(checkpointer, num_ops: int = 100) -> float:
    """Benchmark checkpoint GET operations."""
    # Pre-populate
    checkpoint_data = {
        "channel_values": {"data": "test"},
        "channel_versions": {"data": 1},
        "versions_seen": {},
        "step": 1,
    }

    for i in range(num_ops):
        checkpointer.put(f"thread{i%10}", f"checkpoint{i}", checkpoint_data)

    # Benchmark GET
    times = []
    for i in range(num_ops):
        start = time.perf_counter()
        checkpointer.get(f"thread{i%10}", f"checkpoint{i}")
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)

    return statistics.mean(times)


def benchmark_llm_cache_hit(cache, num_ops: int = 1000) -> float:
    """Benchmark LLM cache HIT operations."""
    # Pre-populate
    prompt = "What is 2+2?"
    response = "The answer is 4"
    cache.put(prompt, response)

    times = []
    for _ in range(num_ops):
        start = time.perf_counter()
        cache.get(prompt)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)

    return statistics.mean(times)


def benchmark_llm_cache_miss(cache, num_ops: int = 1000) -> float:
    """Benchmark LLM cache MISS operations."""
    times = []
    for i in range(num_ops):
        start = time.perf_counter()
        cache.get(f"prompt_{i}")
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)

    return statistics.mean(times)


def benchmark_llm_cache_put(cache, num_ops: int = 1000) -> float:
    """Benchmark LLM cache PUT operations."""
    times = []
    for i in range(num_ops):
        start = time.perf_counter()
        cache.put(f"prompt_{i}", f"response_{i}")
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)

    return statistics.mean(times)


def benchmark_compression_ratio() -> Dict[str, float]:
    """Benchmark compression ratios."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create large checkpoint data
        large_data = {
            "channel_values": {
                "messages": ["message_" + str(i) for i in range(100)],
                "data": "x" * 1000,
            },
            "channel_versions": {
                "messages": 1,
                "data": 1,
            },
            "versions_seen": {},
            "step": 1,
        }

        results = {}

        # No compression
        db_none = os.path.join(tmpdir, "none.db")
        cp_none = RustSQLiteCheckpointer(db_none, compression=None)
        cp_none.put("thread1", "checkpoint1", large_data)
        size_none = os.path.getsize(db_none)
        results["none"] = size_none

        # Zstd compression
        db_zstd = os.path.join(tmpdir, "zstd.db")
        cp_zstd = RustSQLiteCheckpointer(db_zstd, compression="zstd")
        cp_zstd.put("thread1", "checkpoint1", large_data)
        size_zstd = os.path.getsize(db_zstd)
        results["zstd"] = size_zstd

        return results


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(name: str, value: float, unit: str = "ms"):
    """Print a formatted result."""
    print(f"  {name:<40} {value:>10.4f} {unit}")


def main():
    print_header("Fast LangGraph - New Features Benchmark")
    print(f"  Python version: {sys.version.split()[0]}")
    print("  Running benchmarks...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # ================================================================
        # Checkpoint Benchmarks
        # ================================================================
        print_header("Checkpoint Performance")

        # In-memory checkpoint
        cp_memory = RustCheckpointer()
        put_time_mem = benchmark_checkpoint_put(cp_memory, num_ops=100)
        get_time_mem = benchmark_checkpoint_get(cp_memory, num_ops=100)

        print_result("In-Memory PUT (avg)", put_time_mem)
        print_result("In-Memory GET (avg)", get_time_mem)

        # SQLite checkpoint (no compression)
        db_path_none = os.path.join(tmpdir, "cp_none.db")
        cp_sqlite_none = RustSQLiteCheckpointer(db_path_none, compression=None)
        put_time_sqlite_none = benchmark_checkpoint_put(cp_sqlite_none, num_ops=100)
        get_time_sqlite_none = benchmark_checkpoint_get(cp_sqlite_none, num_ops=100)

        print_result("SQLite PUT (no compression, avg)", put_time_sqlite_none)
        print_result("SQLite GET (no compression, avg)", get_time_sqlite_none)

        # SQLite checkpoint (zstd compression)
        db_path_zstd = os.path.join(tmpdir, "cp_zstd.db")
        cp_sqlite_zstd = RustSQLiteCheckpointer(db_path_zstd, compression="zstd")
        put_time_sqlite_zstd = benchmark_checkpoint_put(cp_sqlite_zstd, num_ops=100)
        get_time_sqlite_zstd = benchmark_checkpoint_get(cp_sqlite_zstd, num_ops=100)

        print_result("SQLite PUT (zstd compression, avg)", put_time_sqlite_zstd)
        print_result("SQLite GET (zstd compression, avg)", get_time_sqlite_zstd)

        # ================================================================
        # Compression Ratio Benchmark
        # ================================================================
        print_header("Compression Efficiency")

        compression_sizes = benchmark_compression_ratio()
        size_none = compression_sizes["none"]
        size_zstd = compression_sizes["zstd"]

        print_result("Uncompressed size", size_none / 1024, "KB")
        print_result("Zstd compressed size", size_zstd / 1024, "KB")

        compression_ratio = (1 - size_zstd / size_none) * 100
        print_result("Compression ratio", compression_ratio, "%")

        # ================================================================
        # LLM Cache Benchmarks
        # ================================================================
        print_header("LLM Cache Performance")

        # In-memory cache
        cache_mem = RustLLMCache(max_size=10000)

        cache_put_mem = benchmark_llm_cache_put(cache_mem, num_ops=1000)
        cache_hit_mem = benchmark_llm_cache_hit(cache_mem, num_ops=1000)
        cache_miss_mem = benchmark_llm_cache_miss(cache_mem, num_ops=1000)

        print_result("In-Memory Cache PUT (avg)", cache_put_mem)
        print_result("In-Memory Cache HIT (avg)", cache_hit_mem)
        print_result("In-Memory Cache MISS (avg)", cache_miss_mem)

        # SQLite cache
        db_cache = os.path.join(tmpdir, "llm_cache.db")
        cache_sqlite = RustSQLiteLLMCache(db_cache)

        cache_put_sqlite = benchmark_llm_cache_put(cache_sqlite, num_ops=1000)
        cache_hit_sqlite = benchmark_llm_cache_hit(cache_sqlite, num_ops=1000)
        cache_miss_sqlite = benchmark_llm_cache_miss(cache_sqlite, num_ops=1000)

        print_result("SQLite Cache PUT (avg)", cache_put_sqlite)
        print_result("SQLite Cache HIT (avg)", cache_hit_sqlite)
        print_result("SQLite Cache MISS (avg)", cache_miss_sqlite)

        # ================================================================
        # Summary
        # ================================================================
        print_header("Performance Summary")

        print("\nCheckpoint Operations:")
        print_result("  Memory vs SQLite PUT overhead",
                    ((put_time_sqlite_none / put_time_mem) - 1) * 100, "%")
        print_result("  Compression PUT overhead",
                    ((put_time_sqlite_zstd / put_time_sqlite_none) - 1) * 100, "%")
        print_result("  Compression space savings", compression_ratio, "%")

        print("\nLLM Cache Operations:")
        print_result("  In-Memory cache HIT speed", cache_hit_mem, "ms")
        print_result("  SQLite cache HIT speed", cache_hit_sqlite, "ms")

        # Simulated LLM call time
        llm_call_time = 100.0  # 100ms average
        cache_savings = ((llm_call_time - cache_hit_mem) / llm_call_time) * 100

        print_result("  Time saved per cache hit", cache_savings, "%")
        print(f"\n  Note: Assuming avg LLM call = {llm_call_time}ms")
        print(f"  Cache hit = {cache_hit_mem:.4f}ms (saves {llm_call_time - cache_hit_mem:.2f}ms)")

        print_header("Benchmark Complete")


if __name__ == "__main__":
    main()
