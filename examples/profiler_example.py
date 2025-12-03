"""
Example usage of profiling tools.

This demonstrates how to use the profiling tools to analyze
and optimize LangGraph execution performance.
"""

import time
from fast_langgraph.profiler import (
    GraphProfiler,
    NodeProfiler,
    PerformanceRecommendations,
    profile_function,
    create_profiler,
)


def example_node_profiling():
    """Example of profiling individual nodes."""
    print("=" * 60)
    print("Node-Level Profiling")
    print("=" * 60)

    profiler = NodeProfiler()

    # Simulate executing different nodes
    with profiler.profile_node("data_loading"):
        time.sleep(0.02)  # Simulate data loading

    with profiler.profile_node("llm_call"):
        time.sleep(0.1)  # Simulate LLM API call

    with profiler.profile_node("data_processing"):
        time.sleep(0.01)  # Simulate processing

    # Execute same node multiple times
    for _ in range(3):
        with profiler.profile_node("llm_call"):
            time.sleep(0.1)

    # Print report
    profiler.print_report()
    print()


def example_graph_profiling():
    """Example of profiling entire graph runs."""
    print("=" * 60)
    print("Graph-Level Profiling")
    print("=" * 60)

    profiler = GraphProfiler()

    # Simulate multiple graph runs
    for run in range(3):
        with profiler.profile_run():
            # Simulate node executions
            with profiler.node_profiler.profile_node("input_processing"):
                time.sleep(0.01)

            with profiler.node_profiler.profile_node("llm_generation"):
                time.sleep(0.05)

            with profiler.node_profiler.profile_node("output_formatting"):
                time.sleep(0.005)

            # Simulate checkpoint operations
            if run % 2 == 0:
                profiler.record_checkpoint_save()

    # Print comprehensive report
    profiler.print_report()
    print()


def example_cache_profiling():
    """Example of tracking cache performance."""
    print("=" * 60)
    print("Cache Performance Profiling")
    print("=" * 60)

    profiler = GraphProfiler()

    with profiler.profile_run():
        # Simulate cache operations
        for i in range(20):
            if i % 3 == 0:
                profiler.record_cache_hit()
            else:
                profiler.record_cache_miss()

        time.sleep(0.01)

    summary = profiler.get_summary()
    print(f"Total cache operations: {summary['cache_hits'] + summary['cache_misses']}")
    print(f"Cache hits: {summary['cache_hits']}")
    print(f"Cache misses: {summary['cache_misses']}")
    print(f"Hit rate: {summary['cache_hit_rate']*100:.1f}%")
    print()


def example_performance_recommendations():
    """Example of getting performance recommendations."""
    print("=" * 60)
    print("Performance Recommendations")
    print("=" * 60)

    profiler = GraphProfiler()

    # Simulate a graph with performance issues
    with profiler.profile_run():
        # Slow node that dominates execution
        with profiler.node_profiler.profile_node("slow_llm_call"):
            time.sleep(0.15)

        # Fast nodes
        with profiler.node_profiler.profile_node("quick_processing"):
            time.sleep(0.001)

        with profiler.node_profiler.profile_node("validation"):
            time.sleep(0.001)

    # Simulate poor cache performance
    for _ in range(15):
        profiler.record_cache_miss()
    for _ in range(5):
        profiler.record_cache_hit()

    # Get and print recommendations
    PerformanceRecommendations.print_recommendations(profiler)
    print()


def example_function_profiling():
    """Example of profiling individual functions."""
    print("=" * 60)
    print("Function-Level Profiling")
    print("=" * 60)

    @profile_function
    def expensive_computation(n):
        """Compute something expensive."""
        total = 0
        for i in range(n):
            total += i ** 2
        time.sleep(0.01)
        return total

    @profile_function
    def quick_computation(n):
        """Quick computation."""
        return sum(range(n))

    print("Calling expensive_computation(10000):")
    result1 = expensive_computation(10000)

    print("\nCalling quick_computation(10000):")
    result2 = quick_computation(10000)

    print()


