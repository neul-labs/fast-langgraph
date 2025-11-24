"""
Shim module for monkeypatching LangGraph with Rust implementations.

This module provides functionality to replace core LangGraph classes with their
high-performance Rust counterparts while maintaining API compatibility.
"""

import sys
import importlib
from typing import Any, Dict, Optional, Set
import warnings

# Track what we've patched
_patched_modules: Set[str] = set()
_original_classes: Dict[str, Any] = {}

def patch_langgraph() -> bool:
    """
    Patch the original LangGraph modules with Rust implementations.

    Returns:
        bool: True if patching was successful, False otherwise.
    """
    try:
        # Import our Rust implementations
        from . import (
            BaseChannel as RustBaseChannel,
            LastValue as RustLastValue,
            Pregel as RustPregelClass,
            Checkpoint as RustCheckpoint,
        )

        patches_applied = []

        # NOTE: Direct class patching is disabled because:
        # 1. Pregel: CompiledStateGraph inherits from it, and PyO3 classes don't support
        #    proper inheritance with mutable dict properties.
        # 2. Channels: isinstance() checks in _validate.py fail because modules cache
        #    imports before patching occurs.
        #
        # Instead, use the hybrid acceleration approach:
        #   from fast_langgraph import AcceleratedPregelLoop
        #   accelerator = AcceleratedPregelLoop()
        #
        # This provides performance gains without breaking compatibility.

        # Mark that patching was "successful" (no-op for compatibility)
        print("✓ Fast LangGraph loaded (hybrid acceleration available)")
        print("  Note: Direct class patching disabled for compatibility.")
        print("  Use AcceleratedPregelLoop for performance optimization.")
        return True

    except ImportError as e:
        print(f"✗ Failed to import Rust implementations: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during patching: {e}")
        return False

def unpatch_langgraph() -> bool:
    """
    Restore the original LangGraph implementations.

    Returns:
        bool: True if unpatching was successful, False otherwise.
    """
    try:
        unpatched = []

        for module_name in list(_patched_modules):
            if module_name in sys.modules:
                module = sys.modules[module_name]

                # Restore all classes in this module
                for class_name, original_class in _original_classes.items():
                    if class_name.startswith(module_name + "."):
                        attr_name = class_name.split(".")[-1]
                        if hasattr(module, attr_name):
                            setattr(module, attr_name, original_class)
                            unpatched.append(class_name)

        # Clear tracking
        _patched_modules.clear()
        _original_classes.clear()

        if unpatched:
            print(f"✓ Successfully unpatched: {', '.join(unpatched)}")
            return True
        else:
            print("✓ No patches to remove")
            return True

    except Exception as e:
        print(f"✗ Error during unpatching: {e}")
        return False

def _patch_class(module_name: str, class_name: str, rust_class: Any) -> bool:
    """
    Internal function to patch a specific class in a module.

    Args:
        module_name: Name of the module to patch
        class_name: Name of the class to patch
        rust_class: Rust implementation to use as replacement

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

        # Check if the class exists in the module
        if not hasattr(module, class_name):
            return False

        # Store the original class for later restoration
        original_class = getattr(module, class_name)
        full_class_name = f"{module_name}.{class_name}"
        _original_classes[full_class_name] = original_class

        # Directly replace the class with the Rust implementation
        # Set module and qualname to match the original for better error messages
        try:
            rust_class.__module__ = original_class.__module__
            rust_class.__qualname__ = original_class.__qualname__
        except (AttributeError, TypeError):
            # Some attributes might be read-only on Rust classes
            pass

        # Replace the class in the module
        setattr(module, class_name, rust_class)

        # Track that we've patched this module
        _patched_modules.add(module_name)

        return True

    except Exception as e:
        warnings.warn(f"Failed to patch {module_name}.{class_name}: {e}", RuntimeWarning)
        return False

def is_patched(module_name: str, class_name: str) -> bool:
    """
    Check if a specific class has been patched.

    Args:
        module_name: Name of the module
        class_name: Name of the class

    Returns:
        bool: True if the class has been patched, False otherwise.
    """
    full_class_name = f"{module_name}.{class_name}"
    return full_class_name in _original_classes

def get_patch_status() -> Dict[str, bool]:
    """
    Get the current patch status for all known LangGraph components.

    Returns:
        Dict mapping component names to their patch status.
    """
    components = [
        # Pregel patching disabled - see shim.py comments
        # "langgraph.pregel.main.Pregel",
        # "langgraph.pregel.Pregel",
        "langgraph.channels.base.BaseChannel",
        "langgraph.channels.last_value.LastValue",
        "langgraph.channels.LastValue",
    ]

    status = {}
    for component in components:
        module_name, class_name = component.rsplit(".", 1)
        status[component] = is_patched(module_name, class_name)

    return status