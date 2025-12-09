"""
Shim module for monkeypatching LangGraph with Rust implementations.

This module provides functionality to replace core LangGraph algorithm functions
with high-performance Rust counterparts while maintaining API compatibility.
"""

import importlib
import sys
import warnings
from typing import Any, Dict

# Track what we've patched
_patched_functions: Dict[str, Any] = {}
_original_functions: Dict[str, Any] = {}


def patch_langgraph() -> bool:
    """
    Patch LangGraph algorithm functions with Rust-accelerated implementations.

    This replaces hot-path functions in langgraph.pregel._algo with versions
    that use Rust for performance-critical operations while maintaining
    exact API compatibility.

    Returns:
        bool: True if patching was successful, False otherwise.
    """
    try:
        # Import our acceleration shims
        from .algo_shims import create_accelerated_apply_writes

        # These are available for future use but currently commented out:
        # create_accelerated_prepare_next_tasks, create_accelerated_read_channels

        patches_applied = []

        # Patch apply_writes in _algo module
        if _patch_function(
            "langgraph.pregel._algo", "apply_writes", create_accelerated_apply_writes
        ):
            patches_applied.append("apply_writes")

        # Patch prepare_next_tasks (when ready)
        # if _patch_function(
        #     "langgraph.pregel._algo",
        #     "prepare_next_tasks",
        #     create_accelerated_prepare_next_tasks
        # ):
        #     patches_applied.append("prepare_next_tasks")

        # Patch read_channels (when ready)
        # if _patch_function(
        #     "langgraph.pregel._io",
        #     "read_channels",
        #     create_accelerated_read_channels
        # ):
        #     patches_applied.append("read_channels")

        if patches_applied:
            print("✓ Fast LangGraph acceleration enabled:")
            for func in patches_applied:
                print(f"  - {func} (Rust-accelerated)")
            return True
        else:
            print("✓ Fast LangGraph loaded (no patches applied)")
            return True

    except ImportError as e:
        print(f"✗ Failed to import acceleration modules: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during patching: {e}")
        import traceback

        traceback.print_exc()
        return False


def unpatch_langgraph() -> bool:
    """
    Restore the original LangGraph implementations.

    Returns:
        bool: True if unpatching was successful, False otherwise.
    """
    try:
        unpatched = []

        for full_func_name, original_func in list(_original_functions.items()):
            module_name, func_name = full_func_name.rsplit(".", 1)

            if module_name in sys.modules:
                module = sys.modules[module_name]
                if hasattr(module, func_name):
                    setattr(module, func_name, original_func)
                    unpatched.append(full_func_name)

        # Clear tracking
        _patched_functions.clear()
        _original_functions.clear()

        if unpatched:
            print(f"✓ Successfully unpatched: {', '.join(unpatched)}")
            return True
        else:
            print("✓ No patches to remove")
            return True

    except Exception as e:
        print(f"✗ Error during unpatching: {e}")
        return False


def _patch_function(
    module_name: str, func_name: str, accelerator_factory: callable
) -> bool:
    """
    Internal function to patch a specific function in a module.

    Args:
        module_name: Name of the module to patch
        func_name: Name of the function to patch
        accelerator_factory: Function that takes the original function and returns accelerated version

    Returns:
        bool: True if patching was successful, False otherwise.
    """
    try:
        # Import the module
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            # Module doesn't exist, skip
            return False

        # Check if the function exists in the module
        if not hasattr(module, func_name):
            warnings.warn(
                f"Function {func_name} not found in {module_name}", RuntimeWarning
            )
            return False

        # Store the original function for later restoration
        original_func = getattr(module, func_name)
        full_func_name = f"{module_name}.{func_name}"
        _original_functions[full_func_name] = original_func

        # Create accelerated version
        accelerated_func = accelerator_factory(original_func)

        # Replace the function in the module
        setattr(module, func_name, accelerated_func)

        # Track that we've patched this function
        _patched_functions[full_func_name] = accelerated_func

        return True

    except Exception as e:
        warnings.warn(f"Failed to patch {module_name}.{func_name}: {e}", RuntimeWarning)
        return False


def is_func_patched(module_name: str, func_name: str) -> bool:
    """
    Check if a specific function has been patched.

    Args:
        module_name: Name of the module
        func_name: Name of the function

    Returns:
        bool: True if the function has been patched, False otherwise.
    """
    full_func_name = f"{module_name}.{func_name}"
    return full_func_name in _original_functions


def get_patch_status() -> Dict[str, bool]:
    """
    Get the current patch status for all known LangGraph components.

    Returns:
        Dict mapping component names to their patch status.
    """
    components = [
        "langgraph.pregel._algo.apply_writes",
        "langgraph.pregel._algo.prepare_next_tasks",
        "langgraph.pregel._io.read_channels",
    ]

    status = {}
    for component in components:
        module_name, func_name = component.rsplit(".", 1)
        status[component] = is_func_patched(module_name, func_name)

    return status


def is_patched() -> bool:
    """
    Check if any LangGraph functions are currently patched.

    Returns:
        bool: True if at least one function is patched, False otherwise.
    """
    return len(_original_functions) > 0
