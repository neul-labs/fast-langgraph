"""
Tests for profiling tools.
"""

import time

import pytest

from fast_langgraph.profiler import (
    GraphProfiler,
    NodeProfiler,
    PerformanceRecommendations,
    create_node_profiler,
    create_profiler,
    profile_function,
)


def test_node_profiler_basic():
    """Test basic node profiling."""
    profiler = NodeProfiler()

    with profiler.profile_node("node1"):
        time.sleep(0.01)

    with profiler.profile_node("node2"):
        time.sleep(0.02)

    stats = profiler.get_stats()
    assert "node1" in stats
    assert "node2" in stats
    assert stats["node1"]["count"] == 1
    assert stats["node2"]["count"] == 1
    assert stats["node1"]["total_time"] >= 0.01
    assert stats["node2"]["total_time"] >= 0.02


def test_node_profiler_multiple_calls():
    """Test profiling the same node multiple times."""
    profiler = NodeProfiler()

    for i in range(3):
        with profiler.profile_node("repeated_node"):
            time.sleep(0.01)

    stats = profiler.get_stats()
    assert stats["repeated_node"]["count"] == 3
    assert stats["repeated_node"]["avg_time"] >= 0.01
    assert stats["repeated_node"]["min_time"] >= 0.01
    assert stats["repeated_node"]["max_time"] >= 0.01


def test_node_profiler_stats():
    """Test statistics calculation."""
    profiler = NodeProfiler()

    # Execute with varying times
    with profiler.profile_node("test_node"):
        time.sleep(0.01)

    with profiler.profile_node("test_node"):
        time.sleep(0.02)

    with profiler.profile_node("test_node"):
        time.sleep(0.01)

    stats = profiler.get_stats()["test_node"]
    assert stats["count"] == 3
    assert stats["min_time"] >= 0.01
    assert stats["max_time"] >= 0.02
    assert stats["avg_time"] == stats["total_time"] / 3


def test_node_profiler_print_report(capsys):
    """Test printing profiling report."""
    profiler = NodeProfiler()

    with profiler.profile_node("node1"):
        time.sleep(0.01)

    profiler.print_report()

    captured = capsys.readouterr()
    assert "Node Profiling Report" in captured.out
    assert "node1" in captured.out


def test_graph_profiler_basic():
    """Test basic graph profiling."""
    profiler = GraphProfiler()

    with profiler.profile_run():
        time.sleep(0.01)

    summary = profiler.get_summary()
    assert summary["total_runs"] == 1
    assert summary["total_time"] >= 0.01
    assert summary["avg_time_per_run"] >= 0.01


def test_graph_profiler_multiple_runs():
    """Test profiling multiple graph runs."""
    profiler = GraphProfiler()

    for i in range(3):
        with profiler.profile_run():
            time.sleep(0.01)

    summary = profiler.get_summary()
    assert summary["total_runs"] == 3
    assert summary["total_time"] >= 0.03


def test_graph_profiler_with_nodes():
    """Test graph profiler with node profiling."""
    profiler = GraphProfiler()

    with profiler.profile_run():
        with profiler.node_profiler.profile_node("node1"):
            time.sleep(0.01)
        with profiler.node_profiler.profile_node("node2"):
            time.sleep(0.01)

    summary = profiler.get_summary()
    assert "node_stats" in summary
    assert "node1" in summary["node_stats"]
    assert "node2" in summary["node_stats"]


def test_graph_profiler_checkpoint_tracking():
    """Test checkpoint operation tracking."""
    profiler = GraphProfiler()

    with profiler.profile_run():
        time.sleep(0.01)

    profiler.record_checkpoint_save()
    profiler.record_checkpoint_save()
    profiler.record_checkpoint_load()

    summary = profiler.get_summary()
    assert summary["checkpoints_saved"] == 2
    assert summary["checkpoints_loaded"] == 1


def test_graph_profiler_cache_tracking():
    """Test cache hit/miss tracking."""
    profiler = GraphProfiler()

    with profiler.profile_run():
        time.sleep(0.01)

    profiler.record_cache_hit()
    profiler.record_cache_hit()
    profiler.record_cache_miss()

    summary = profiler.get_summary()
    assert summary["cache_hits"] == 2
    assert summary["cache_misses"] == 1
    assert abs(summary["cache_hit_rate"] - 2.0 / 3.0) < 0.01


def test_graph_profiler_zero_cache_operations():
    """Test cache hit rate with no cache operations."""
    profiler = GraphProfiler()

    with profiler.profile_run():
        time.sleep(0.01)

    summary = profiler.get_summary()
    assert summary["cache_hit_rate"] == 0.0


def test_graph_profiler_print_report(capsys):
    """Test printing comprehensive profiling report."""
    profiler = GraphProfiler()

    with profiler.profile_run():
        with profiler.node_profiler.profile_node("test_node"):
            time.sleep(0.01)

    profiler.record_checkpoint_save()
    profiler.record_cache_hit()

    profiler.print_report()

    captured = capsys.readouterr()
    assert "Graph Profiling Report" in captured.out
    assert "Node Profiling Report" in captured.out
    assert "test_node" in captured.out


