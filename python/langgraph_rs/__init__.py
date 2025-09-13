"""LangGraph Rust Implementation

This package provides high-performance implementations of core LangGraph components
using Rust for significant performance improvements over the Python implementation.
"""

__version__ = "0.1.0"

# Import the Rust modules
try:
    from .langgraph_rs import GraphExecutor
    # Try to import all Rust modules
    try:
        from .langgraph_rs import PregelExecutor, Channel, LastValueChannel, Checkpoint
        _has_rust_backend = True
    except ImportError:
        _has_rust_backend = False
except ImportError:
    _has_rust_backend = False

# Fallback to Python implementation if Rust is not available
if _has_rust_backend:
    # Use the Rust implementations
    pass  # All classes are already imported from Rust
else:
    # Fallback to Python implementations (simplified)
    class PregelExecutor:
        def __init__(self):
            pass
            
        def execute_graph(self, input_data):
            # In a real implementation, this would delegate to the Python version
            return input_data
            
        def add_node(self, node_id, triggers, channels):
            # In a real implementation, this would add a node to the graph
            pass
    
    class Channel:
        def __init__(self):
            pass
            
        def update(self, values):
            pass
            
        def get(self):
            pass
            
        def is_available(self):
            return False
    
    class LastValueChannel(Channel):
        def __init__(self):
            super().__init__()
            
        def update(self, values):
            pass
            
        def get(self):
            return None
            
        def is_available(self):
            return False
    
    class Checkpoint:
        def __init__(self):
            self.channel_values = {}
            self.channel_versions = {}
            self.versions_seen = {}
            
        def to_json(self):
            return "{}"
            
        def from_json(self, json_str):
            return Checkpoint()

# Import shim module
from . import shim

__all__ = [
    "PregelExecutor", 
    "Channel", 
    "LastValueChannel", 
    "Checkpoint",
    "GraphExecutor",  # For backward compatibility
    "shim"  # For monkeypatching existing langgraph
]