"""
Shim module for automatic LangGraph acceleration.

This module provides automatic patching of LangGraph with high-performance
Rust implementations. When enabled, it transparently accelerates:

**Automatic (via shim):**
- Thread pool executor caching (2.3x speedup) - eliminates 20ms overhead per invocation
- apply_writes acceleration (1.2x speedup) - Rust-based channel updates

**Manual (requires explicit usage):**
- RustSQLiteCheckpointer - drop-in replacement for checkpointing (5-6x faster)
- RustLLMCache / @cached decorator - LLM response caching
- langgraph_state_update - optimized state merging

Usage:
    # Option 1: Environment variable (recommended for production)
    export FAST_LANGGRAPH_AUTO_PATCH=1
    python your_app.py

    # Option 2: Explicit patching
    import fast_langgraph
    fast_langgraph.shim.patch_langgraph()

    # Option 3: All optimizations including manual components
    from fast_langgraph.optimizations import enable_all_optimizations
    enable_all_optimizations()
"""

import importlib
import sys
import warnings
from typing import Any, Callable, Dict

# Track what we've patched
_patched_functions: Dict[str, Any] = {}
_original_functions: Dict[str, Any] = {}
_executor_cache_patched: bool = False


def patch_langgraph(verbose: bool = True) -> bool:
    """
    Patch LangGraph with all available automatic accelerations.

    This function enables transparent performance improvements by patching:

    1. **Thread Pool Executor Caching** (2.3x speedup)
       - Patches langchain_core.runnables.config.get_executor_for_config
       - Eliminates ~20ms overhead per graph invocation
       - Reuses ThreadPoolExecutor instances across calls

    2. **apply_writes Acceleration** (1.2x speedup)
       - Patches langgraph.pregel._algo.apply_writes
       - Uses Rust FastChannelUpdater for batch channel updates

    Args:
        verbose: If True, print status messages (default: True)

    Returns:
        bool: True if at least one patch was applied, False otherwise.

    Note:
        For additional optimizations requiring explicit usage, see:
        - RustSQLiteCheckpointer for fast checkpointing
        - @cached decorator for LLM response caching
        - langgraph_state_update for state merging
    """
    global _executor_cache_patched

    patches_applied = []
    patches_failed = []

    # 1. Patch executor caching (biggest win - 2.3x speedup)
    if not _executor_cache_patched:
        try:
            from .executor_cache import patch_langchain_executor

            if patch_langchain_executor():
                _executor_cache_patched = True
                patches_applied.append("executor_cache (2.3x speedup)")
        except ImportError:
            patches_failed.append("executor_cache (langchain_core not available)")
        except Exception as e:
            patches_failed.append(f"executor_cache ({e})")

    # 2. Patch apply_writes with Rust acceleration
    try:
        from .algo_shims import create_accelerated_apply_writes

        if _patch_function(
            "langgraph.pregel._algo", "apply_writes", create_accelerated_apply_writes
        ):
            patches_applied.append("apply_writes (1.2x speedup)")
    except ImportError as e:
        patches_failed.append(f"apply_writes ({e})")
    except Exception as e:
        patches_failed.append(f"apply_writes ({e})")

    # Print summary
    if verbose:
        if patches_applied:
            print("✓ Fast LangGraph automatic acceleration enabled:")
            for patch in patches_applied:
                print(f"  • {patch}")
            print()
            print("  For additional speedups, use these manually:")
            print("  • RustSQLiteCheckpointer - 5-6x faster checkpointing")
            print("  • @cached decorator - LLM response caching")
        else:
            print("✓ Fast LangGraph loaded (no automatic patches applied)")

        if patches_failed and verbose:
            print()
            print("  ⚠ Some patches could not be applied:")
            for failure in patches_failed:
                print(f"    - {failure}")

    return len(patches_applied) > 0


def unpatch_langgraph(verbose: bool = True) -> bool:
    """
    Restore the original LangGraph implementations.

    Note:
        Executor cache patching cannot be fully reversed without a restart.
        The cached executors will continue to be reused until the process ends.

    Args:
        verbose: If True, print status messages (default: True)

    Returns:
        bool: True if unpatching was successful, False otherwise.
    """
    global _executor_cache_patched

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

        if verbose:
            if unpatched:
                print(f"✓ Successfully unpatched: {', '.join(unpatched)}")
            else:
                print("✓ No function patches to remove")

            if _executor_cache_patched:
                print("  ⚠ Note: Executor cache requires restart to fully disable")

        return True

    except Exception as e:
        if verbose:
            print(f"✗ Error during unpatching: {e}")
        return False


def _patch_function(
    module_name: str, func_name: str, accelerator_factory: Callable[[Any], Any]
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


def get_patch_status() -> Dict[str, Any]:
    """
    Get the current patch status for all LangGraph acceleration components.

    Returns:
        Dict with detailed status of each acceleration component:
        {
            'automatic': {
                'executor_cache': bool,
                'apply_writes': bool,
            },
            'manual': {
                'rust_checkpointer': bool,  # Available for manual use
                'rust_cache': bool,         # Available for manual use
            },
            'summary': str  # Human-readable summary
        }
    """
    # Check automatic patches
    automatic = {
        "executor_cache": _executor_cache_patched,
        "apply_writes": is_func_patched("langgraph.pregel._algo", "apply_writes"),
    }

    # Check manual component availability
    manual = {"rust_checkpointer": False, "rust_cache": False}

    try:
        from . import RustSQLiteCheckpointer  # noqa: F401

        manual["rust_checkpointer"] = True
    except ImportError:
        pass

    try:
        from . import RustLLMCache  # noqa: F401

        manual["rust_cache"] = True
    except ImportError:
        pass

    # Generate summary
    auto_count = sum(automatic.values())
    manual_count = sum(manual.values())

    if auto_count == 0:
        summary = "No automatic acceleration enabled. Call patch_langgraph() to enable."
    elif auto_count == len(automatic):
        summary = f"All automatic acceleration enabled ({auto_count} patches)"
    else:
        summary = (
            f"Partial acceleration: {auto_count}/{len(automatic)} automatic patches"
        )

    if manual_count > 0:
        summary += f", {manual_count} manual components available"

    return {"automatic": automatic, "manual": manual, "summary": summary}


def is_patched() -> bool:
    """
    Check if any LangGraph acceleration is currently active.

    Returns:
        bool: True if at least one acceleration is active, False otherwise.
    """
    return len(_original_functions) > 0 or _executor_cache_patched


def print_status() -> None:
    """
    Print a human-readable status of all acceleration components.
    """
    status = get_patch_status()

    print("Fast LangGraph Acceleration Status")
    print("=" * 40)
    print()
    print("Automatic (transparent patching):")
    for name, enabled in status["automatic"].items():
        icon = "✓" if enabled else "✗"
        print(f"  {icon} {name}")

    print()
    print("Manual (explicit usage required):")
    for name, available in status["manual"].items():
        icon = "✓" if available else "✗"
        status_text = "available" if available else "not available"
        print(f"  {icon} {name}: {status_text}")

    print()
    print(f"Summary: {status['summary']}")
