"""
Shim module for LangGraph Rust Implementation
This module provides compatibility shims that can monkeypatch the existing langgraph classes
"""

import sys
import importlib
import os
from typing import Any, Optional

# Import the Rust modules
try:
    from .langgraph_rs import GraphExecutor as RustPregelExecutor
    from .langgraph_rs import Channel as RustChannel
    from .langgraph_rs import LastValueChannel as RustLastValueChannel
    from .langgraph_rs import Checkpoint as RustCheckpoint
    _has_rust_backend = True
except ImportError:
    _has_rust_backend = False


def patch_langgraph() -> bool:
    """
    Monkeypatch the existing langgraph classes with Rust implementations.
    
    This function will attempt to import langgraph and replace its classes
    with the high-performance Rust implementations.
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not _has_rust_backend:
        print("Rust backend not available, cannot patch langgraph")
        return False
    
    try:
        # Try to import the existing langgraph modules
        import langgraph
        import langgraph.pregel
        import langgraph.channels
        import langgraph.checkpoint
        
        # Patch the Pregel executor
        if hasattr(langgraph.pregel, 'Pregel'):
            # Store reference to original class
            langgraph.pregel.Pregel._original_class = langgraph.pregel.Pregel
            # Replace with Rust implementation
            langgraph.pregel.Pregel = RustPregelExecutor
            print("✓ Successfully patched langgraph.pregel.Pregel with Rust implementation")
        
        # Patch channel classes
        if hasattr(langgraph.channels, 'BaseChannel'):
            langgraph.channels.BaseChannel._original_class = langgraph.channels.BaseChannel
            langgraph.channels.BaseChannel = RustChannel
            print("✓ Successfully patched langgraph.channels.BaseChannel with Rust implementation")
            
        if hasattr(langgraph.channels, 'LastValue'):
            langgraph.channels.LastValue._original_class = langgraph.channels.LastValue
            langgraph.channels.LastValue = RustLastValueChannel
            print("✓ Successfully patched langgraph.channels.LastValue with Rust implementation")
        
        # Patch checkpoint classes
        if hasattr(langgraph.checkpoint, 'Checkpoint'):
            langgraph.checkpoint.Checkpoint._original_class = langgraph.checkpoint.Checkpoint
            langgraph.checkpoint.Checkpoint = RustCheckpoint
            print("✓ Successfully patched langgraph.checkpoint.Checkpoint with Rust implementation")
        
        print("✓ LangGraph successfully patched with Rust implementations")
        return True
        
    except ImportError:
        print("❌ langgraph not found, cannot patch")
        return False
    except Exception as e:
        print(f"❌ Error patching langgraph: {e}")
        return False


def unpatch_langgraph() -> bool:
    """
    Restore the original langgraph classes.
    
    This function will restore the original langgraph classes if they were patched.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import langgraph
        import langgraph.pregel
        import langgraph.channels
        import langgraph.checkpoint
        
        # Restore Pregel executor
        if hasattr(langgraph.pregel.Pregel, '_original_class'):
            langgraph.pregel.Pregel = langgraph.pregel.Pregel._original_class
            print("✓ Successfully restored original langgraph.pregel.Pregel")
        
        # Restore channel classes
        if hasattr(langgraph.channels.BaseChannel, '_original_class'):
            langgraph.channels.BaseChannel = langgraph.channels.BaseChannel._original_class
            print("✓ Successfully restored original langgraph.channels.BaseChannel")
            
        if hasattr(langgraph.channels.LastValue, '_original_class'):
            langgraph.channels.LastValue = langgraph.channels.LastValue._original_class
            print("✓ Successfully restored original langgraph.channels.LastValue")
        
        # Restore checkpoint classes
        if hasattr(langgraph.checkpoint.Checkpoint, '_original_class'):
            langgraph.checkpoint.Checkpoint = langgraph.checkpoint.Checkpoint._original_class
            print("✓ Successfully restored original langgraph.checkpoint.Checkpoint")
        
        print("✓ LangGraph successfully restored to original implementation")
        return True
        
    except ImportError:
        print("❌ langgraph not found, cannot unpatch")
        return False
    except Exception as e:
        print(f"❌ Error unpatching langgraph: {e}")
        return False


# Auto-patch on import if environment variable is set
if 'LANGGRAPH_RS_AUTO_PATCH' in os.environ:
    patch_langgraph()


__all__ = [
    "patch_langgraph",
    "unpatch_langgraph",
    "RustPregelExecutor",
    "RustChannel",
    "RustLastValueChannel",
    "RustCheckpoint"
]