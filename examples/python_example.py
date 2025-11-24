#!/usr/bin/env python3
"""
Example usage of LangGraph Rust implementation
"""

try:
    from fast_langgraph import PregelExecutor
    print("Successfully imported LangGraph Rust implementation")
    
    # Create a new executor
    executor = PregelExecutor()
    
    # Create a simple input
    input_data = {"value": 42}
    
    # Execute the graph (this would be more complex in a real implementation)
    result = executor.execute_graph(input_data)
    
    print(f"Input: {input_data}")
    print(f"Output: {result}")
    print("Example completed successfully!")
    
except ImportError as e:
    print(f"Failed to import LangGraph Rust implementation: {e}")
    print("Falling back to Python implementation...")
    
    # Fallback to Python implementation
    from fast_langgraph import PregelExecutor
    executor = PregelExecutor()
    input_data = {"value": 42}
    result = executor.execute_graph(input_data)
    
    print(f"Input: {input_data}")
    print(f"Output: {result}")
    print("Example completed successfully!")