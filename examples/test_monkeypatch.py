#!/usr/bin/env python3
"""
Example showing how to monkeypatch LangGraph with Rust implementations.

This example demonstrates:
1. Importing LangGraph
2. Checking what classes are available before patching
3. Applying the monkeypatch
4. Verifying the classes have been replaced
5. Basic performance comparison
"""

import sys
import os
import time

# Add the langgraph-rs package to the path
sys.path.insert(0, os.path.dirname(__file__))

def test_without_patching():
    """Test original LangGraph implementation."""
    print("=== Testing WITHOUT Rust Patching ===")

    try:
        # Add LangGraph to path
        sys.path.insert(0, '/home/dipankar/Github/langgraph/libs/langgraph')

        # Import original LangGraph
        from langgraph.channels.last_value import LastValue
        from langgraph.pregel.main import Pregel

        print(f"✓ Original LastValue class: {LastValue}")
        print(f"✓ Original Pregel class: {Pregel}")

        # Test basic functionality
        channel = LastValue(str)
        print(f"✓ Created LastValue channel: {type(channel)}")

        # Basic performance test
        start_time = time.time()
        for i in range(1000):
            channel.update([f"value_{i}"])
        end_time = time.time()

        original_ops_per_sec = 1000 / (end_time - start_time)
        print(f"✓ Original performance: {original_ops_per_sec:.0f} updates/sec")

        return original_ops_per_sec

    except ImportError as e:
        print(f"✗ Could not import LangGraph: {e}")
        print("Make sure LangGraph is installed at ~/Github/langgraph")
        return None

def test_with_patching():
    """Test with Rust monkeypatching."""
    print("\n=== Testing WITH Rust Patching ===")

    try:
        import fast_langgraph

        print(f"✓ Rust available: {fast_langgraph.is_rust_available()}")

        # Apply the patch
        success = fast_langgraph.shim.patch_langgraph()
        print(f"✓ Patch applied: {success}")

        if success:
            # Check patch status
            status = fast_langgraph.shim.get_patch_status()
            patched_components = [k for k, v in status.items() if v]
            print(f"✓ Patched components: {patched_components}")

            # Import LangGraph again (should now use Rust implementations)
            from langgraph.channels.last_value import LastValue
            from langgraph.pregel.main import Pregel

            print(f"✓ Patched LastValue class: {LastValue}")
            print(f"✓ Patched Pregel class: {Pregel}")

            # Test the patched implementation
            channel = LastValue(str)
            print(f"✓ Created patched channel: {type(channel)}")

            # Performance test with patched version
            start_time = time.time()
            for i in range(1000):
                channel.update([f"value_{i}"])
            end_time = time.time()

            rust_ops_per_sec = 1000 / (end_time - start_time)
            print(f"✓ Rust performance: {rust_ops_per_sec:.0f} updates/sec")

            return rust_ops_per_sec
        else:
            print("✗ Patching failed")
            return None

    except Exception as e:
        print(f"✗ Error during patching: {e}")
        return None

def test_direct_usage():
    """Test direct usage of Rust implementations."""
    print("\n=== Testing Direct Rust Usage ===")

    try:
        import fast_langgraph

        if not fast_langgraph.is_rust_available():
            print("✗ Rust implementations not available")
            print("Run 'pip install -e .' to build the Rust extension")
            return None

        # Use Rust implementations directly
        channel = fast_langgraph.LastValue(str, "test_channel")
        print(f"✓ Direct Rust channel: {type(channel)}")

        # Test functionality
        channel.update(["direct_test"])
        value = channel.get()
        print(f"✓ Direct test value: {value}")

        # Performance test with direct usage
        start_time = time.time()
        for i in range(10000):  # More iterations for direct usage
            channel.update([f"value_{i}"])
        end_time = time.time()

        direct_ops_per_sec = 10000 / (end_time - start_time)
        print(f"✓ Direct Rust performance: {direct_ops_per_sec:.0f} updates/sec")

        return direct_ops_per_sec

    except Exception as e:
        print(f"✗ Error with direct usage: {e}")
        return None

def main():
    """Main test function."""
    print("LangGraph Rust Monkeypatch Test")
    print("=" * 40)

    # Test without patching first
    original_perf = test_without_patching()

    # Test with patching
    patched_perf = test_with_patching()

    # Test direct usage
    direct_perf = test_direct_usage()

    # Summary
    print("\n=== SUMMARY ===")

    if original_perf and patched_perf:
        improvement = patched_perf / original_perf
        print(f"Performance improvement with patching: {improvement:.1f}x")

    if original_perf and direct_perf:
        improvement = direct_perf / original_perf
        print(f"Performance improvement with direct usage: {improvement:.1f}x")

    # Test unpatching
    try:
        import fast_langgraph
        unpatch_success = fast_langgraph.shim.unpatch_langgraph()
        print(f"✓ Unpatching successful: {unpatch_success}")
    except Exception as e:
        print(f"✗ Unpatching failed: {e}")

if __name__ == "__main__":
    main()