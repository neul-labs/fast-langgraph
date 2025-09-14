"""LangGraph Rust Implementation

This package provides high-performance implementations of core LangGraph components
using Rust for significant performance improvements over the Python implementation.
"""

__version__ = "0.1.0"

# Import the Rust modules
try:
    from .langgraph_rs import GraphExecutor, BaseChannel, LastValue, Checkpoint, Pregel
    # Try to import all Rust modules
    try:
        from .langgraph_rs import PregelExecutor, Channel, LastValueChannel
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
    
    class BaseChannel:
        def __init__(self, typ, key=""):
            self.typ = typ
            self.key = key
            
        @property
        def ValueType(self):
            return self.typ
            
        @property
        def UpdateType(self):
            return self.typ
            
        def copy(self):
            return BaseChannel(self.typ, self.key)
            
        def checkpoint(self):
            return None
            
        @classmethod
        def from_checkpoint(cls, checkpoint):
            return cls(None)
            
        def get(self):
            raise NotImplementedError
            
        def is_available(self):
            return False
            
        def update(self, values):
            raise NotImplementedError
            
        def consume(self):
            return False
            
        def finish(self):
            return False
    
    class LastValue(BaseChannel):
        def __init__(self, typ, key=""):
            super().__init__(typ, key)
            self.value = None
            
        def update(self, values):
            if len(values) == 0:
                return False
            if len(values) != 1:
                raise ValueError("LastValue channel can only receive one value per update")
            self.value = values[0]
            return True
            
        def get(self):
            if self.value is None:
                raise Exception("Channel is empty")
            return self.value
            
        def is_available(self):
            return self.value is not None
            
        def consume(self):
            return False
            
        def finish(self):
            return False
            
        def checkpoint(self):
            return self.value
            
        @classmethod
        def from_checkpoint(cls, checkpoint):
            instance = cls(None)
            instance.value = checkpoint
            return instance
            
        def copy(self):
            instance = LastValue(self.typ, self.key)
            instance.value = self.value
            return instance
    
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
    
    class Pregel:
        def __init__(self, nodes, channels=None, auto_validate=True, stream_mode="values",
                     stream_eager=False, output_channels=None, stream_channels=None,
                     interrupt_after_nodes=(), interrupt_before_nodes=(), input_channels=None,
                     step_timeout=None, debug=None, checkpointer=None, store=None, cache=None,
                     retry_policy=(), cache_policy=None, context_schema=None, config=None,
                     trigger_to_nodes=None, name="LangGraph"):
            self.nodes = nodes
            self.channels = channels or {}
            self.stream_mode = stream_mode
            self.output_channels = output_channels
            self.input_channels = input_channels
            self.checkpointer = checkpointer
            
        def invoke(self, input_data, config=None, context=None, stream_mode=None,
                   print_mode=None, output_keys=None, interrupt_before=None,
                   interrupt_after=None, durability=None):
            # In a real implementation, this would execute the graph
            return input_data
            
        def stream(self, input_data, config=None, context=None, stream_mode=None,
                   print_mode=None, output_keys=None, interrupt_before=None,
                   interrupt_after=None, durability=None, subgraphs=None, debug=None):
            # In a real implementation, this would stream the graph execution
            return []
            
        def ainvoke(self, *args, **kwargs):
            # In a real implementation, this would async execute the graph
            if args:
                return args[0]
            return None
            
        def astream(self, *args, **kwargs):
            # In a real implementation, this would async stream the graph execution
            return []

# Import shim module
from . import shim

__all__ = [
    "PregelExecutor", 
    "BaseChannel",
    "LastValue",
    "Channel", 
    "LastValueChannel", 
    "Checkpoint",
    "Pregel",
    "GraphExecutor",  # For backward compatibility
    "shim"  # For monkeypatching existing langgraph
]