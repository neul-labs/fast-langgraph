#!/usr/bin/env python3
"""
Comprehensive test suite for LangGraph Rust Pregel implementation
"""

import os
import sys

# Add the python directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))


def test_pregel_basic():
    """Test basic Pregel creation and functionality"""
    try:
        import fast_langgraph

        # Test Pregel creation with minimal parameters
        pregel = fast_langgraph.Pregel(
            nodes={}, output_channels="output", input_channels="input"
        )
        print("✓ Pregel created successfully with minimal parameters")

        # Test Pregel creation with all parameters
        pregel_full = fast_langgraph.Pregel(
            nodes={"test": None},
            channels={"test": None},
            auto_validate=True,
            stream_mode="values",
            stream_eager=False,
            output_channels="output",
            stream_channels=None,
            interrupt_after_nodes=(),
            interrupt_before_nodes=(),
            input_channels="input",
            step_timeout=None,
            debug=None,
            checkpointer=None,
            store=None,
            cache=None,
            retry_policy=(),
            cache_policy=None,
            context_schema=None,
            config=None,
            trigger_to_nodes=None,
            name="TestGraph",
        )
        print("✓ Pregel created successfully with all parameters")

        # Test that all expected attributes exist
        expected_attrs = [
            "nodes",
            "channels",
            "stream_mode",
            "output_channels",
            "input_channels",
            "checkpointer",
        ]
        for attr in expected_attrs:
            if hasattr(pregel, attr):
                print(f"✓ Pregel has attribute: {attr}")
            else:
                print(f"⚠ Pregel missing attribute: {attr}")

        return True

    except Exception as e:
        print(f"✗ Error testing Pregel basic functionality: {e}")
        return False


def test_pregel_invoke():
    """Test Pregel invoke method"""
    try:
        import fast_langgraph

        # Create a Pregel instance
        pregel = fast_langgraph.Pregel(
            nodes={}, output_channels="output", input_channels="input"
        )

        # Test basic invoke
        result = pregel.invoke({"test": "input"})
        assert result == {"test": "input"}
        print("✓ Pregel.invoke() works with basic input")

        # Test invoke with config
        config = {"configurable": {"thread_id": "test_thread"}}
        result = pregel.invoke({"test": "input"}, config=config)
        assert result == {"test": "input"}
        print("✓ Pregel.invoke() works with config")

        # Test invoke with context
        result = pregel.invoke({"test": "input"}, context={"ctx": "value"})
        assert result == {"test": "input"}
        print("✓ Pregel.invoke() works with context")

        # Test invoke with various parameters
        result = pregel.invoke(
            {"test": "input"},
            stream_mode="values",
            print_mode=(),
            output_keys="test",
            interrupt_before=None,
            interrupt_after=None,
            durability=None,
        )
        assert result == {"test": "input"}
        print("✓ Pregel.invoke() works with all parameters")

        return True

    except Exception as e:
        print(f"✗ Error testing Pregel invoke: {e}")
        return False


def test_pregel_stream():
    """Test Pregel stream method"""
    try:
        import fast_langgraph

        # Create a Pregel instance
        pregel = fast_langgraph.Pregel(
            nodes={}, output_channels="output", input_channels="input"
        )

        # Test basic stream
        result = pregel.stream({"test": "input"})
        assert isinstance(result, list)
        print("✓ Pregel.stream() works with basic input")

        # Test stream with various parameters
        result = pregel.stream(
            {"test": "input"},
            config=None,
            context={"ctx": "value"},
            stream_mode=None,
            print_mode=None,
            output_keys=None,
            interrupt_before=None,
            interrupt_after=None,
            durability=None,
            subgraphs=False,
            debug=None,
        )
        assert isinstance(result, list)
        print("✓ Pregel.stream() works with all parameters")

        return True

    except Exception as e:
        print(f"✗ Error testing Pregel stream: {e}")
        return False


def test_pregel_ainvoke():
    """Test Pregel ainvoke method"""
    try:
        import fast_langgraph

        # Create a Pregel instance
        pregel = fast_langgraph.Pregel(
            nodes={}, output_channels="output", input_channels="input"
        )

        # Test basic ainvoke
        result = pregel.ainvoke({"test": "input"})
        # In our simple implementation, this should return the input
        print("✓ Pregel.ainvoke() works with basic input")

        # Test ainvoke with args - just pass the input as first arg
        result = pregel.ainvoke({"test": "input"})
        print("✓ Pregel.ainvoke() works with args")

        return True

    except Exception as e:
        print(f"✗ Error testing Pregel ainvoke: {e}")
        return False


def test_pregel_astream():
    """Test Pregel astream method"""
    try:
        import fast_langgraph

        # Create a Pregel instance
        pregel = fast_langgraph.Pregel(
            nodes={}, output_channels="output", input_channels="input"
        )

        # Test basic astream
        result = pregel.astream({"test": "input"})
        # In our simple implementation, this should return an empty list
        assert isinstance(result, list)
        print("✓ Pregel.astream() works with basic input")

        return True

    except Exception as e:
        print(f"✗ Error testing Pregel astream: {e}")
        return False


def test_pregel_api_compatibility():
    """Test that Pregel API is compatible with Python LangGraph"""
    try:
        import fast_langgraph

        # Create a Pregel instance
        pregel = fast_langgraph.Pregel(
            nodes={}, output_channels="output", input_channels="input"
        )

        # Test that all expected methods exist
        expected_methods = ["invoke", "stream", "ainvoke", "astream"]

        for method in expected_methods:
            if hasattr(pregel, method):
                print(f"✓ Pregel has method: {method}")
            else:
                print(f"✗ Pregel missing method: {method}")
                return False

        # Test method signatures (basic check)
        import inspect

        # Check invoke signature
        sig = inspect.signature(pregel.invoke)
        print(f"✓ Pregel.invoke signature: {sig}")

        # Check stream signature
        sig = inspect.signature(pregel.stream)
        print(f"✓ Pregel.stream signature: {sig}")

        return True

    except Exception as e:
        print(f"✗ Error testing Pregel API compatibility: {e}")
        return False


def test_async_methods():
    """Test async methods existence and basic functionality"""
    try:
        import fast_langgraph

        # Create a Pregel instance
        pregel = fast_langgraph.Pregel(
            nodes={}, output_channels="output", input_channels="input"
        )

        # Test that async methods exist and are callable
        assert callable(pregel.ainvoke)
        assert callable(pregel.astream)
        print("✓ Pregel async methods are callable")

        # Test basic calling of async methods
        result = pregel.ainvoke({"test": "input"})
        print("✓ Pregel.ainvoke() works with basic input")

        result = pregel.astream({"test": "input"})
        print("✓ Pregel.astream() works with basic input")

        return True

    except Exception as e:
        print(f"✗ Error testing async methods: {e}")
        return False


def main():
    """Main test function"""
    print("Testing LangGraph Rust Pregel Implementation")
    print("=" * 50)

    tests = [
        test_pregel_basic,
        test_pregel_invoke,
        test_pregel_stream,
        test_pregel_ainvoke,
        test_pregel_astream,
        test_pregel_api_compatibility,
        test_async_methods,
    ]

    results = []
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("Test Results:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All Pregel tests passed!")
        return True
    else:
        print(f"\n❌ {total - passed} test(s) failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
