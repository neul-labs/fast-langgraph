"""
Integration tests for LangGraph Rust implementations.

These tests verify that the Rust implementations are compatible with the
original LangGraph Python API.
"""

import os
import sys
import time

import pytest

# Add the local package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import fast_langgraph

    RUST_AVAILABLE = fast_langgraph.is_rust_available()
except ImportError:
    RUST_AVAILABLE = False


class TestDirectUsage:
    """Test direct usage of Rust implementations."""

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extension not available")
    def test_last_value_channel_creation(self):
        """Test creating a LastValue channel."""
        channel = fast_langgraph.LastValue(str, "test_channel")
        assert channel is not None
        assert channel.key == "test_channel"

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extension not available")
    def test_last_value_channel_operations(self):
        """Test LastValue channel operations."""
        channel = fast_langgraph.LastValue(str, "test")

        # Initially not available
        assert not channel.is_available()

        # Update with a value
        result = channel.update(["test_value"])
        assert result is True
        assert channel.is_available()

        # Get the value
        value = channel.get()
        assert value == "test_value"

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extension not available")
    def test_checkpoint_creation(self):
        """Test creating a checkpoint."""
        checkpoint = fast_langgraph.Checkpoint()
        assert checkpoint is not None
        assert checkpoint.v == 1

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extension not available")
    def test_checkpoint_serialization(self):
        """Test checkpoint serialization."""
        checkpoint = fast_langgraph.Checkpoint()
        json_str = checkpoint.to_json()
        assert isinstance(json_str, str)
        assert '"v": 1' in json_str

        # Test deserialization
        new_checkpoint = fast_langgraph.Checkpoint.from_json(json_str)
        assert new_checkpoint.v == checkpoint.v

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extension not available")
    def test_pregel_creation(self):
        """Test creating a Pregel instance."""
        # Basic creation test
        pregel = fast_langgraph.Pregel(nodes={}, output_channels=[], input_channels=[])
        assert pregel is not None


class TestShimModule:
    """Test the shim module functionality."""

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extension not available")
    def test_patch_status(self):
        """Test getting patch status."""
        status = fast_langgraph.shim.get_patch_status()
        assert isinstance(status, dict)
        # New structure has 'automatic', 'manual', and 'summary' keys
        assert "automatic" in status
        assert "manual" in status
        assert "summary" in status
        assert isinstance(status["automatic"], dict)
        assert isinstance(status["manual"], dict)
        assert isinstance(status["summary"], str)
        # Check that automatic and manual contain bool values
        assert all(isinstance(v, bool) for v in status["automatic"].values())
        assert all(isinstance(v, bool) for v in status["manual"].values())

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extension not available")
    def test_patch_unpatch_cycle(self):
        """Test patching and unpatching."""
        # Get initial status
        initial_status = fast_langgraph.shim.get_patch_status()

        # Try to patch
        patch_result = fast_langgraph.shim.patch_langgraph()

        # Unpatch
        unpatch_result = fast_langgraph.shim.unpatch_langgraph()

        # Check that unpatching succeeded
        assert unpatch_result is True


class TestPerformance:
    """Basic performance tests."""

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extension not available")
    def test_channel_update_performance(self):
        """Test channel update performance."""
        import time

        channel = fast_langgraph.LastValue(int, "perf_test")

        # Warm up
        for i in range(100):
            channel.update([i])

        # Time the operations
        start_time = time.time()
        for i in range(10000):
            channel.update([i])
        end_time = time.time()

        duration = end_time - start_time
        ops_per_second = 10000 / duration

        print(f"Channel updates: {ops_per_second:.0f} ops/sec")

        # Should be significantly faster than pure Python
        # This is a basic smoke test
        assert ops_per_second > 1000  # At least 1K ops/sec

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extension not available")
    def test_checkpoint_serialization_performance(self):
        """Test checkpoint serialization performance."""
        import time

        checkpoint = fast_langgraph.Checkpoint()
        # Add some data
        checkpoint.channel_values = {f"channel_{i}": f"value_{i}" for i in range(100)}

        # Warm up
        for _ in range(10):
            checkpoint.to_json()

        # Time the operations
        start_time = time.time()
        for _ in range(1000):
            json_str = checkpoint.to_json()
        end_time = time.time()

        duration = end_time - start_time
        ops_per_second = 1000 / duration

        print(f"Checkpoint serialization: {ops_per_second:.0f} ops/sec")

        # Should be reasonably fast
        assert ops_per_second > 100  # At least 100 ops/sec


def test_rust_channel_performance():
    """Test that demonstrates the performance improvements of Rust channels."""
    try:
        # Import the Rust implementation if available
        import fast_langgraph
        from fast_langgraph import LastValueChannel

        # Test LastValueChannel performance
        channel = LastValueChannel(str)

        # Measure update performance
        start_time = time.perf_counter_ns()
        for i in range(1000):
            channel.update([f"value_{i}"])
        end_time = time.perf_counter_ns()

        avg_update_time = (end_time - start_time) / 1000
        print(f"Average LastValueChannel update time: {avg_update_time:.2f}ns")

        # Should be significantly faster than Python implementation
        assert avg_update_time < 1000  # Less than 1 microsecond average

        # Test get performance
        start_time = time.perf_counter_ns()
        for i in range(1000):
            value = channel.get()
        end_time = time.perf_counter_ns()

        avg_get_time = (end_time - start_time) / 1000
        print(f"Average LastValueChannel get time: {avg_get_time:.2f}ns")

        # Should be significantly faster than Python implementation
        assert avg_get_time < 500  # Less than 500ns average

    except ImportError:
        # Fall back to Python implementation if Rust is not available
        pytest.skip("Rust implementation not available")


