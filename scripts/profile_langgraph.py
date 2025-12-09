#!/usr/bin/env python3
"""
Profile a realistic LangGraph workflow to identify actual bottlenecks.

This creates a representative graph with:
- State management
- Conditional edges
- Multiple nodes
- Checkpointing

Then profiles where time is actually spent.
"""

import cProfile
import pstats
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


def create_realistic_graph():
    """Create a realistic LangGraph with multiple nodes and conditional logic."""

    # Define nodes that simulate common patterns
    def router_node(state: AgentState) -> AgentState:
        """Route to different nodes based on state."""
        iteration = state.get("iteration", 0)

        if iteration < 3:
            next_step = "process"
        elif iteration < 6:
            next_step = "transform"
        else:
            next_step = "finalize"

        return {
            "messages": [f"Router: directing to {next_step}"],
            "next_step": next_step,
            "iteration": iteration + 1
        }

    def process_node(state: AgentState) -> AgentState:
        """Simulate processing work."""
        messages = state.get("messages", [])
        iteration = state.get("iteration", 0)

        # Simulate some work
        result = sum(range(1000))  # Small CPU work

        return {
            "messages": [f"Process: iteration {iteration}, result={result}"],
            "total_tokens": state.get("total_tokens", 0) + 150
        }

    def transform_node(state: AgentState) -> AgentState:
        """Simulate data transformation."""
        messages = state.get("messages", [])
        iteration = state.get("iteration", 0)

        # Simulate transformation
        data = {"values": list(range(100))}
        transformed = {"values": [x * 2 for x in data["values"]]}

        return {
            "messages": [f"Transform: iteration {iteration}, items={len(transformed['values'])}"],
            "total_tokens": state.get("total_tokens", 0) + 200
        }

    def finalize_node(state: AgentState) -> AgentState:
        """Finalize and prepare output."""
        return {
            "messages": ["Finalize: complete"],
            "next_step": "end"
        }

    # Conditional edge function
    def should_continue(state: AgentState) -> str:
        """Decide whether to continue or end."""
        next_step = state.get("next_step", "")

        if next_step == "end":
            return "end"
        elif next_step == "process":
            return "process"
        elif next_step == "transform":
            return "transform"
        else:
            return "finalize"

    # Build graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("process", process_node)
    workflow.add_node("transform", transform_node)
    workflow.add_node("finalize", finalize_node)

    # Set entry point
    workflow.set_entry_point("router")

    # Add conditional edges
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

    # Add edges back to router for iteration
    workflow.add_edge("process", "router")
    workflow.add_edge("transform", "router")
    workflow.add_edge("finalize", END)

    return workflow


def profile_with_checkpointing():
    """Profile graph execution WITH checkpointing."""
    print("\n" + "=" * 70)
    print("Profiling WITH Checkpointing")
    print("=" * 70 + "\n")

    workflow = create_realistic_graph()
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)

    # Profile execution
    profiler = cProfile.Profile()
    profiler.enable()

    # Run multiple invocations with checkpointing
    config = {"configurable": {"thread_id": "1"}}

    for i in range(10):
        result = app.invoke(
            {
                "messages": [],
                "next_step": "",
                "iteration": 0,
                "total_tokens": 0
            },
            config=config
        )

    profiler.disable()

    # Print stats
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')

    print("\nTop 30 functions by cumulative time:")
    print("-" * 70)
    stats.print_stats(30)

    return stats


def profile_without_checkpointing():
    """Profile graph execution WITHOUT checkpointing."""
    print("\n" + "=" * 70)
    print("Profiling WITHOUT Checkpointing")
    print("=" * 70 + "\n")

    workflow = create_realistic_graph()
    app = workflow.compile()  # No checkpointer

    # Profile execution
    profiler = cProfile.Profile()
    profiler.enable()

    # Run multiple invocations
    for i in range(10):
        result = app.invoke(
            {
                "messages": [],
                "next_step": "",
                "iteration": 0,
                "total_tokens": 0
            }
        )

    profiler.disable()

    # Print stats
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')

    print("\nTop 30 functions by cumulative time:")
    print("-" * 70)
    stats.print_stats(30)

    return stats


