#!/usr/bin/env python3
"""
Simple performance comparison for Fast LangGraph shimming.

Tests a specific LangGraph workflow with and without Rust acceleration
to measure the performance improvement from apply_writes shimming.
"""

import sys
import time
from pathlib import Path

# Add paths
FAST_LANGGRAPH_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(FAST_LANGGRAPH_ROOT))
sys.path.insert(0, str(FAST_LANGGRAPH_ROOT / ".langgraph-test" / "langgraph" / "libs" / "langgraph"))

def run_test_workflow(use_shim=False):
    """
    Run a simple LangGraph workflow that exercises apply_writes.

    Args:
        use_shim: If True, enable Fast LangGraph shimming

    Returns:
        tuple: (success: bool, duration: float, iterations: int)
    """
    # Apply shim if requested
    if use_shim:
        import fast_langgraph.shim as shim
        print("Enabling Fast LangGraph acceleration...")
        result = shim.patch_langgraph()
        if not result:
            print("ERROR: Failed to apply shim!")
            return False, 0.0, 0
        print()

    # Import LangGraph after shimming (if enabled)
    from typing import TypedDict

    from langgraph.graph import END, StateGraph

    # Define a simple state
    class State(TypedDict):
        value: int

    # Create a simple graph with multiple nodes
    # This will trigger apply_writes many times
    def increment(state: State) -> State:
        return {"value": state["value"] + 1}

    def double(state: State) -> State:
        return {"value": state["value"] * 2}

    def decrement(state: State) -> State:
        return {"value": state["value"] - 1}

    # Build graph
    graph = StateGraph(State)
    graph.add_node("increment", increment)
    graph.add_node("double", double)
    graph.add_node("decrement", decrement)

    graph.set_entry_point("increment")
    graph.add_edge("increment", "double")
    graph.add_edge("double", "decrement")
    graph.add_edge("decrement", END)

    app = graph.compile()

    # Run the workflow multiple times to get measurable results
    iterations = 100
    start_time = time.time()

    try:
        for i in range(iterations):
            result = app.invoke({"value": i})
            # Verify correctness: (i + 1) * 2 - 1 = 2i + 1
            expected = 2 * i + 1
            if result["value"] != expected:
                print(f"ERROR: Expected {expected}, got {result['value']}")
                return False, 0.0, i

        duration = time.time() - start_time
        return True, duration, iterations

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, 0.0, 0

def main():
    """Run comparison between baseline and accelerated versions."""
    print("=" * 70)
    print("Fast LangGraph Simple Performance Comparison")
    print("=" * 70)
    print()

    # Run baseline (no shim)
    print("Running BASELINE (Pure Python)...")
    print("-" * 70)
    success_baseline, duration_baseline, iters_baseline = run_test_workflow(use_shim=False)

    if not success_baseline:
        print("✗ Baseline test failed!")
        sys.exit(1)

    print(f"✓ Baseline completed: {iters_baseline} iterations in {duration_baseline:.3f}s")
    print(f"  Average per iteration: {duration_baseline/iters_baseline*1000:.2f}ms")
    print()

    # Clean up modules for fresh import
    # Remove langgraph modules so they can be re-imported with shim
    modules_to_remove = [k for k in sys.modules.keys() if k.startswith('langgraph')]
    for module in modules_to_remove:
        del sys.modules[module]

    # Run accelerated (with shim)
    print("Running ACCELERATED (Rust shim)...")
    print("-" * 70)
    success_accelerated, duration_accelerated, iters_accelerated = run_test_workflow(use_shim=True)

    if not success_accelerated:
        print("✗ Accelerated test failed!")
        sys.exit(1)

    print(f"✓ Accelerated completed: {iters_accelerated} iterations in {duration_accelerated:.3f}s")
    print(f"  Average per iteration: {duration_accelerated/iters_accelerated*1000:.2f}ms")
    print()

    # Compare results
    print("=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)
    print()
    print(f"Baseline duration:     {duration_baseline:.3f}s")
    print(f"Accelerated duration:  {duration_accelerated:.3f}s")

    if duration_accelerated > 0:
        speedup = duration_baseline / duration_accelerated
        improvement = ((duration_baseline - duration_accelerated) / duration_baseline * 100)

        print(f"Speedup:              {speedup:.2f}x")
        print(f"Improvement:          {improvement:.1f}%")
        print()

        if speedup > 1.0:
            print(f"✓ SUCCESS: Rust acceleration provides {speedup:.2f}x speedup!")
        elif speedup > 0.95:
            print("⚠ NEUTRAL: Performance similar (within 5%)")
        else:
            print("✗ REGRESSION: Accelerated version is slower!")
    else:
        print("ERROR: Cannot compute speedup (accelerated duration is 0)")

if __name__ == "__main__":
    main()
