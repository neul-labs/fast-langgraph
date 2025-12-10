#!/usr/bin/env python3
"""
Generate a comprehensive BENCHMARK.md report by running all benchmarks.

Usage:
    python scripts/generate_benchmark_report.py

This will run all benchmarks and output results to BENCHMARK.md
"""

import copy
import json
import os
import random
import statistics
import string
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add paths
FAST_LANGGRAPH_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(FAST_LANGGRAPH_ROOT))


def get_system_info() -> Dict[str, str]:
    """Get system information for the report."""
    import platform

    return {
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "platform_version": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor() or "Unknown",
    }


def benchmark_channels() -> Dict[str, Any]:
    """Benchmark channel operations."""
    from fast_langgraph import RustLastValue

    results = {}

    # Benchmark updates
    channel = RustLastValue(int)
    iterations = 100000

    start = time.perf_counter()
    for i in range(iterations):
        channel.update([i])
    rust_update_time = time.perf_counter() - start

    # Python baseline
    py_channel = {"value": None}
    start = time.perf_counter()
    for i in range(iterations):
        py_channel["value"] = i
    python_update_time = time.perf_counter() - start

    results["channel_updates"] = {
        "rust_ms": rust_update_time * 1000,
        "python_ms": python_update_time * 1000,
        "iterations": iterations,
        "rust_per_op_ns": (rust_update_time / iterations) * 1e9,
        "python_per_op_ns": (python_update_time / iterations) * 1e9,
    }

    return results


def benchmark_checkpointing() -> Dict[str, Any]:
    """Benchmark checkpointing operations."""
    from fast_langgraph import RustCheckpointer, RustSQLiteCheckpointer

    results = {}

    # Test state
    state = {
        "messages": [f"msg_{i}" for i in range(100)],
        "context": {"user_id": "123", "session": "abc"},
        "step": 42
    }

    iterations = 1000

    # In-memory checkpointer
    checkpointer = RustCheckpointer()

    # PUT benchmark
    start = time.perf_counter()
    for i in range(iterations):
        checkpointer.put("thread1", f"checkpoint_{i}", state)
    put_time = time.perf_counter() - start

    # GET benchmark
    start = time.perf_counter()
    for i in range(iterations):
        checkpointer.get("thread1", f"checkpoint_{i}")
    get_time = time.perf_counter() - start

    results["in_memory"] = {
        "put_ms": put_time * 1000,
        "get_ms": get_time * 1000,
        "iterations": iterations,
        "put_per_op_us": (put_time / iterations) * 1e6,
        "get_per_op_us": (get_time / iterations) * 1e6,
    }

    # SQLite checkpointer
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoint.db")
        sqlite_checkpointer = RustSQLiteCheckpointer(db_path)

        # PUT benchmark
        start = time.perf_counter()
        for i in range(iterations):
            sqlite_checkpointer.put("thread1", f"checkpoint_{i}", state)
        sqlite_put_time = time.perf_counter() - start

        # GET benchmark
        start = time.perf_counter()
        for i in range(iterations):
            sqlite_checkpointer.get("thread1", f"checkpoint_{i}")
        sqlite_get_time = time.perf_counter() - start

        results["sqlite"] = {
            "put_ms": sqlite_put_time * 1000,
            "get_ms": sqlite_get_time * 1000,
            "iterations": iterations,
            "put_per_op_us": (sqlite_put_time / iterations) * 1e6,
            "get_per_op_us": (sqlite_get_time / iterations) * 1e6,
        }

    return results


