"""
Fast LangGraph - High-performance Rust implementation with Python bindings.

This module provides high-performance Rust implementations of core LangGraph components
that can be used as drop-in replacements for the original Python implementations.
"""

import os
import sys
from typing import Any, Optional

# Try to import the Rust extension module
try:
    from . import fast_langgraph  # type: ignore
    _rust_available = True
except ImportError:
    _rust_available = False
    fast_langgraph = None

# Re-export main classes for direct usage
if _rust_available:
    from .fast_langgraph import (
        BaseChannel,
        LastValue,
        Checkpoint,
        Pregel,
        GraphExecutor,
        # Hybrid acceleration classes
        ChannelManager,
        TaskScheduler,
        PregelAccelerator,
    )

    # Legacy alias
    PregelExecutor = GraphExecutor
    LastValueChannel = LastValue
else:
    # Fallback stubs if Rust extension is not available
    class BaseChannel:
        def __init__(self, *args, **kwargs):
            raise ImportError("Rust extension not available")

    class LastValue:
        def __init__(self, *args, **kwargs):
            raise ImportError("Rust extension not available")

    class Checkpoint:
        def __init__(self, *args, **kwargs):
            raise ImportError("Rust extension not available")

    class Pregel:
        def __init__(self, *args, **kwargs):
            raise ImportError("Rust extension not available")

    class GraphExecutor:
        def __init__(self, *args, **kwargs):
            raise ImportError("Rust extension not available")

    PregelExecutor = GraphExecutor
    LastValueChannel = LastValue

# Import shim module
from . import shim

# Import accelerator module
from . import accelerator
from .accelerator import (
    AcceleratedPregelLoop,
    is_accelerator_available,
    accelerate_apply_writes,
    accelerate_triggers,
    patch_algo,
    unpatch_algo,
)

__all__ = [
    "BaseChannel",
    "LastValue",
    "LastValueChannel",
    "Checkpoint",
    "Pregel",
    "GraphExecutor",
    "PregelExecutor",
    # Hybrid acceleration
    "ChannelManager",
    "TaskScheduler",
    "PregelAccelerator",
    "shim",
    "is_rust_available",
    # Accelerator module
    "accelerator",
    "AcceleratedPregelLoop",
    "is_accelerator_available",
    "accelerate_apply_writes",
    "accelerate_triggers",
    "patch_algo",
    "unpatch_algo",
]

def is_rust_available() -> bool:
    """Check if the Rust extension is available."""
    return _rust_available

# Auto-patch if environment variable is set (support both old and new env var names)
if os.environ.get("FAST_LANGGRAPH_AUTO_PATCH") == "1" or os.environ.get("LANGGRAPH_RS_AUTO_PATCH") == "1":
    try:
        shim.patch_langgraph()
    except Exception as e:
        import warnings
        warnings.warn(f"Failed to auto-patch langgraph: {e}", RuntimeWarning)