def manual_timing_breakdown():
    """Manually time different components."""
    print("\n" + "=" * 70)
    print("Manual Timing Breakdown")
    print("=" * 70 + "\n")

    workflow = create_realistic_graph()

    # Time compilation
    start = time.time()
    app_no_checkpoint = workflow.compile()
    compile_time = time.time() - start
    print(f"Graph compilation (no checkpoint):  {compile_time*1000:.2f}ms")

    # Time compilation with checkpoint
    start = time.time()
    checkpointer = MemorySaver()
    app_with_checkpoint = workflow.compile(checkpointer=checkpointer)
    compile_checkpoint_time = time.time() - start
    print(f"Graph compilation (with checkpoint): {compile_checkpoint_time*1000:.2f}ms")
    print()

    # Time single invocation without checkpoint
    input_data = {
        "messages": [],
        "next_step": "",
        "iteration": 0,
        "total_tokens": 0
    }

    start = time.time()
    result = app_no_checkpoint.invoke(input_data)
    invoke_no_checkpoint = time.time() - start
    print(f"Single invocation (no checkpoint):   {invoke_no_checkpoint*1000:.2f}ms")

    # Time single invocation with checkpoint
    config = {"configurable": {"thread_id": "1"}}
    start = time.time()
    result = app_with_checkpoint.invoke(input_data, config=config)
    invoke_with_checkpoint = time.time() - start
    print(f"Single invocation (with checkpoint): {invoke_with_checkpoint*1000:.2f}ms")

    checkpoint_overhead = invoke_with_checkpoint - invoke_no_checkpoint
    print(f"Checkpoint overhead per invocation:  {checkpoint_overhead*1000:.2f}ms")
    print()

    # Time 100 invocations
    start = time.time()
    for i in range(100):
        app_no_checkpoint.invoke(input_data)
    batch_no_checkpoint = time.time() - start

    start = time.time()
    for i in range(100):
        app_with_checkpoint.invoke(input_data, config=config)
    batch_with_checkpoint = time.time() - start

    print(f"100 invocations (no checkpoint):     {batch_no_checkpoint:.3f}s ({batch_no_checkpoint/100*1000:.2f}ms avg)")
    print(f"100 invocations (with checkpoint):   {batch_with_checkpoint:.3f}s ({batch_with_checkpoint/100*1000:.2f}ms avg)")
    print(f"Total checkpoint overhead:           {(batch_with_checkpoint - batch_no_checkpoint):.3f}s")
    print()

    return {
        "compile_time": compile_time,
        "compile_checkpoint_time": compile_checkpoint_time,
        "invoke_no_checkpoint": invoke_no_checkpoint,
        "invoke_with_checkpoint": invoke_with_checkpoint,
        "checkpoint_overhead_per_invoke": checkpoint_overhead,
        "batch_no_checkpoint": batch_no_checkpoint,
        "batch_with_checkpoint": batch_with_checkpoint,
    }


def identify_optimization_targets(timing_data):
    """Analyze timing data to identify optimization targets."""
    print("\n" + "=" * 70)
    print("OPTIMIZATION TARGET ANALYSIS")
    print("=" * 70 + "\n")

    checkpoint_overhead = timing_data["checkpoint_overhead_per_invoke"]
    total_time = timing_data["invoke_with_checkpoint"]

    print("Time Budget per Invocation (with checkpointing):")
    print(f"  Total:                {total_time*1000:.2f}ms")
    print(f"  Checkpoint overhead:  {checkpoint_overhead*1000:.2f}ms ({checkpoint_overhead/total_time*100:.1f}%)")
    print(f"  Core execution:       {(total_time - checkpoint_overhead)*1000:.2f}ms ({(1 - checkpoint_overhead/total_time)*100:.1f}%)")
    print()

    print("Recommended Optimization Targets (in priority order):")
    print()

    if checkpoint_overhead / total_time > 0.3:
        print("1. ⭐ CHECKPOINT OPERATIONS (High Impact)")
        print(f"   Current overhead: {checkpoint_overhead*1000:.2f}ms per invocation")
        print("   Target for Rust optimization:")
        print("   - Checkpoint serialization/deserialization")
        print("   - State copying and merging")
        print("   - Version tracking")
        print(f"   Potential speedup: 2-5x (could save {checkpoint_overhead*0.5*1000:.2f}-{checkpoint_overhead*0.8*1000:.2f}ms)")
        print()

    print("2. 🎯 GRAPH TRAVERSAL & TASK SCHEDULING")
    print("   - Trigger detection (which nodes to run)")
    print("   - Conditional edge evaluation")
    print("   - Task queue management")
    print("   Potential speedup: 1.5-2x for complex graphs")
    print()

    print("3. 📊 STATE MANAGEMENT")
    print("   - State merging with Annotated reducers")
    print("   - Channel value tracking")
    print("   - Version comparisons")
    print("   Potential speedup: 1.2-1.5x")
    print()

    print("4. ⚠️  NOT RECOMMENDED:")
    print("   - Individual channel operations (too fast, PyO3 overhead dominates)")
    print("   - Node execution (Python business logic, can't optimize)")
    print("   - LLM API calls (external, can't optimize)")
    print()


def main():
    """Run profiling and analysis."""
    print("=" * 70)
    print("LangGraph Profiling & Bottleneck Analysis")
    print("=" * 70)

    # Manual timing breakdown
    timing_data = manual_timing_breakdown()

    # Profile with and without checkpointing
    print("\n" + "=" * 70)
    print("Running detailed profiling...")
    print("=" * 70)

    stats_no_checkpoint = profile_without_checkpointing()
    stats_with_checkpoint = profile_with_checkpointing()

    # Identify optimization targets
    identify_optimization_targets(timing_data)

    print("\nProfiling complete! Check the output above for optimization targets.")
    print("\nKey files to examine:")
    print("  - Checkpoint: langgraph/checkpoint/")
    print("  - State management: langgraph/pregel/")
    print("  - Graph execution: langgraph/pregel/__init__.py")


if __name__ == "__main__":
    main()