def test_graph_profiler_export_json(tmp_path):
    """Test exporting profiling data to JSON."""
    profiler = GraphProfiler()

    with profiler.profile_run():
        time.sleep(0.01)

    json_file = tmp_path / "profiling.json"
    profiler.export_json(str(json_file))

    assert json_file.exists()

    # Read and verify JSON
    import json

    with open(json_file) as f:
        data = json.load(f)

    assert "total_runs" in data
    assert data["total_runs"] == 1


def test_graph_profiler_no_runs():
    """Test profiler with no runs."""
    profiler = GraphProfiler()

    summary = profiler.get_summary()
    assert "error" in summary
    assert summary["error"] == "No graph runs profiled"


def test_performance_recommendations_low_cache_hit_rate():
    """Test recommendations for low cache hit rate."""
    profiler = GraphProfiler()

    with profiler.profile_run():
        time.sleep(0.01)

    # Simulate low cache hit rate
    for _ in range(15):
        profiler.record_cache_miss()

    for _ in range(5):
        profiler.record_cache_hit()

    recommendations = PerformanceRecommendations.analyze(profiler)
    recommendation_text = " ".join(recommendations)
    assert "cache hit rate" in recommendation_text.lower()


def test_performance_recommendations_high_cache_hit_rate():
    """Test recommendations for high cache hit rate."""
    profiler = GraphProfiler()

    with profiler.profile_run():
        time.sleep(0.01)

    # Simulate high cache hit rate
    for _ in range(20):
        profiler.record_cache_hit()

    for _ in range(2):
        profiler.record_cache_miss()

    recommendations = PerformanceRecommendations.analyze(profiler)
    recommendation_text = " ".join(recommendations)
    assert (
        "excellent" in recommendation_text.lower()
        or "good" in recommendation_text.lower()
    )


def test_performance_recommendations_slowest_nodes():
    """Test identification of slowest nodes."""
    profiler = GraphProfiler()

    with profiler.profile_run():
        with profiler.node_profiler.profile_node("slow_node"):
            time.sleep(0.05)
        with profiler.node_profiler.profile_node("fast_node"):
            time.sleep(0.001)

    recommendations = PerformanceRecommendations.analyze(profiler)
    recommendation_text = " ".join(recommendations)
    assert (
        "slowest nodes" in recommendation_text.lower()
        or "slow_node" in recommendation_text.lower()
    )


def test_performance_recommendations_high_checkpoint_frequency():
    """Test recommendations for high checkpoint frequency."""
    profiler = GraphProfiler()

    # Run multiple times with many checkpoints
    for _ in range(5):
        with profiler.profile_run():
            time.sleep(0.01)

        # Simulate many checkpoints per run
        for _ in range(15):
            profiler.record_checkpoint_save()

    recommendations = PerformanceRecommendations.analyze(profiler)
    recommendation_text = " ".join(recommendations)
    assert "checkpoint" in recommendation_text.lower()


def test_performance_recommendations_slow_execution():
    """Test recommendations for slow execution."""
    profiler = GraphProfiler()

    with profiler.profile_run():
        time.sleep(0.15)  # > 100ms

    recommendations = PerformanceRecommendations.analyze(profiler)
    recommendation_text = " ".join(recommendations)
    # Should provide performance tips for slow execution
    assert (
        "cache" in recommendation_text.lower()
        or "performance" in recommendation_text.lower()
    )


def test_performance_recommendations_print(capsys):
    """Test printing performance recommendations."""
    profiler = GraphProfiler()

    with profiler.profile_run():
        time.sleep(0.01)

    PerformanceRecommendations.print_recommendations(profiler)

    captured = capsys.readouterr()
    assert "Performance Recommendations" in captured.out


def test_performance_recommendations_no_data():
    """Test recommendations with no profiling data."""
    profiler = GraphProfiler()

    recommendations = PerformanceRecommendations.analyze(profiler)
    assert len(recommendations) == 1
    assert "no profiling data" in recommendations[0].lower()


def test_profile_function_decorator(capsys):
    """Test profile_function decorator."""

    @profile_function
    def slow_function():
        time.sleep(0.01)
        return 42

    result = slow_function()

    assert result == 42

    captured = capsys.readouterr()
    assert "slow_function took" in captured.out
    assert "ms" in captured.out


def test_create_profiler():
    """Test convenience function for creating profiler."""
    profiler = create_profiler()
    assert isinstance(profiler, GraphProfiler)


def test_create_node_profiler():
    """Test convenience function for creating node profiler."""
    profiler = create_node_profiler()
    assert isinstance(profiler, NodeProfiler)


def test_node_profiler_exception_handling():
    """Test that profiler handles exceptions gracefully."""
    profiler = NodeProfiler()

    try:
        with profiler.profile_node("failing_node"):
            raise ValueError("Test error")
    except ValueError:
        pass

    # Should still record timing even with exception
    stats = profiler.get_stats()
    assert "failing_node" in stats
    assert stats["failing_node"]["count"] == 1


def test_graph_profiler_exception_handling():
    """Test that graph profiler handles exceptions gracefully."""
    profiler = GraphProfiler()

    try:
        with profiler.profile_run():
            raise ValueError("Test error")
    except ValueError:
        pass

    # Should still record the run
    summary = profiler.get_summary()
    assert summary["total_runs"] == 1


def test_empty_node_profiler_print(capsys):
    """Test printing report with no data."""
    profiler = NodeProfiler()
    profiler.print_report()

    captured = capsys.readouterr()
    assert "No profiling data" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
