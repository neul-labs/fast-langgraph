#!/usr/bin/env python3
"""
Benchmark Rust channels vs Python channels to measure actual performance improvement.

This creates identical LangGraph workflows using:
1. Python LastValue channels (baseline)
2. Rust RustLastValue channels (accelerated)

And measures the performance difference in channel update operations.
"""

import sys
import time
from pathlib import Path
from typing import TypedDict

# Add paths
FAST_LANGGRAPH_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(FAST_LANGGRAPH_ROOT))
sys.path.insert(0, str(FAST_LANGGRAPH_ROOT / ".langgraph-test" / "langgraph" / "libs" / "langgraph"))

class State(TypedDict):
    """Simple state for testing."""
    value: int
    count: int


def benchmark_python_channels(iterations: int = 1000):
    """Benchmark with Python LastValue channels."""
    from langgraph.graph import END, StateGraph

    print("Creating graph with Python channels...")

    # Create graph
    graph = StateGraph(State)

    # Define nodes
    def increment(state: State) -> State:
        return {"value": state["value"] + 1, "count": state["count"] + 1}

    def double(state: State) -> State:
        return {"value": state["value"] * 2, "count": state["count"] + 1}

    def decrement(state: State) -> State:
        return {"value": state["value"] - 1, "count": state["count"] + 1}

    # Build graph with multiple nodes to create many channel updates
    graph.add_node("increment", increment)
    graph.add_node("double", double)
    graph.add_node("decrement", decrement)

    graph.set_entry_point("increment")
    graph.add_edge("increment", "double")
    graph.add_edge("double", "decrement")
    graph.add_edge("decrement", END)

    app = graph.compile()

    # Warm up
    for i in range(10):
        app.invoke({"value": i, "count": 0})

    # Benchmark
    print(f"Running {iterations} iterations with Python channels...")
    start_time = time.time()

    for i in range(iterations):
        result = app.invoke({"value": i, "count": 0})
        # Verify correctness
        expected = (i + 1) * 2 - 1
        assert result["value"] == expected, f"Wrong result: {result['value']} != {expected}"
        assert result["count"] == 3, f"Wrong count: {result['count']} != 3"

    duration = time.time() - start_time

    print(f"✓ Python channels: {iterations} iterations in {duration:.3f}s")
    print(f"  Average per iteration: {duration/iterations*1000:.3f}ms")
    print()

    return duration


def benchmark_rust_channels(iterations: int = 1000):
    """Benchmark with Rust RustLastValue channels."""
    from langgraph.graph import END, StateGraph

    import fast_langgraph.shim as shim
    from fast_langgraph import RustLastValue

    print("Creating graph with Rust channels...")

    # Apply shim for acceleration
    shim.patch_langgraph()

    # Create graph
    graph = StateGraph(State)

    # Replace channels with Rust versions
    # This is the key difference - using RustLastValue instead of Python LastValue
    graph.channels["value"] = RustLastValue(int, "value")
    graph.channels["count"] = RustLastValue(int, "count")

    # Define nodes (same as Python version)
    def increment(state: State) -> State:
        return {"value": state["value"] + 1, "count": state["count"] + 1}

    def double(state: State) -> State:
        return {"value": state["value"] * 2, "count": state["count"] + 1}

    def decrement(state: State) -> State:
        return {"value": state["value"] - 1, "count": state["count"] + 1}

    # Build graph (same structure)
    graph.add_node("increment", increment)
    graph.add_node("double", double)
    graph.add_node("decrement", decrement)

    graph.set_entry_point("increment")
    graph.add_edge("increment", "double")
    graph.add_edge("double", "decrement")
    graph.add_edge("decrement", END)

    app = graph.compile()

    # Warm up
    for i in range(10):
        app.invoke({"value": i, "count": 0})

    # Benchmark
    print(f"Running {iterations} iterations with Rust channels...")
    start_time = time.time()

    for i in range(iterations):
        result = app.invoke({"value": i, "count": 0})
        # Verify correctness
        expected = (i + 1) * 2 - 1
        assert result["value"] == expected, f"Wrong result: {result['value']} != {expected}"
        assert result["count"] == 3, f"Wrong count: {result['count']} != 3"

    duration = time.time() - start_time

    print(f"✓ Rust channels: {iterations} iterations in {duration:.3f}s")
    print(f"  Average per iteration: {duration/iterations*1000:.3f}ms")
    print()

    return duration


