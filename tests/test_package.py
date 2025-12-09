"""
Test to verify the package structure and basic functionality
"""

import os
import sys

# Add the python directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))


def test_imports():
    """Test that all expected modules can be imported"""
    try:
        import fast_langgraph

        print("✓ Successfully imported fast_langgraph")

        # Test that all expected attributes are available
        expected_attrs = [
            "__version__",
            "PregelExecutor",
            "Channel",
            "LastValueChannel",
            "Checkpoint",
        ]
        for attr in expected_attrs:
            if hasattr(fast_langgraph, attr):
                print(f"✓ Found expected attribute: {attr}")
            else:
                print(f"✗ Missing expected attribute: {attr}")

        # Test creating instances
        executor = fast_langgraph.PregelExecutor()
        print("✓ Successfully created PregelExecutor")

        channel = fast_langgraph.LastValueChannel()
        print("✓ Successfully created LastValueChannel")

        checkpoint = fast_langgraph.Checkpoint()
        print("✓ Successfully created Checkpoint")

        return True

    except ImportError as e:
        print(f"✗ Failed to import fast_langgraph: {e}")
        return False
    except Exception as e:
        print(f"✗ Error testing package: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality of the package"""
    try:
        import fast_langgraph

        # Test basic functionality
        executor = fast_langgraph.PregelExecutor()
        result = executor.execute_graph({"test": "value"})
        print(f"✓ Basic execution works: {result}")

        channel = fast_langgraph.LastValueChannel()
        channel.update(["test_value"])
        value = channel.get()
        print(f"✓ Channel operations work: {value}")

        checkpoint = fast_langgraph.Checkpoint()
        checkpoint.channel_values["test"] = "test_value"
        json_str = checkpoint.to_json()
        print(f"✓ Checkpoint operations work: {json_str}")

        return True

    except Exception as e:
        print(f"✗ Error testing basic functionality: {e}")
        return False


if __name__ == "__main__":
    print("Testing LangGraph Rust Package")
    print("=" * 40)

    import_success = test_imports()
    functionality_success = test_basic_functionality()

    print("\n" + "=" * 40)
    print("Test Results:")
    print(f"Import Test: {'✓ PASS' if import_success else '✗ FAIL'}")
    print(f"Functionality Test: {'✓ PASS' if functionality_success else '✗ FAIL'}")

    if import_success and functionality_success:
        print("\n🎉 Package is working correctly!")
    else:
        print("\n❌ Package has issues that need to be addressed!")
