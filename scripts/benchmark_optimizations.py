#!/usr/bin/env python3
"""
Benchmark all Fast LangGraph optimizations together.

This script measures the combined impact of:
1. Thread pool caching
2. RustCheckpointer
3. Accelerated apply_writes

It runs the same workload with and without optimizations to measure actual speedup.
"""

import statistics
import sys
import time
from operator import add
from pathlib import Path
from typing import Annotated, TypedDict

# Add paths
FAST_LANGGRAPH_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(FAST_LANGGRAPH_ROOT))
sys.path.insert(0, str(FAST_LANGGRAPH_ROOT / ".langgraph-test" / "langgraph" / "libs" / "langgraph"))

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph


class AgentState(TypedDict):
    """State for our example agent."""
    messages: Annotated[list[str], add]
    next_step: str
    iteration: int
    total_tokens: int


def create_test_graph():
    """Create a realistic test graph with simulated LLM calls."""

    def simulate_llm_call(prompt_tokens: int = 100, response_tokens: int = 50):
        """
        Simulate an LLM API call with realistic timing.

        Real LLM calls take 50-500ms depending on model and tokens.
        We simulate 5-10ms to keep tests fast while still having
        meaningful CPU work that benefits from executor caching.
        """
        # Simulate tokenization and prompt processing
        start = time.perf_counter()

        # Simulate CPU-intensive work (context window processing)
        result = 0
        for i in range(prompt_tokens):
            result += hash(f"token_{i}") % 1000

        # Simulate network delay (shortened for testing)
        time.sleep(0.002)  # 2ms simulated network delay

        # Simulate response generation
        response = []
        for i in range(response_tokens):
            response.append(f"word_{hash(result + i) % 1000}")

        elapsed = time.perf_counter() - start
        return " ".join(response[:10]), elapsed  # Return sample of response

    def router_node(state: AgentState) -> AgentState:
        iteration = state.get("iteration", 0)

        # Simulate LLM call to decide routing
        response, llm_time = simulate_llm_call(prompt_tokens=200, response_tokens=30)

        if iteration < 3:
            next_step = "process"
        elif iteration < 6:
            next_step = "transform"
        else:
            next_step = "finalize"

        return {
            "messages": [f"Router: {response[:30]}... -> {next_step}"],
            "next_step": next_step,
            "iteration": iteration + 1
        }

    def process_node(state: AgentState) -> AgentState:
        # Simulate LLM processing work
        response, llm_time = simulate_llm_call(prompt_tokens=500, response_tokens=100)

        # Some CPU-intensive processing
        result = sum(hash(msg) for msg in state.get("messages", []))

        return {
            "messages": [f"Process: {response[:30]}... (result={result % 10000})"],
            "total_tokens": state.get("total_tokens", 0) + 600
        }

    def transform_node(state: AgentState) -> AgentState:
        # Simulate LLM transformation
        response, llm_time = simulate_llm_call(prompt_tokens=300, response_tokens=80)

        # Data transformation work
        data = {"values": list(range(500))}
        transformed = {"values": [hash(f"{x}_{response}") % 1000 for x in data["values"]]}

        return {
            "messages": [f"Transform: {response[:30]}... (items={len(transformed['values'])})"],
            "total_tokens": state.get("total_tokens", 0) + 380
        }

    def finalize_node(state: AgentState) -> AgentState:
        # Final LLM call to summarize
        response, llm_time = simulate_llm_call(prompt_tokens=400, response_tokens=60)

        return {
            "messages": [f"Finalize: {response[:30]}... complete"],
            "next_step": "end"
        }

    def should_continue(state: AgentState) -> str:
        next_step = state.get("next_step", "")
        if next_step == "end":
            return "end"
        elif next_step == "process":
            return "process"
        elif next_step == "transform":
            return "transform"
        else:
            return "finalize"

    workflow = StateGraph(AgentState)
    workflow.add_node("router", router_node)
    workflow.add_node("process", process_node)
    workflow.add_node("transform", transform_node)
    workflow.add_node("finalize", finalize_node)
    workflow.set_entry_point("router")

    workflow.add_conditional_edges(
        "router",
        should_continue,
        {
            "process": "process",
            "transform": "transform",
            "finalize": "finalize",
            "end": END
        }
    )

    workflow.add_edge("process", "router")
    workflow.add_edge("transform", "router")
    workflow.add_edge("finalize", END)

    return workflow


