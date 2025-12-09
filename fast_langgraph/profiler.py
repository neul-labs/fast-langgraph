"""
Profiling tools for LangGraph execution.

These tools help identify bottlenecks and optimize graph performance.
"""

import json
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional


class NodeProfiler:
    """Profile individual node execution times."""

    def __init__(self):
        self.node_times: Dict[str, List[float]] = defaultdict(list)
        self.node_counts: Dict[str, int] = defaultdict(int)
        self.current_node: Optional[str] = None
        self.start_time: Optional[float] = None

    @contextmanager
    def profile_node(self, node_name: str):
        """Context manager to profile a single node execution."""
        self.current_node = node_name
        self.start_time = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - self.start_time
            self.node_times[node_name].append(elapsed)
            self.node_counts[node_name] += 1
            self.current_node = None
            self.start_time = None

    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get profiling statistics for all nodes."""
        stats = {}
        for node_name, times in self.node_times.items():
            if times:
                stats[node_name] = {
                    "count": self.node_counts[node_name],
                    "total_time": sum(times),
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                }
        return stats

    def print_report(self):
        """Print a formatted profiling report."""
        stats = self.get_stats()

        if not stats:
            print("No profiling data collected.")
            return

        print("\n" + "=" * 80)
        print("Node Profiling Report")
        print("=" * 80)

        # Sort by total time
        sorted_stats = sorted(
            stats.items(), key=lambda x: x[1]["total_time"], reverse=True
        )

        print(
            f"\n{'Node':<30} {'Count':>8} {'Total (ms)':>12} {'Avg (ms)':>12} {'Min (ms)':>12} {'Max (ms)':>12}"
        )
        print("-" * 80)

        for node_name, node_stats in sorted_stats:
            print(
                f"{node_name:<30} "
                f"{node_stats['count']:>8} "
                f"{node_stats['total_time']*1000:>12.2f} "
                f"{node_stats['avg_time']*1000:>12.2f} "
                f"{node_stats['min_time']*1000:>12.2f} "
                f"{node_stats['max_time']*1000:>12.2f}"
            )

        print("=" * 80)

        # Summary
        total_time = sum(s["total_time"] for s in stats.values())
        total_calls = sum(s["count"] for s in stats.values())
        print(f"\nTotal execution time: {total_time*1000:.2f} ms")
        print(f"Total node calls: {total_calls}")
        print(f"Average time per call: {(total_time/total_calls)*1000:.2f} ms")
        print()


class GraphProfiler:
    """Comprehensive profiling for LangGraph execution."""

    def __init__(self):
        self.node_profiler = NodeProfiler()
        self.graph_runs: List[Dict[str, Any]] = []
        self.current_run_start: Optional[float] = None
        self.checkpoints_saved = 0
        self.checkpoints_loaded = 0
        self.cache_hits = 0
        self.cache_misses = 0

    @contextmanager
    def profile_run(self):
        """Context manager to profile an entire graph run."""
        self.current_run_start = time.perf_counter()
        run_data = {"start_time": self.current_run_start, "nodes_executed": []}

        try:
            yield self
        finally:
            elapsed = time.perf_counter() - self.current_run_start
            run_data["total_time"] = elapsed
            run_data["end_time"] = time.perf_counter()
            self.graph_runs.append(run_data)
            self.current_run_start = None

    def record_checkpoint_save(self):
        """Record a checkpoint save operation."""
        self.checkpoints_saved += 1

    def record_checkpoint_load(self):
        """Record a checkpoint load operation."""
        self.checkpoints_loaded += 1

    def record_cache_hit(self):
        """Record a cache hit."""
        self.cache_hits += 1

    def record_cache_miss(self):
        """Record a cache miss."""
        self.cache_misses += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all profiling data."""
        total_runs = len(self.graph_runs)

        if total_runs == 0:
            return {"error": "No graph runs profiled"}

        total_time = sum(run["total_time"] for run in self.graph_runs)
        avg_time = total_time / total_runs

        return {
            "total_runs": total_runs,
            "total_time": total_time,
            "avg_time_per_run": avg_time,
            "min_time": min(run["total_time"] for run in self.graph_runs),
            "max_time": max(run["total_time"] for run in self.graph_runs),
            "checkpoints_saved": self.checkpoints_saved,
            "checkpoints_loaded": self.checkpoints_loaded,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": (
                self.cache_hits / (self.cache_hits + self.cache_misses)
                if (self.cache_hits + self.cache_misses) > 0
                else 0.0
            ),
            "node_stats": self.node_profiler.get_stats(),
        }

    def print_report(self):
        """Print a comprehensive profiling report."""
        summary = self.get_summary()

        if "error" in summary:
            print(summary["error"])
            return

        print("\n" + "=" * 80)
        print("Graph Profiling Report")
        print("=" * 80)

        print("\nGraph Execution:")
        print(f"  Total runs: {summary['total_runs']}")
        print(f"  Total time: {summary['total_time']*1000:.2f} ms")
        print(f"  Avg time per run: {summary['avg_time_per_run']*1000:.2f} ms")
        print(f"  Min time: {summary['min_time']*1000:.2f} ms")
        print(f"  Max time: {summary['max_time']*1000:.2f} ms")

        print("\nCheckpoints:")
        print(f"  Saved: {summary['checkpoints_saved']}")
        print(f"  Loaded: {summary['checkpoints_loaded']}")

        print("\nCache Performance:")
        print(f"  Hits: {summary['cache_hits']}")
        print(f"  Misses: {summary['cache_misses']}")
        print(f"  Hit rate: {summary['cache_hit_rate']*100:.1f}%")

        # Print node profiling report
        self.node_profiler.print_report()

    def export_json(self, filename: str):
        """Export profiling data to JSON file."""
        data = self.get_summary()
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Profiling data exported to {filename}")


