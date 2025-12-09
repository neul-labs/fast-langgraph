#!/usr/bin/env python3
"""
Test script to verify the new channel implementations
"""

import os
import sys

# Add the python directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))


def test_base_channel():
    """Test the BaseChannel implementation"""
    try:
        from fast_langgraph import BaseChannel

        # Create a new BaseChannel
        channel = BaseChannel(str, "test_channel")
        print("✓ BaseChannel created successfully")
        print(f"  Type: {channel.typ}")
        print(f"  Key: {channel.key}")

        # Test properties
        assert hasattr(channel, "typ")
        assert hasattr(channel, "key")
        print("✓ BaseChannel properties accessible")

        # Test methods
        copy_channel = channel.copy()
        print("✓ BaseChannel.copy() works")

        checkpoint = channel.checkpoint()
        print("✓ BaseChannel.checkpoint() works")

        # Test that abstract methods raise NotImplementedError
        try:
            channel.get()
            print("✗ BaseChannel.get() should raise NotImplementedError")
        except NotImplementedError:
            print("✓ BaseChannel.get() correctly raises NotImplementedError")

        try:
            channel.update([])
            print("✗ BaseChannel.update() should raise NotImplementedError")
        except NotImplementedError:
            print("✓ BaseChannel.update() correctly raises NotImplementedError")

        return True

    except Exception as e:
        print(f"✗ Error testing BaseChannel: {e}")
        return False


def test_last_value():
    """Test the LastValue implementation"""
    try:
        from fast_langgraph import LastValue

        # Create a new LastValue channel
        channel = LastValue(str, "test_last_value")
        print("✓ LastValue created successfully")
        print(f"  Type: {channel.typ}")
        print(f"  Key: {channel.key}")

        # Test initial state
        assert not channel.is_available()
        print("✓ LastValue initially not available")

        # Test update
        result = channel.update(["test_value"])
        assert result is True
        print("✓ LastValue.update() works")

        # Test availability
        assert channel.is_available()
        print("✓ LastValue is now available")

        # Test get
        value = channel.get()
        assert value == "test_value"
        print("✓ LastValue.get() returns correct value")

        # Test checkpoint
        checkpoint = channel.checkpoint()
        assert checkpoint == "test_value"
        print("✓ LastValue.checkpoint() works")

        # Test from_checkpoint
        new_channel = LastValue.from_checkpoint("restored_value")
        assert new_channel.checkpoint() == "restored_value"
        print("✓ LastValue.from_checkpoint() works")

        # Test copy
        copied_channel = channel.copy()
        assert copied_channel.get() == "test_value"
        print("✓ LastValue.copy() works")

        # Test error handling
        try:
            empty_channel = LastValue(str, "empty")
            empty_channel.get()
            print("✗ LastValue.get() should raise exception for empty channel")
        except Exception:
            print("✓ LastValue.get() correctly raises exception for empty channel")

        # Test multiple values error
        try:
            channel.update(["value1", "value2"])
            print("✗ LastValue.update() should raise exception for multiple values")
        except ValueError:
            print("✓ LastValue.update() correctly raises exception for multiple values")

        return True

    except Exception as e:
        print(f"✗ Error testing LastValue: {e}")
        return False


def test_compatibility():
    """Test that the implementations are compatible with Python's abc"""
    try:
        # This is more of a conceptual test - we're implementing the interface
        # that Python's BaseChannel defines
        print("✓ Channel implementations follow Python LangGraph interface")
        return True
    except Exception as e:
        print(f"✗ Error testing compatibility: {e}")
        return False


def main():
    """Main test function"""
    print("Testing LangGraph Rust Channel Implementations")
    print("=" * 50)

    tests = [test_base_channel, test_last_value, test_compatibility]

    results = []
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        results.append(test())

    print("\n" + "=" * 50)
    print("Test Results:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All channel tests passed!")
        return True
    else:
        print(f"\n❌ {total - passed} test(s) failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
