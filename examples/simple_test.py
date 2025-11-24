#!/usr/bin/env python3
"""
Simple test to demonstrate the LangGraph Rust shim functionality.

This test doesn't require LangGraph to be installed and shows the
basic monkeypatching mechanism working.
"""

import sys
import os
import time

# Add the langgraph-rs package to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_shim_functionality():
    """Test the shim module without requiring LangGraph installation."""
    print("=== Testing Shim Functionality ===")

    try:
        import fast_langgraph.shim as shim

        print("✓ Successfully imported shim module")

        # Check initial patch status
        status = shim.get_patch_status()
        print(f"✓ Initial patch status: {len(status)} components tracked")

        for component, is_patched in status.items():
            print(f"  - {component}: {'✓ patched' if is_patched else '✗ not patched'}")

        # Test patching (will fail gracefully since LangGraph isn't installed)
        print("\n--- Attempting to patch LangGraph ---")
        patch_result = shim.patch_langgraph()
        print(f"Patch result: {patch_result}")

        # Test unpatching
        print("\n--- Attempting to unpatch LangGraph ---")
        unpatch_result = shim.unpatch_langgraph()
        print(f"Unpatch result: {unpatch_result}")

        return True

    except Exception as e:
        print(f"✗ Error testing shim: {e}")
        return False

def test_rust_availability():
    """Test if Rust implementations are available."""
    print("\n=== Testing Rust Availability ===")

    try:
        import fast_langgraph

        print("✓ Successfully imported fast_langgraph")

        rust_available = fast_langgraph.is_rust_available()
        print(f"✓ Rust available: {rust_available}")

        if rust_available:
            print("✓ Rust extension is built and working")

            # Test direct usage
            try:
                channel = fast_langgraph.LastValue(str, "test")
                print("✓ Can create LastValue channel")

                channel.update(["test_value"])
                print("✓ Can update channel")

                value = channel.get()
                print(f"✓ Can get value: {value}")

                # Test checkpoint
                checkpoint = fast_langgraph.Checkpoint()
                print("✓ Can create checkpoint")

                json_str = checkpoint.to_json()
                print(f"✓ Can serialize to JSON: {len(json_str)} chars")

                return True

            except Exception as e:
                print(f"✗ Error testing Rust implementations: {e}")
                return False
        else:
            print("ℹ Rust extension not available (expected if not built)")
            print("  Run 'pip install -e .' to build the extension")
            return True

    except ImportError as e:
        print(f"✗ Could not import fast_langgraph: {e}")
        return False

def test_performance_stub():
    """Test performance with stub implementations."""
    print("\n=== Testing Performance (Stub) ===")

    try:
        import fast_langgraph

        if not fast_langgraph.is_rust_available():
            print("ℹ Skipping performance test - Rust not available")
            return True

        # Basic performance test
        channel = fast_langgraph.LastValue(str, "perf_test")

        # Warm up
        for i in range(100):
            channel.update([f"warmup_{i}"])

        # Measure performance
        start_time = time.time()
        for i in range(10000):
            channel.update([f"test_{i}"])
        end_time = time.time()

        duration = end_time - start_time
        ops_per_second = 10000 / duration

        print(f"✓ Channel update performance: {ops_per_second:.0f} ops/sec")
        print(f"✓ Average time per update: {duration * 1000000 / 10000:.1f} μs")

        # Basic memory test
        memory_usage = channel.memory_usage()
        print(f"✓ Channel memory usage: {memory_usage} bytes")

        return True

    except Exception as e:
        print(f"✗ Error in performance test: {e}")
        return False

def main():
    """Main test function."""
    print("LangGraph Rust - Basic Functionality Test")
    print("=" * 50)

    tests = [
        ("Shim Functionality", test_shim_functionality),
        ("Rust Availability", test_rust_availability),
        ("Performance Test", test_performance_stub),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * len(test_name))
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")

    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed - check output above")

if __name__ == "__main__":
    main()