def profile_function(func: Callable) -> Callable:
    """Decorator to profile a function's execution time."""

    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} took {elapsed*1000:.2f} ms")
        return result

    return wrapper


class PerformanceRecommendations:
    """Analyze profiling data and provide optimization recommendations."""

    @staticmethod
    def analyze(profiler: GraphProfiler) -> List[str]:
        """Analyze profiling data and return recommendations."""
        recommendations = []
        summary = profiler.get_summary()

        if "error" in summary:
            return ["No profiling data available for analysis"]

        # Check cache performance
        cache_hit_rate = summary.get("cache_hit_rate", 0)
        if (
            cache_hit_rate < 0.5
            and (summary["cache_hits"] + summary["cache_misses"]) > 10
        ):
            recommendations.append(
                f"⚠️  Low cache hit rate ({cache_hit_rate*100:.1f}%). "
                "Consider increasing cache size or reviewing cache key strategy."
            )
        elif cache_hit_rate > 0.8:
            recommendations.append(
                f"✅ Excellent cache hit rate ({cache_hit_rate*100:.1f}%)!"
            )

        # Check node execution times
        node_stats = summary.get("node_stats", {})
        if node_stats:
            # Find slowest nodes
            slowest = sorted(
                node_stats.items(), key=lambda x: x[1]["avg_time"], reverse=True
            )[:3]

            if slowest:
                recommendations.append("\n📊 Slowest nodes (by avg time):")
                for node_name, stats in slowest:
                    recommendations.append(
                        f"   - {node_name}: {stats['avg_time']*1000:.2f} ms avg "
                        f"({stats['count']} calls, {stats['total_time']*1000:.2f} ms total)"
                    )

                # Check if slowest node dominates
                if slowest[0][1]["total_time"] / summary["total_time"] > 0.7:
                    recommendations.append(
                        f"\n⚠️  Node '{slowest[0][0]}' accounts for "
                        f"{(slowest[0][1]['total_time']/summary['total_time'])*100:.1f}% "
                        "of total execution time. Consider optimizing this node."
                    )

        # Check checkpoint frequency
        checkpoints_per_run = summary["checkpoints_saved"] / summary["total_runs"]
        if checkpoints_per_run > 10:
            recommendations.append(
                f"\n⚠️  High checkpoint frequency ({checkpoints_per_run:.1f} per run). "
                "Consider reducing checkpoint frequency if not needed."
            )

        # General recommendations
        if summary["avg_time_per_run"] * 1000 > 100:  # > 100ms
            recommendations.append("\n💡 Performance tips:")
            recommendations.append("   - Use RustLLMCache for LLM response caching")
            recommendations.append("   - Enable fast state merge operations")
            recommendations.append(
                "   - Consider using in-memory checkpointer for development"
            )

        return (
            recommendations
            if recommendations
            else ["✅ No issues detected - performance looks good!"]
        )

    @staticmethod
    def print_recommendations(profiler: GraphProfiler):
        """Print optimization recommendations."""
        print("\n" + "=" * 80)
        print("Performance Recommendations")
        print("=" * 80)

        recommendations = PerformanceRecommendations.analyze(profiler)
        for rec in recommendations:
            print(rec)

        print("=" * 80 + "\n")


# Convenience functions
def create_profiler() -> GraphProfiler:
    """Create a new graph profiler."""
    return GraphProfiler()


def create_node_profiler() -> NodeProfiler:
    """Create a new node profiler."""
    return NodeProfiler()