def benchmark_channel_operations_only(iterations: int = 100000):
    """Benchmark just the channel update operations without full graph execution."""
    from langgraph.channels import LastValue as PyLastValue

    from fast_langgraph import RustLastValue

    print("=" * 70)
    print("Direct Channel Operations Benchmark")
    print("=" * 70)
    print()

    # Benchmark Python channels
    print("Testing Python LastValue channel updates...")
    py_chan = PyLastValue(int)
    py_chan.key = "test"

    start_time = time.time()
    for i in range(iterations):
        py_chan.update([i])
        val = py_chan.get()
    py_duration = time.time() - start_time

    print(f"✓ Python: {iterations} updates in {py_duration:.3f}s")
    print(f"  Average per update: {py_duration/iterations*1000000:.2f}µs")
    print()

    # Benchmark Rust channels
    print("Testing Rust RustLastValue channel updates...")
    rust_chan = RustLastValue(int, "test")

    start_time = time.time()
    for i in range(iterations):
        rust_chan.update([i])
        val = rust_chan.get()
    rust_duration = time.time() - start_time

    print(f"✓ Rust: {iterations} updates in {rust_duration:.3f}s")
    print(f"  Average per update: {rust_duration/iterations*1000000:.2f}µs")
    print()

    # Calculate speedup
    if rust_duration > 0:
        speedup = py_duration / rust_duration
        improvement = ((py_duration - rust_duration) / py_duration * 100)

        print(f"Channel Operations Speedup: {speedup:.2f}x")
        print(f"Performance Improvement: {improvement:.1f}%")
        print()

    return py_duration, rust_duration


def main():
    """Run all benchmarks and compare results."""
    print("=" * 70)
    print("Fast LangGraph Rust Channel Benchmark")
    print("=" * 70)
    print()

    # First, benchmark direct channel operations
    py_chan_time, rust_chan_time = benchmark_channel_operations_only(iterations=100000)

    # Then benchmark full graph execution
    print("=" * 70)
    print("Full Graph Execution Benchmark")
    print("=" * 70)
    print()

    iterations = 1000

    # Run Python baseline
    print("BASELINE: Python Channels")
    print("-" * 70)
    python_duration = benchmark_python_channels(iterations)

    # Clean up modules for fresh import
    modules_to_remove = [k for k in sys.modules.keys() if k.startswith('langgraph')]
    for module in modules_to_remove:
        del sys.modules[module]

    # Run Rust accelerated
    print("ACCELERATED: Rust Channels")
    print("-" * 70)
    rust_duration = benchmark_rust_channels(iterations)

    # Compare results
    print("=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    print()

    print("Direct Channel Operations:")
    print(f"  Python LastValue:     {py_chan_time:.3f}s (100k updates)")
    print(f"  Rust RustLastValue:   {rust_chan_time:.3f}s (100k updates)")
    if rust_chan_time > 0:
        chan_speedup = py_chan_time / rust_chan_time
        print(f"  Channel Speedup:      {chan_speedup:.2f}x")
    print()

    print("Full Graph Execution:")
    print(f"  Python channels:      {python_duration:.3f}s ({iterations} iterations)")
    print(f"  Rust channels:        {rust_duration:.3f}s ({iterations} iterations)")

    if rust_duration > 0:
        speedup = python_duration / rust_duration
        improvement = ((python_duration - rust_duration) / python_duration * 100)

        print(f"  Graph Speedup:        {speedup:.2f}x")
        print(f"  Performance Gain:     {improvement:.1f}%")
        print()

        if speedup > 1.1:
            print(f"✓ SUCCESS: Rust channels provide {speedup:.2f}x speedup!")
        elif speedup > 0.95:
            print("⚠ NEUTRAL: Performance similar (within 5%)")
        else:
            print("✗ REGRESSION: Rust channels are slower")

    print()
    print("Note: The graph execution speedup is lower than channel speedup")
    print("because it includes Python node execution, which dominates runtime.")
    print("Channel operations are a smaller % of total execution time.")


if __name__ == "__main__":
    main()