def example_export_profiling_data():
    """Example of exporting profiling data to JSON."""
    print("=" * 60)
    print("Exporting Profiling Data")
    print("=" * 60)

    profiler = GraphProfiler()

    # Simulate some execution
    for _ in range(5):
        with profiler.profile_run():
            with profiler.node_profiler.profile_node("node_a"):
                time.sleep(0.01)
            with profiler.node_profiler.profile_node("node_b"):
                time.sleep(0.02)

    # Export to JSON
    import tempfile
    import os

    temp_file = os.path.join(tempfile.gettempdir(), "profiling_data.json")
    profiler.export_json(temp_file)
    print(f"Exported profiling data to: {temp_file}")

    # Read and display
    import json
    with open(temp_file) as f:
        data = json.load(f)

    print("\nExported data summary:")
    print(f"  Total runs: {data['total_runs']}")
    print(f"  Total time: {data['total_time']*1000:.2f} ms")
    print(f"  Nodes profiled: {len(data['node_stats'])}")
    print()


def example_real_world_simulation():
    """Simulate a realistic LangGraph execution with profiling."""
    print("=" * 60)
    print("Real-World LangGraph Simulation")
    print("=" * 60)

    profiler = create_profiler()

    # Simulate a conversational agent graph
    for conversation_turn in range(3):
        print(f"\nConversation turn {conversation_turn + 1}:")

        with profiler.profile_run():
            # Input processing
            with profiler.node_profiler.profile_node("parse_user_input"):
                time.sleep(0.005)

            # Check cache for similar queries
            cache_hit = conversation_turn > 0
            if cache_hit:
                profiler.record_cache_hit()
                print("  [CACHE HIT] Using cached response")
            else:
                profiler.record_cache_miss()

                # Call LLM
                with profiler.node_profiler.profile_node("llm_generate_response"):
                    time.sleep(0.08)
                    print("  [LLM CALL] Generating response")

            # Post-processing
            with profiler.node_profiler.profile_node("format_output"):
                time.sleep(0.003)

            # Save checkpoint every 2 turns
            if conversation_turn % 2 == 0:
                with profiler.node_profiler.profile_node("save_checkpoint"):
                    time.sleep(0.01)
                    profiler.record_checkpoint_save()
                    print("  [CHECKPOINT] Saved state")

    # Print comprehensive report
    print("\n" + "=" * 60)
    print("Profiling Report")
    print("=" * 60)
    profiler.print_report()

    # Get recommendations
    PerformanceRecommendations.print_recommendations(profiler)


def example_compare_optimizations():
    """Compare performance before and after optimizations."""
    print("=" * 60)
    print("Before/After Optimization Comparison")
    print("=" * 60)

    # Before optimization
    print("\nBefore optimization (no caching):")
    profiler_before = GraphProfiler()

    for _ in range(5):
        with profiler_before.profile_run():
            with profiler_before.node_profiler.profile_node("llm_call"):
                time.sleep(0.05)  # Simulate LLM call

    summary_before = profiler_before.get_summary()
    print(f"  Total time: {summary_before['total_time']*1000:.2f} ms")
    print(f"  Avg per run: {summary_before['avg_time_per_run']*1000:.2f} ms")

    # After optimization (with caching)
    print("\nAfter optimization (with caching):")
    profiler_after = GraphProfiler()

    for i in range(5):
        with profiler_after.profile_run():
            if i == 0:
                # First call - cache miss
                with profiler_after.node_profiler.profile_node("llm_call"):
                    time.sleep(0.05)
                profiler_after.record_cache_miss()
            else:
                # Subsequent calls - cache hit
                with profiler_after.node_profiler.profile_node("cache_lookup"):
                    time.sleep(0.001)
                profiler_after.record_cache_hit()

    summary_after = profiler_after.get_summary()
    print(f"  Total time: {summary_after['total_time']*1000:.2f} ms")
    print(f"  Avg per run: {summary_after['avg_time_per_run']*1000:.2f} ms")
    print(f"  Cache hit rate: {summary_after['cache_hit_rate']*100:.1f}%")

    # Calculate improvement
    improvement = (summary_before['total_time'] - summary_after['total_time']) / summary_before['total_time']
    print(f"\nPerformance improvement: {improvement*100:.1f}%")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Fast LangGraph Profiling Examples")
    print("=" * 60 + "\n")

    example_node_profiling()
    example_graph_profiling()
    example_cache_profiling()
    example_performance_recommendations()
    example_function_profiling()
    example_export_profiling_data()
    example_real_world_simulation()
    example_compare_optimizations()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