def benchmark_llm_cache() -> Dict[str, Any]:
    """Benchmark LLM caching."""
    from fast_langgraph import RustLLMCache

    results = {}
    cache = RustLLMCache(max_size=1000)

    # Simulate LLM responses with cache
    def simulate_llm(prompt: str) -> str:
        time.sleep(0.001)  # 1ms simulated LLM call
        return f"Response to: {prompt}"

    prompts = [f"prompt_{i % 10}" for i in range(100)]  # 10 unique, repeated

    # Without cache
    start = time.perf_counter()
    for prompt in prompts:
        simulate_llm(prompt)
    no_cache_time = time.perf_counter() - start

    # With cache
    start = time.perf_counter()
    for prompt in prompts:
        cached = cache.get(prompt)
        if cached is None:
            response = simulate_llm(prompt)
            cache.put(prompt, response)
    with_cache_time = time.perf_counter() - start

    stats = cache.stats()

    results["llm_cache"] = {
        "without_cache_ms": no_cache_time * 1000,
        "with_cache_ms": with_cache_time * 1000,
        "speedup": no_cache_time / with_cache_time,
        "hit_rate": stats.get("hit_rate_percent", 0),
        "hits": stats.get("hits", 0),
        "misses": stats.get("misses", 0),
    }

    # Cache lookup performance
    iterations = 100000
    cache.put("test_prompt", "test_response")

    start = time.perf_counter()
    for _ in range(iterations):
        cache.get("test_prompt")
    lookup_time = time.perf_counter() - start

    results["cache_lookup"] = {
        "total_ms": lookup_time * 1000,
        "iterations": iterations,
        "per_lookup_us": (lookup_time / iterations) * 1e6,
    }

    return results


def benchmark_state_merge() -> Dict[str, Any]:
    """Benchmark state merge operations."""
    from fast_langgraph import merge_dicts, deep_merge_dicts, langgraph_state_update

    results = {}

    # Simple merge
    base_state = {f"key_{i}": i for i in range(1000)}
    updates = {f"key_{i}": i + 1000 for i in range(500, 1000)}

    iterations = 10000

    start = time.perf_counter()
    for _ in range(iterations):
        merge_dicts(base_state, updates)
    rust_time = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(iterations):
        {**base_state, **updates}
    python_time = time.perf_counter() - start

    results["simple_merge"] = {
        "rust_ms": rust_time * 1000,
        "python_ms": python_time * 1000,
        "iterations": iterations,
        "keys": 1000,
    }

    # Deep merge
    nested_base = {
        "user": {"name": "Alice", "settings": {"theme": "dark"}},
        "data": {f"field_{i}": i for i in range(100)}
    }
    nested_updates = {
        "user": {"settings": {"theme": "light"}},
        "data": {f"field_{i}": i + 100 for i in range(50, 100)}
    }

    iterations = 5000

    start = time.perf_counter()
    for _ in range(iterations):
        deep_merge_dicts(nested_base, nested_updates)
    rust_deep_time = time.perf_counter() - start

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
        python_deep_merge(nested_base, nested_updates)
    python_deep_time = time.perf_counter() - start

    results["deep_merge"] = {
        "rust_ms": rust_deep_time * 1000,
        "python_ms": python_deep_time * 1000,
        "iterations": iterations,
    }

    # LangGraph state update
    state = {
        "messages": [{"role": "user", "content": f"msg_{i}"} for i in range(100)],
        "step": 10
    }
    update = {
        "messages": [{"role": "assistant", "content": "new"}],
        "step": 11
    }

    iterations = 5000
    start = time.perf_counter()
    for _ in range(iterations):
        langgraph_state_update(state, update, append_keys=["messages"])
    lg_time = time.perf_counter() - start

    results["langgraph_update"] = {
        "total_ms": lg_time * 1000,
        "iterations": iterations,
        "per_update_us": (lg_time / iterations) * 1e6,
    }

    return results


def benchmark_function_cache() -> Dict[str, Any]:
    """Benchmark function caching."""
    from fast_langgraph import RustFunctionCache, cached

    results = {}

    # Expensive function
    def expensive_func(x):
        total = 0
        for i in range(100):
            total += i * x
        return total

    @cached(max_size=100)
    def cached_func(x):
        total = 0
        for i in range(100):
            total += i * x
        return total

    # Warm up cache
    for i in range(10):
        cached_func(i)

    iterations = 10000

    # Uncached
    start = time.perf_counter()
    for _ in range(iterations):
        expensive_func(5)
    uncached_time = time.perf_counter() - start

    # Cached
    start = time.perf_counter()
    for _ in range(iterations):
        cached_func(5)
    cached_time = time.perf_counter() - start

    results["function_cache"] = {
        "uncached_ms": uncached_time * 1000,
        "cached_ms": cached_time * 1000,
        "iterations": iterations,
        "speedup": uncached_time / cached_time,
        "overhead_us": (cached_time / iterations) * 1e6,
    }

    # Raw cache lookup
    cache = RustFunctionCache(max_size=1000)
    for i in range(100):
        cache.put((i,), f"result_{i}")

    iterations = 100000
    start = time.perf_counter()
    for _ in range(iterations):
        cache.get((50,))
    lookup_time = time.perf_counter() - start

    results["cache_lookup"] = {
        "total_ms": lookup_time * 1000,
        "iterations": iterations,
        "per_lookup_us": (lookup_time / iterations) * 1e6,
    }

    return results


