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

        # Patch langgraph.pregel.main.Pregel
        if _patch_class("langgraph.pregel.main", "Pregel", RustPregelClass):
            patches_applied.append("langgraph.pregel.main.Pregel")

        # Patch langgraph.pregel.Pregel (from __init__.py)
        if _patch_class("langgraph.pregel", "Pregel", RustPregelClass):
            patches_applied.append("langgraph.pregel.Pregel")

        # Patch langgraph.channels classes
        if _patch_class("langgraph.channels.base", "BaseChannel", RustBaseChannel):
            patches_applied.append("langgraph.channels.base.BaseChannel")

        if _patch_class("langgraph.channels.last_value", "LastValue", RustLastValue):
            patches_applied.append("langgraph.channels.last_value.LastValue")

        if _patch_class("langgraph.channels", "LastValue", RustLastValue):
            patches_applied.append("langgraph.channels.LastValue")

        # Patch checkpoint classes if they exist
        try:
            if _patch_class("langgraph.checkpoint.base", "Checkpoint", RustCheckpoint):
                patches_applied.append("langgraph.checkpoint.base.Checkpoint")
        except ImportError:
            pass  # checkpoint module might not exist

        if patches_applied:
            print(f"✓ Successfully patched: {', '.join(patches_applied)}")
            return True
        else:
            print("✗ No LangGraph modules found to patch")
            return False

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

        # Create a wrapper class that inherits from the Rust implementation
        # but maintains the same module and name for compatibility
        class RustWrapper(rust_class):
            __module__ = original_class.__module__
            __qualname__ = original_class.__qualname__

            def __init__(self, *args, **kwargs):
                # Handle the different constructor signatures
                try:
                    super().__init__(*args, **kwargs)
                except Exception as e:
                    # Fallback: try to create with minimal args
                    warnings.warn(
                        f"Failed to initialize {class_name} with provided args, "
                        f"using defaults: {e}",
                        RuntimeWarning
                    )
                    try:
                        if class_name == "BaseChannel" and args:
                            super().__init__(args[0])  # Just the type
                        elif class_name == "LastValue" and args:
                            super().__init__(args[0])  # Just the type
                        else:
                            super().__init__()
                    except Exception:
                        # Last resort: create with no args
                        super().__init__()

        # Set the wrapper class name
        RustWrapper.__name__ = class_name

        # Replace the class in the module
        setattr(module, class_name, RustWrapper)

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
        "langgraph.pregel.main.Pregel",
        "langgraph.pregel.Pregel",
        "langgraph.channels.base.BaseChannel",
        "langgraph.channels.last_value.LastValue",
        "langgraph.channels.LastValue",
    ]

    status = {}
    for component in components:
        module_name, class_name = component.rsplit(".", 1)
        status[component] = is_patched(module_name, class_name)

    return status