def run_benchmark(num_iterations: int = 100, warmup: int = 5, num_sessions: int = 10):
    """
    Run benchmark comparing baseline vs optimized performance.

    Args:
        num_iterations: Number of graph invocations to test per session
        warmup: Number of warmup iterations (not counted)
        num_sessions: Number of different conversation sessions (threads)
    """
    print("=" * 70)
    print("Fast LangGraph Optimization Benchmark")
    print("=" * 70)
    print()
    print("Configuration:")
    print(f"  Sessions: {num_sessions} conversation threads")
    print(f"  Iterations per session: {num_iterations}")
    print(f"  Total invocations: {num_sessions * num_iterations}")
    print(f"  Warmup iterations: {warmup}")
    print()

    input_data = {
        "messages": [],
        "next_step": "",
        "iteration": 0,
        "total_tokens": 0
    }

    # ===== BASELINE: No optimizations =====
    print("Running BASELINE (no optimizations)...")
    print("-" * 70)

    workflow = create_test_graph()
    checkpointer = MemorySaver()
    app_baseline = workflow.compile(checkpointer=checkpointer)

    # Warmup
    config = {"configurable": {"thread_id": "warmup"}}
    for _ in range(warmup):
        app_baseline.invoke(input_data, config=config)

    # Actual benchmark - simulate multiple conversation sessions
    # Each session has multiple invocations (simulating a conversation)
    baseline_times = []
    print(f"  Running {num_sessions} sessions...")
    for session in range(num_sessions):
        config = {"configurable": {"thread_id": f"baseline-session-{session}"}}

        # Multiple invocations in this conversation
        for iteration in range(num_iterations):
            start = time.perf_counter()
            app_baseline.invoke(input_data, config=config)
            elapsed = time.perf_counter() - start
            baseline_times.append(elapsed * 1000)  # Convert to ms

    baseline_avg = statistics.mean(baseline_times)
    baseline_median = statistics.median(baseline_times)
    baseline_stdev = statistics.stdev(baseline_times) if len(baseline_times) > 1 else 0
    baseline_p95 = sorted(baseline_times)[int(len(baseline_times) * 0.95)]

    print(f"  Total invocations: {len(baseline_times)}")
    print(f"  Average:    {baseline_avg:.2f}ms")
    print(f"  Median:     {baseline_median:.2f}ms")
    print(f"  P95:        {baseline_p95:.2f}ms")
    print(f"  Std Dev:    {baseline_stdev:.2f}ms")
    print(f"  Total:      {sum(baseline_times)/1000:.3f}s")
    print()

    # ===== OPTIMIZED: All optimizations enabled =====
    print("Running OPTIMIZED (all optimizations enabled)...")
    print("-" * 70)

    # Enable all optimizations
    try:
        from fast_langgraph.optimizations import enable_all_optimizations
        results = enable_all_optimizations(verbose=True)
        print()

        if results['total_enabled'] == 0:
            print("⚠ WARNING: No optimizations were enabled!")
            print("  Make sure Rust extension is built: uv run maturin develop --release")
            return
    except Exception as e:
        print(f"✗ Error enabling optimizations: {e}")
        return

    # Create new graph with optimizations active
    workflow_opt = create_test_graph()

    # Use MemorySaver for now (RustCheckpointSaver needs full BaseCheckpointSaver implementation)
    checkpointer_opt = MemorySaver()
    print("✓ Using MemorySaver (RustCheckpointer integration pending)")

    app_optimized = workflow_opt.compile(checkpointer=checkpointer_opt)

    # Warmup
    config = {"configurable": {"thread_id": "warmup-opt"}}
    for _ in range(warmup):
        app_optimized.invoke(input_data, config=config)

    # Actual benchmark - same pattern as baseline
    optimized_times = []
    print(f"  Running {num_sessions} sessions...")
    for session in range(num_sessions):
        config = {"configurable": {"thread_id": f"optimized-session-{session}"}}

        # Multiple invocations in this conversation
        for iteration in range(num_iterations):
            start = time.perf_counter()
            app_optimized.invoke(input_data, config=config)
            elapsed = time.perf_counter() - start
            optimized_times.append(elapsed * 1000)  # Convert to ms

    optimized_avg = statistics.mean(optimized_times)
    optimized_median = statistics.median(optimized_times)
    optimized_stdev = statistics.stdev(optimized_times) if len(optimized_times) > 1 else 0
    optimized_p95 = sorted(optimized_times)[int(len(optimized_times) * 0.95)]

    print(f"  Total invocations: {len(optimized_times)}")
    print(f"  Average:    {optimized_avg:.2f}ms")
    print(f"  Median:     {optimized_median:.2f}ms")
    print(f"  P95:        {optimized_p95:.2f}ms")
    print(f"  Std Dev:    {optimized_stdev:.2f}ms")
    print(f"  Total:      {sum(optimized_times)/1000:.3f}s")
    print()

    # ===== RESULTS =====
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()

    speedup_avg = baseline_avg / optimized_avg
    speedup_median = baseline_median / optimized_median
    speedup_p95 = baseline_p95 / optimized_p95
    time_saved = (baseline_avg - optimized_avg) * len(baseline_times) / 1000

    print(f"Average Speedup:     {speedup_avg:.2f}x")
    print(f"Median Speedup:      {speedup_median:.2f}x")
    print(f"P95 Speedup:         {speedup_p95:.2f}x")
    print(f"Time Saved per Call: {baseline_avg - optimized_avg:.2f}ms")
    print(f"Total Time Saved:    {time_saved:.3f}s ({len(baseline_times)} total invocations)")
    print()

    if speedup_avg >= 2.0:
        print("✓ EXCELLENT: Achieved 2x+ speedup!")
    elif speedup_avg >= 1.5:
        print("✓ GOOD: Achieved 1.5x+ speedup")
    elif speedup_avg >= 1.2:
        print("✓ OK: Achieved 1.2x+ speedup")
    elif speedup_avg >= 1.05:
        print("✓ MINOR: Small but measurable speedup")
    else:
        print("⚠ WARNING: Speedup less than expected")
        print("  Check that all optimizations are enabled")
        print("  Note: Benefits are most visible with:")
        print("    - More iterations per session (executor reuse)")
        print("    - Real LLM calls (seconds vs milliseconds)")
        print("    - Checkpoint-heavy workloads")

    print()
    print("Detailed timing distribution:")
    print(f"  Baseline:  min={min(baseline_times):.2f}ms, "
          f"max={max(baseline_times):.2f}ms, "
          f"p95={sorted(baseline_times)[int(len(baseline_times)*0.95)]:.2f}ms")
    print(f"  Optimized: min={min(optimized_times):.2f}ms, "
          f"max={max(optimized_times):.2f}ms, "
          f"p95={sorted(optimized_times)[int(len(optimized_times)*0.95)]:.2f}ms")
    print()
    print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark Fast LangGraph optimizations")
    parser.add_argument("-n", "--iterations", type=int, default=10,
                       help="Number of iterations per session (default: 10)")
    parser.add_argument("-s", "--sessions", type=int, default=10,
                       help="Number of conversation sessions (default: 10)")
    parser.add_argument("-w", "--warmup", type=int, default=5,
                       help="Number of warmup iterations (default: 5)")

    args = parser.parse_args()

    run_benchmark(
        num_iterations=args.iterations,
        warmup=args.warmup,
        num_sessions=args.sessions
    )
