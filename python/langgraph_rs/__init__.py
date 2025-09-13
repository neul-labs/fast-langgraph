"""LangGraph Rust Implementation

This package provides high-performance implementations of core LangGraph components
using Rust for significant performance improvements over the Python implementation.
"""

__version__ = "0.1.0"

# Import the Rust module
try:
    from .langgraph_rs import GraphExecutor
    _has_rust_backend = True
except ImportError:
    _has_rust_backend = False

# Fallback to Python implementation if Rust is not available
if _has_rust_backend:
    # Use the Rust implementation
    PregelExecutor = GraphExecutor
else:
    # Fallback to Python implementation (simplified)
    class PregelExecutor:
        def __init__(self):
            pass
            
        def execute_graph(self, input_data):
            # In a real implementation, this would delegate to the Python version
            return input_data
            
        def add_node(self, node_id, triggers, channels):
            # In a real implementation, this would add a node to the graph
            pass

__all__ = ["PregelExecutor"]