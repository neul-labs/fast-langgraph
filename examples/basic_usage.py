"""
Example usage of LangGraph Rust implementation
"""

try:
    from fast_langgraph import PregelExecutor, LastValueChannel, Checkpoint
    
    print("Successfully imported LangGraph Rust implementation")
    
    # Create a new executor
    executor = PregelExecutor()
    
    # Create a simple input
    input_data = {"value": 42}
    
    # Execute the graph (this would be more complex in a real implementation)
    result = executor.execute_graph(input_data)
    
    print(f"Input: {input_data}")
    print(f"Output: {result}")
    
    # Demonstrate other components
    channel = LastValueChannel()
    channel.update(["test_value"])
    value = channel.get()
    print(f"Channel value: {value}")
    
    checkpoint = Checkpoint()
    checkpoint.channel_values["test"] = "test_value"
    json_str = checkpoint.to_json()
    print(f"Checkpoint JSON: {json_str}")
    
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