def test_rust_checkpoint_performance():
    """Test that demonstrates the performance improvements of Rust checkpoints."""
    try:
        # Import the Rust implementation if available
        from fast_langgraph.checkpoint import Checkpoint

        # Test checkpoint creation performance
        start_time = time.perf_counter_ns()
        for i in range(100):
            checkpoint = Checkpoint()
            checkpoint.channel_values["test"] = f"value_{i}"
        end_time = time.perf_counter_ns()

        avg_creation_time = (end_time - start_time) / 100
        print(f"Average Checkpoint creation time: {avg_creation_time:.2f}ns")

        # Should be significantly faster than Python implementation
        assert avg_creation_time < 10000  # Less than 10 microseconds average

        # Test JSON serialization performance
        checkpoint = Checkpoint()
        checkpoint.channel_values["test"] = "test_value"

        start_time = time.perf_counter_ns()
        for i in range(100):
            json_str = checkpoint.to_json()
        end_time = time.perf_counter_ns()

        avg_serialization_time = (end_time - start_time) / 100
        print(f"Average JSON serialization time: {avg_serialization_time:.2f}ns")

        # Should be significantly faster than Python implementation
        assert avg_serialization_time < 5000  # Less than 5 microseconds average

    except ImportError:
        # Fall back to Python implementation if Rust is not available
        pytest.skip("Rust implementation not available")


def test_rust_pregel_executor_performance():
    """Test that demonstrates the performance improvements of Rust Pregel executor."""
    try:
        # Import the Rust implementation if available
        from fast_langgraph.pregel import PregelExecutor

        # Test executor creation performance
        start_time = time.perf_counter_ns()
        for i in range(100):
            executor: PregelExecutor[int, int] = PregelExecutor()
        end_time = time.perf_counter_ns()

        avg_creation_time = (end_time - start_time) / 100
        print(f"Average PregelExecutor creation time: {avg_creation_time:.2f}ns")

        # Should be significantly faster than Python implementation
        assert avg_creation_time < 5000  # Less than 5 microseconds average

    except ImportError:
        # Fall back to Python implementation if Rust is not available
        pytest.skip("Rust implementation not available")


def test_rust_memory_efficiency():
    """Test that demonstrates the memory efficiency of Rust implementation."""
    try:
        # Import the Rust implementation if available
        from fast_langgraph.channels import LastValueChannel
        from fast_langgraph.checkpoint import Checkpoint

        # Test memory usage of channels
        channel = LastValueChannel[str]()
        channel.update(["test_value"])

        # Memory usage should be minimal
        memory_usage = channel.memory_usage()
        print(f"LastValueChannel memory usage: {memory_usage} bytes")

        # Should be significantly less than Python implementation
        assert memory_usage < 100  # Less than 100 bytes

        # Test memory usage of checkpoints
        checkpoint = Checkpoint()
        checkpoint.channel_values["test"] = "test_value"

        memory_usage = checkpoint.memory_usage()
        print(f"Checkpoint memory usage: {memory_usage} bytes")

        # Should be significantly less than Python implementation
        assert memory_usage < 1000  # Less than 1KB

    except ImportError:
        # Fall back to Python implementation if Rust is not available
        pytest.skip("Rust implementation not available")


def test_rust_api_compatibility():
    """Test that demonstrates API compatibility with existing Python implementation."""
    try:
        # Import the Rust implementation if available
        from fast_langgraph.channels import Channel, LastValueChannel, TopicChannel
        from fast_langgraph.checkpoint import Checkpoint
        from fast_langgraph.pregel import PregelExecutor, PregelNode

        # Test that all expected interfaces are available
        assert hasattr(LastValueChannel, "update")
        assert hasattr(LastValueChannel, "get")
        assert hasattr(LastValueChannel, "is_available")

        # Test that all expected classes can be instantiated
        channel = LastValueChannel[str]()
        assert channel is not None

        topic_channel = TopicChannel[str](True)
        assert topic_channel is not None

        checkpoint = Checkpoint()
        assert checkpoint is not None

        executor: PregelExecutor[int, int] = PregelExecutor()
        assert executor is not None

        # Test basic functionality
        channel.update(["test"])
        assert channel.is_available()
        assert channel.get() == "test"

    except ImportError:
        # Fall back to Python implementation if Rust is not available
        pytest.skip("Rust implementation not available")


if __name__ == "__main__":
    # Run tests directly for development
    try:
        test_rust_channel_performance()
        print("✓ Channel performance test passed")
    except Exception as e:
        print(f"✗ Channel performance test failed: {e}")

    try:
        test_rust_checkpoint_performance()
        print("✓ Checkpoint performance test passed")
    except Exception as e:
        print(f"✗ Checkpoint performance test failed: {e}")

    try:
        test_rust_pregel_executor_performance()
        print("✓ Pregel executor performance test passed")
    except Exception as e:
        print(f"✗ Pregel executor performance test failed: {e}")

    try:
        test_rust_memory_efficiency()
        print("✓ Memory efficiency test passed")
    except Exception as e:
        print(f"✗ Memory efficiency test failed: {e}")

    try:
        test_rust_api_compatibility()
        print("✓ API compatibility test passed")
    except Exception as e:
        print(f"✗ API compatibility test failed: {e}")