def benchmark_profiler() -> Dict[str, Any]:
    """Benchmark profiler overhead."""
    from fast_langgraph import GraphProfiler

    results = {}
    profiler = GraphProfiler()

    def simple_op():
        total = 0
        for i in range(100):
            total += i
        return total

    iterations = 10000

    # Without profiling
    start = time.perf_counter()
    for _ in range(iterations):
        simple_op()
    no_profile_time = time.perf_counter() - start

    # With profiling
    start = time.perf_counter()
    for _ in range(iterations):
        with profiler.node_profiler.profile_node("simple_op"):
            simple_op()
    with_profile_time = time.perf_counter() - start

    overhead = with_profile_time - no_profile_time

    results["profiler"] = {
        "without_ms": no_profile_time * 1000,
        "with_ms": with_profile_time * 1000,
        "overhead_ms": overhead * 1000,
        "overhead_pct": (overhead / no_profile_time) * 100,
        "iterations": iterations,
        "per_op_us": (overhead / iterations) * 1e6,
    }

    return results


def generate_random_string(length: int = 10) -> str:
    """Generate a random string."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_llm_state(num_messages: int = 100, content_length: int = 500) -> Dict[str, Any]:
    """Generate a realistic LLM agent state with message history."""
    return {
        "messages": [
            {
                "role": random.choice(["user", "assistant", "system"]),
                "content": generate_random_string(content_length),
                "function_call": {
                    "name": f"tool_{i % 5}",
                    "arguments": json.dumps({"arg1": i, "arg2": f"value_{i}"}),
                } if i % 3 == 0 else None,
            }
            for i in range(num_messages)
        ],
        "agent_scratchpad": [
            {"thought": generate_random_string(200), "action": f"action_{i}"}
            for i in range(num_messages // 2)
        ],
        "context": {
            "user_profile": {
                "id": generate_random_string(20),
                "preferences": {f"pref_{j}": random.random() for j in range(20)},
            },
            "session": {
                "start_time": time.time(),
                "interactions": num_messages,
            }
        },
        "current_step": num_messages,
    }


def benchmark_complex_structures() -> Dict[str, Any]:
    """Benchmark complex data structure operations - showcasing Rust's strengths."""
    from fast_langgraph import RustCheckpointer, langgraph_state_update, deep_merge_dicts

    results = {}

    # 1. Checkpoint serialization with complex state (Rust's biggest win)
    checkpointer = RustCheckpointer()

    sizes = [
        (10, 100, "small"),
        (50, 500, "medium"),
        (200, 1000, "large"),
    ]

    for num_msgs, content_len, size_name in sizes:
        state = generate_llm_state(num_msgs, content_len)
        state_json = json.dumps(state)
        state_size_kb = len(state_json) / 1024

        iterations = 200

        # Rust checkpoint
        start = time.perf_counter()
        for i in range(iterations):
            checkpointer.put("thread", f"cp_{i}", state)
        rust_time = time.perf_counter() - start

        # Python deepcopy (common checkpoint approach)
        start = time.perf_counter()
        checkpoints = {}
        for i in range(iterations):
            checkpoints[f"cp_{i}"] = copy.deepcopy(state)
        python_time = time.perf_counter() - start

        speedup = python_time / rust_time if rust_time > 0 else 0

        results[f"checkpoint_{size_name}"] = {
            "rust_ms": rust_time * 1000,
            "python_ms": python_time * 1000,
            "speedup": speedup,
            "state_size_kb": state_size_kb,
            "iterations": iterations,
        }

    # 2. Sustained state updates (graph execution simulation)
    update_configs = [
        (1000, 10, "quick"),
        (100, 100, "medium"),
    ]

    for num_steps, msgs_per_step, config_name in update_configs:
        initial_state = generate_llm_state(10, 200)

        # Pre-generate updates
        all_updates = [
            {
                "messages": [{"role": "assistant", "content": generate_random_string(200)}
                             for _ in range(msgs_per_step)],
                "current_step": step,
            }
            for step in range(num_steps)
        ]

        # Rust sustained updates
        state = dict(initial_state)
        start = time.perf_counter()
        for update in all_updates:
            state = langgraph_state_update(state, update, append_keys=["messages"])
        rust_time = time.perf_counter() - start

        # Python sustained updates
        def python_update(state, update, append_keys):
            result = dict(state)
            for key, value in update.items():
                if key in append_keys and isinstance(result.get(key), list):
                    result[key] = result[key] + value
                else:
                    result[key] = value
            return result

        state = dict(initial_state)
        start = time.perf_counter()
        for update in all_updates:
            state = python_update(state, update, ["messages"])
        python_time = time.perf_counter() - start

        speedup = python_time / rust_time if rust_time > 0 else 0

        results[f"state_update_{config_name}"] = {
            "rust_ms": rust_time * 1000,
            "python_ms": python_time * 1000,
            "speedup": speedup,
            "num_steps": num_steps,
            "msgs_per_step": msgs_per_step,
        }

    # 3. End-to-end graph simulation
    num_nodes = 20
    num_iterations = 50

    start = time.perf_counter()
    for iteration in range(num_iterations):
        state = generate_llm_state(5, 100)
        for node_idx in range(num_nodes):
            update = {
                "messages": [{"role": "assistant", "content": f"Node {node_idx} output"}],
                "current_step": node_idx,
            }
            state = langgraph_state_update(state, update, append_keys=["messages"])
            if node_idx % 5 == 0:
                checkpointer.put(f"iter_{iteration}", f"node_{node_idx}", state)
    rust_e2e_time = time.perf_counter() - start

    python_checkpoints = {}
    start = time.perf_counter()
    for iteration in range(num_iterations):
        state = generate_llm_state(5, 100)
        for node_idx in range(num_nodes):
            update = {
                "messages": [{"role": "assistant", "content": f"Node {node_idx} output"}],
                "current_step": node_idx,
            }
            state = python_update(state, update, ["messages"])
            if node_idx % 5 == 0:
                python_checkpoints[f"iter_{iteration}_node_{node_idx}"] = copy.deepcopy(state)
    python_e2e_time = time.perf_counter() - start

    speedup = python_e2e_time / rust_e2e_time if rust_e2e_time > 0 else 0

    results["e2e_simulation"] = {
        "rust_ms": rust_e2e_time * 1000,
        "python_ms": python_e2e_time * 1000,
        "speedup": speedup,
        "num_nodes": num_nodes,
        "num_iterations": num_iterations,
    }

    return results


