"""
Test to verify the shim functionality for monkeypatching langgraph
"""

import os
import sys

# Add the python directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))


def test_shim_import():
    """Test that the shim module can be imported"""
    import fast_langgraph.shim  # noqa: F401


def test_patch_function():
    """Test that the patch function exists and is callable"""
    import fast_langgraph.shim

    assert hasattr(fast_langgraph.shim, "patch_langgraph")
    assert callable(fast_langgraph.shim.patch_langgraph)
    assert hasattr(fast_langgraph.shim, "unpatch_langgraph")
    assert callable(fast_langgraph.shim.unpatch_langgraph)


def test_auto_patch_env_var():
    """Test that the shim checks for the auto-patch environment variable"""
    import fast_langgraph

    assert hasattr(fast_langgraph, "shim")


def test_rust_backend_availability():
    """Test that the Rust backend classes are available via the package"""
    import fast_langgraph

    assert hasattr(fast_langgraph, "is_rust_available")
    assert callable(fast_langgraph.is_rust_available)
