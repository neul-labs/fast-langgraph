#!/usr/bin/env python3
"""
Test script to verify FastChannelUpdater and RustLastValue channel work correctly.
"""

import sys
from pathlib import Path

# Add paths
FAST_LANGGRAPH_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(FAST_LANGGRAPH_ROOT))

def test_rust_channels():
    """Test RustLastValue channel basic operations."""
    print("Testing RustLastValue channel...")
    print("-" * 70)

    from fast_langgraph import RustLastValue

    # Create a channel
    chan = RustLastValue(int, "test_channel")
    print(f"✓ Created RustLastValue channel: {chan.key}")

    # Test update
    result = chan.update([42])
    print(f"✓ Update with [42]: {result}")

    # Test get
    value = chan.get()
    print(f"✓ Get value: {value}")
    assert value == 42, f"Expected 42, got {value}"

    # Test is_available
    available = chan.is_available()
    print(f"✓ Is available: {available}")
    assert available, "Channel should be available"

    # Test checkpoint
    checkpoint = chan.checkpoint()
    print(f"✓ Checkpoint: {checkpoint}")

    # Test from_checkpoint
    chan2 = RustLastValue.from_checkpoint(int, checkpoint, "restored")
    value2 = chan2.get()
    print(f"✓ Restored from checkpoint: {value2}")
    assert value2 == 42, f"Expected 42 after restore, got {value2}"

    # Test multiple values should fail
    try:
        chan.update([1, 2])
        print("✗ Should have raised error for multiple values")
        return False
    except ValueError as e:
        print(f"✓ Correctly raised error for multiple values: {str(e)[:50]}...")

    print()
    return True


def test_fast_channel_updater():
    """Test FastChannelUpdater with mixed channel types."""
    print("Testing FastChannelUpdater...")
    print("-" * 70)

    from fast_langgraph import FastChannelUpdater, RustLastValue

    # Create mixed channels
    rust_chan1 = RustLastValue(int, "rust1")
    rust_chan2 = RustLastValue(str, "rust2")

    channels = {
        "rust1": rust_chan1,
        "rust2": rust_chan2,
    }

    # Create pending writes
    pending_writes = {
        "rust1": [100],
        "rust2": ["hello"],
    }

    # Apply writes
    updater = FastChannelUpdater()
    updated = updater.apply_writes_batch(channels, pending_writes)

    print("✓ Applied writes to channels")
    print(f"✓ Updated channels: {updated}")

    # Verify updates
    val1 = rust_chan1.get()
    val2 = rust_chan2.get()

    print(f"✓ rust1 value: {val1}")
    print(f"✓ rust2 value: {val2}")

    assert val1 == 100, f"Expected 100, got {val1}"
    assert val2 == "hello", f"Expected 'hello', got {val2}"
    assert set(updated) == {"rust1", "rust2"}, f"Expected both channels updated, got {updated}"

    print()
    return True


def test_mixed_python_rust_channels():
    """Test FastChannelUpdater with both Python and Rust channels."""
    print("Testing mixed Python/Rust channels...")
    print("-" * 70)

    from fast_langgraph import FastChannelUpdater, RustLastValue

    # Import Python LastValue
    sys.path.insert(0, str(FAST_LANGGRAPH_ROOT / ".langgraph-test" / "langgraph" / "libs" / "langgraph"))
    from langgraph.channels import LastValue as PyLastValue

    # Create mixed channels
    rust_chan = RustLastValue(int, "rust")
    py_chan = PyLastValue(int)
    py_chan.key = "python"

    channels = {
        "rust": rust_chan,
        "python": py_chan,
    }

    # Create pending writes
    pending_writes = {
        "rust": [42],
        "python": [99],
    }

    # Apply writes
    updater = FastChannelUpdater()
    updated = updater.apply_writes_batch(channels, pending_writes)

    print("✓ Applied writes to mixed channels")
    print(f"✓ Updated channels: {updated}")

    # Verify updates
    rust_val = rust_chan.get()
    py_val = py_chan.get()

    print(f"✓ Rust channel value: {rust_val}")
    print(f"✓ Python channel value: {py_val}")

    assert rust_val == 42, f"Expected 42, got {rust_val}"
    assert py_val == 99, f"Expected 99, got {py_val}"
    assert set(updated) == {"rust", "python"}, f"Expected both channels updated, got {updated}"

    print()
    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("Fast Channel Tests")
    print("=" * 70)
    print()

    tests = [
        ("Basic RustLastValue operations", test_rust_channels),
        ("FastChannelUpdater", test_fast_channel_updater),
        ("Mixed Python/Rust channels", test_mixed_python_rust_channels),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✓ {name}: PASSED")
            else:
                failed += 1
                print(f"✗ {name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()

        print()

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