def generate_markdown_report(all_results: Dict[str, Any], system_info: Dict[str, str]) -> str:
    """Generate the BENCHMARK.md content."""

    lines = []

    # Header
    lines.append("# Fast LangGraph Benchmark Results")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # System Info
    lines.append("## System Information")
    lines.append("")
    lines.append("| Property | Value |")
    lines.append("|----------|-------|")
    lines.append(f"| Python Version | {system_info['python_version']} |")
    lines.append(f"| Platform | {system_info['platform']} {system_info['platform_version']} |")
    lines.append(f"| Machine | {system_info['machine']} |")
    lines.append(f"| Processor | {system_info['processor']} |")
    lines.append("")

    # Table of Contents
    lines.append("## Table of Contents")
    lines.append("")
    lines.append("- [Complex Data Structures (Rust Strengths)](#complex-data-structures-rust-strengths)")
    lines.append("- [Channel Operations](#channel-operations)")
    lines.append("- [Checkpointing](#checkpointing)")
    lines.append("- [LLM Caching](#llm-caching)")
    lines.append("- [State Merge Operations](#state-merge-operations)")
    lines.append("- [Function Caching](#function-caching)")
    lines.append("- [Profiler Overhead](#profiler-overhead)")
    lines.append("- [Summary](#summary)")
    lines.append("")

    # Complex Data Structures (Rust Strengths)
    lines.append("## Complex Data Structures (Rust Strengths)")
    lines.append("")
    lines.append("These benchmarks showcase where Rust provides the most significant performance gains.")
    lines.append("")

    cs = all_results.get("complex_structures", {})

    if cs:
        # Checkpoint serialization
        lines.append("### Checkpoint Serialization (vs Python deepcopy)")
        lines.append("")
        lines.append("Rust's biggest advantage - avoiding Python object overhead during state persistence.")
        lines.append("")
        lines.append("| State Size | Rust | Python | Speedup |")
        lines.append("|------------|------|--------|---------|")

        for size_name in ["small", "medium", "large"]:
            key = f"checkpoint_{size_name}"
            if key in cs:
                data = cs[key]
                lines.append(f"| {data['state_size_kb']:.1f} KB | {data['rust_ms']:.2f} ms | {data['python_ms']:.2f} ms | **{data['speedup']:.0f}x** |")
        lines.append("")

        # Sustained state updates
        lines.append("### Sustained State Updates (Graph Execution)")
        lines.append("")
        lines.append("Simulating real LangGraph execution with continuous state updates.")
        lines.append("")
        lines.append("| Workload | Steps | Rust | Python | Speedup |")
        lines.append("|----------|-------|------|--------|---------|")

        for config_name in ["quick", "medium"]:
            key = f"state_update_{config_name}"
            if key in cs:
                data = cs[key]
                lines.append(f"| {config_name.title()} | {data['num_steps']} | {data['rust_ms']:.2f} ms | {data['python_ms']:.2f} ms | **{data['speedup']:.1f}x** |")
        lines.append("")

        # E2E simulation
        if "e2e_simulation" in cs:
            e2e = cs["e2e_simulation"]
            lines.append("### End-to-End Graph Simulation")
            lines.append("")
            lines.append(f"Full graph execution: {e2e['num_nodes']} nodes, {e2e['num_iterations']} iterations with checkpointing.")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| Rust Total Time | {e2e['rust_ms']:.2f} ms |")
            lines.append(f"| Python Total Time | {e2e['python_ms']:.2f} ms |")
            lines.append(f"| **Speedup** | **{e2e['speedup']:.2f}x** |")
            lines.append("")

    # Channel Operations
    lines.append("## Channel Operations")
    lines.append("")
    ch = all_results.get("channels", {}).get("channel_updates", {})
    if ch:
        lines.append("Benchmarking `RustLastValue` channel update operations.")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Iterations | {ch['iterations']:,} |")
        lines.append(f"| Rust Total Time | {ch['rust_ms']:.2f} ms |")
        lines.append(f"| Python Total Time | {ch['python_ms']:.2f} ms |")
        lines.append(f"| Rust Per Operation | {ch['rust_per_op_ns']:.2f} ns |")
        lines.append(f"| Python Per Operation | {ch['python_per_op_ns']:.2f} ns |")
        lines.append("")

    # Checkpointing
    lines.append("## Checkpointing")
    lines.append("")
    cp = all_results.get("checkpointing", {})

    if cp.get("in_memory"):
        mem = cp["in_memory"]
        lines.append("### In-Memory Checkpointer")
        lines.append("")
        lines.append("| Operation | Total Time | Per Operation |")
        lines.append("|-----------|------------|---------------|")
        lines.append(f"| PUT ({mem['iterations']:,} ops) | {mem['put_ms']:.2f} ms | {mem['put_per_op_us']:.2f} us |")
        lines.append(f"| GET ({mem['iterations']:,} ops) | {mem['get_ms']:.2f} ms | {mem['get_per_op_us']:.2f} us |")
        lines.append("")

    if cp.get("sqlite"):
        sql = cp["sqlite"]
        lines.append("### SQLite Checkpointer")
        lines.append("")
        lines.append("| Operation | Total Time | Per Operation |")
        lines.append("|-----------|------------|---------------|")
        lines.append(f"| PUT ({sql['iterations']:,} ops) | {sql['put_ms']:.2f} ms | {sql['put_per_op_us']:.2f} us |")
        lines.append(f"| GET ({sql['iterations']:,} ops) | {sql['get_ms']:.2f} ms | {sql['get_per_op_us']:.2f} us |")
        lines.append("")

    # LLM Caching
    lines.append("## LLM Caching")
    lines.append("")
    llm = all_results.get("llm_cache", {})

    if llm.get("llm_cache"):
        lc = llm["llm_cache"]
        lines.append("### Cache Effectiveness (Simulated LLM Calls)")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Without Cache | {lc['without_cache_ms']:.2f} ms |")
        lines.append(f"| With Cache | {lc['with_cache_ms']:.2f} ms |")
        lines.append(f"| **Speedup** | **{lc['speedup']:.2f}x** |")
        lines.append(f"| Hit Rate | {lc['hit_rate']}% |")
        lines.append(f"| Cache Hits | {lc['hits']} |")
        lines.append(f"| Cache Misses | {lc['misses']} |")
        lines.append("")

    if llm.get("cache_lookup"):
        cl = llm["cache_lookup"]
        lines.append("### Raw Cache Lookup Performance")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Iterations | {cl['iterations']:,} |")
        lines.append(f"| Total Time | {cl['total_ms']:.2f} ms |")
        lines.append(f"| Per Lookup | {cl['per_lookup_us']:.2f} us |")
        lines.append("")

    # State Merge Operations
    lines.append("## State Merge Operations")
    lines.append("")
    sm = all_results.get("state_merge", {})

    if sm.get("simple_merge"):
        simple = sm["simple_merge"]
        lines.append("### Simple Dictionary Merge")
        lines.append("")
        lines.append(f"Merging dictionaries with {simple['keys']} keys.")
        lines.append("")
        lines.append("| Implementation | Time ({} iterations) |".format(simple['iterations']))
        lines.append("|----------------|----------------------|")
        lines.append(f"| Rust `merge_dicts` | {simple['rust_ms']:.2f} ms |")
        lines.append(f"| Python `{{**a, **b}}` | {simple['python_ms']:.2f} ms |")
        lines.append("")

    if sm.get("deep_merge"):
        deep = sm["deep_merge"]
        lines.append("### Deep Dictionary Merge")
        lines.append("")
        lines.append("| Implementation | Time ({} iterations) |".format(deep['iterations']))
        lines.append("|----------------|----------------------|")
        lines.append(f"| Rust `deep_merge_dicts` | {deep['rust_ms']:.2f} ms |")
        lines.append(f"| Python recursive | {deep['python_ms']:.2f} ms |")
        lines.append("")

    if sm.get("langgraph_update"):
        lg = sm["langgraph_update"]
        lines.append("### LangGraph State Update")
        lines.append("")
        lines.append("State update with message appending (100 existing messages).")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Iterations | {lg['iterations']:,} |")
        lines.append(f"| Total Time | {lg['total_ms']:.2f} ms |")
        lines.append(f"| Per Update | {lg['per_update_us']:.2f} us |")
        lines.append("")

    # Function Caching
    lines.append("## Function Caching")
    lines.append("")
    fc = all_results.get("function_cache", {})

    if fc.get("function_cache"):
        fn = fc["function_cache"]
        lines.append("### @cached Decorator Performance")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Iterations | {fn['iterations']:,} |")
        lines.append(f"| Uncached Time | {fn['uncached_ms']:.2f} ms |")
        lines.append(f"| Cached Time | {fn['cached_ms']:.2f} ms |")
        lines.append(f"| **Speedup** | **{fn['speedup']:.2f}x** |")
        lines.append(f"| Cache Overhead | {fn['overhead_us']:.2f} us/call |")
        lines.append("")

    if fc.get("cache_lookup"):
        cl = fc["cache_lookup"]
        lines.append("### Raw Cache Lookup")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Iterations | {cl['iterations']:,} |")
        lines.append(f"| Total Time | {cl['total_ms']:.2f} ms |")
        lines.append(f"| Per Lookup | {cl['per_lookup_us']:.2f} us |")
        lines.append("")

    # Profiler Overhead
    lines.append("## Profiler Overhead")
    lines.append("")
    pr = all_results.get("profiler", {}).get("profiler", {})
    if pr:
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Iterations | {pr['iterations']:,} |")
        lines.append(f"| Without Profiling | {pr['without_ms']:.2f} ms |")
        lines.append(f"| With Profiling | {pr['with_ms']:.2f} ms |")
        lines.append(f"| Overhead | {pr['overhead_ms']:.2f} ms ({pr['overhead_pct']:.1f}%) |")
        lines.append(f"| Per Operation | {pr['per_op_us']:.2f} us |")
        lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")

    # Rust Strengths highlight
    lines.append("### Rust's Key Strengths")
    lines.append("")
    lines.append("| Operation | Speedup | Best Use Case |")
    lines.append("|-----------|---------|---------------|")

    if cs:
        if "checkpoint_large" in cs:
            lines.append(f"| Checkpoint Serialization | **{cs['checkpoint_large']['speedup']:.0f}x** | State persistence |")
        if "state_update_quick" in cs:
            lines.append(f"| Sustained State Updates | **{cs['state_update_quick']['speedup']:.1f}x** | Long-running graphs |")
        if "e2e_simulation" in cs:
            lines.append(f"| E2E Graph Execution | **{cs['e2e_simulation']['speedup']:.1f}x** | Production workloads |")
    lines.append("")

    lines.append("### All Performance Characteristics")
    lines.append("")
    lines.append("| Feature | Performance |")
    lines.append("|---------|-------------|")

    if cs:
        if "checkpoint_large" in cs:
            lines.append(f"| Complex Checkpoint (250KB) | {cs['checkpoint_large']['speedup']:.0f}x faster than deepcopy |")
    if llm.get("llm_cache"):
        lines.append(f"| LLM Cache (90% hit rate) | {llm['llm_cache']['speedup']:.1f}x speedup |")
    if fc.get("function_cache"):
        lines.append(f"| Function Caching | {fc['function_cache']['speedup']:.1f}x speedup |")
    if cp.get("in_memory"):
        lines.append(f"| In-Memory Checkpoint PUT | {cp['in_memory']['put_per_op_us']:.1f} us/op |")
        lines.append(f"| In-Memory Checkpoint GET | {cp['in_memory']['get_per_op_us']:.1f} us/op |")
    if sm.get("langgraph_update"):
        lines.append(f"| LangGraph State Update | {sm['langgraph_update']['per_update_us']:.1f} us/op |")
    if pr:
        lines.append(f"| Profiler Overhead | {pr['per_op_us']:.1f} us/op |")

    lines.append("")
    lines.append("### Running Benchmarks")
    lines.append("")
    lines.append("To regenerate this report:")
    lines.append("")
    lines.append("```bash")
    lines.append("uv run python scripts/generate_benchmark_report.py")
    lines.append("```")
    lines.append("")
    lines.append("To run individual benchmarks:")
    lines.append("")
    lines.append("```bash")
    lines.append("# Rust benchmarks (requires cargo)")
    lines.append("cargo bench")
    lines.append("")
    lines.append("# Python benchmarks")
    lines.append("uv run python scripts/benchmark_rust_strengths.py      # Rust's key advantages")
    lines.append("uv run python scripts/benchmark_complex_structures.py  # Complex data structure tests")
    lines.append("uv run python scripts/benchmark_all_features.py")
    lines.append("uv run python scripts/benchmark_rust_channels.py")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main():
    """Run all benchmarks and generate BENCHMARK.md."""
    print("=" * 70)
    print("Fast LangGraph Benchmark Report Generator")
    print("=" * 70)
    print()

    all_results = {}

    # Get system info
    print("Gathering system information...")
    system_info = get_system_info()

    # Run benchmarks
    benchmarks = [
        ("complex_structures", "Complex Data Structures (Rust Strengths)", benchmark_complex_structures),
        ("channels", "Channel Operations", benchmark_channels),
        ("checkpointing", "Checkpointing", benchmark_checkpointing),
        ("llm_cache", "LLM Caching", benchmark_llm_cache),
        ("state_merge", "State Merge Operations", benchmark_state_merge),
        ("function_cache", "Function Caching", benchmark_function_cache),
        ("profiler", "Profiler Overhead", benchmark_profiler),
    ]

    for key, name, func in benchmarks:
        print(f"Running {name} benchmark...")
        try:
            all_results[key] = func()
            print(f"  Done.")
        except Exception as e:
            print(f"  Error: {e}")
            all_results[key] = {}

    print()
    print("Generating BENCHMARK.md...")

    # Generate report
    report = generate_markdown_report(all_results, system_info)

    # Write to file
    output_path = FAST_LANGGRAPH_ROOT / "BENCHMARK.md"
    with open(output_path, "w") as f:
        f.write(report)

    print(f"Report written to: {output_path}")
    print()
    print("=" * 70)
    print("Done!")
    print("=" * 70)


if __name__ == "__main__":
    main()
