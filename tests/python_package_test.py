#!/usr/bin/env python3
"""
Test script to verify Python package structure
"""


def test_package_structure():
    """Test that our package structure is correct"""
    try:
        # Try to import the package
        import os
        import sys

        # Add the python directory to the path
        package_path = os.path.join(os.path.dirname(__file__), "..", "python")
        sys.path.insert(0, package_path)

        # Try to import the package
        import fast_langgraph

        print("✅ Successfully imported fast_langgraph package")

        # Check that it has the expected attributes
        expected_attrs = ["__version__"]
        for attr in expected_attrs:
            if hasattr(fast_langgraph, attr):
                print(f"✅ Found expected attribute: {attr}")
            else:
                print(f"❌ Missing expected attribute: {attr}")

        return True

    except ImportError as e:
        print(f"❌ Failed to import package: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing package: {e}")
        return False


def main():
    """Main test function"""
    print("Testing LangGraph Rust Package Structure")
    print("=" * 40)

    # Test package structure
    success = test_package_structure()

    print("\n" + "=" * 40)
    print("Test Results:")
    print(f"Package Structure: {'✅ PASS' if success else '❌ FAIL'}")

    if success:
        print("\n🎉 Package structure is working correctly!")
        print("Ready for integration with LangGraph.")
    else:
        print("\n❌ Package structure failed!")
        print("Please check your package structure.")


if __name__ == "__main__":
    main()
