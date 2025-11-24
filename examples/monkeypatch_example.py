"""
Example demonstrating how to use the LangGraph Rust shim to monkeypatch existing langgraph code
"""

# Example 1: Manual patching
print("=== Example 1: Manual Patching ===")

try:
    import fast_langgraph
    
    # Patch the existing langgraph with Rust implementations
    success = fast_langgraph.shim.patch_langgraph()
    
    if success:
        print("✓ Successfully patched langgraph with Rust implementations")
        
        # Now we can use the existing langgraph code without changes
        # but it will use the high-performance Rust backend
        import langgraph.pregel
        
        # This will actually use the Rust implementation
        app = langgraph.pregel.Pregel()
        print("✓ Created Pregel app using Rust implementation")
        
        # Unpatch to restore original implementation
        fast_langgraph.shim.unpatch_langgraph()
        print("✓ Restored original langgraph implementation")
    else:
        print("✗ Failed to patch langgraph")
        
except ImportError:
    print("langgraph not found, skipping manual patching example")

print()

# Example 2: Auto patching with environment variable
print("=== Example 2: Auto Patching ===")
print("To automatically patch langgraph on import, set the environment variable:")
print("  export FAST_LANGGRAPH_AUTO_PATCH=1")
print("  python your_langgraph_app.py")
print()

# Example 3: Direct usage (no patching)
print("=== Example 3: Direct Usage ===")

try:
    # Use the Rust implementations directly
    from fast_langgraph import PregelExecutor, LastValueChannel, Checkpoint
    
    # Create instances using Rust implementations
    executor = PregelExecutor()
    channel = LastValueChannel()
    checkpoint = Checkpoint()
    
    print("✓ Created instances using Rust implementations directly")
    
    # Execute a simple graph
    result = executor.execute_graph({"input": "test"})
    print(f"✓ Execution result: {result}")
    
except ImportError as e:
    print(f"✗ Failed to import fast_langgraph: {e}")

print()
print("=== Summary ===")
print("The fast-langgraph package provides three ways to use the Rust implementations:")
print("1. Manual patching: Use fast_langgraph.shim.patch_langgraph() to replace existing classes")
print("2. Auto patching: Set FAST_LANGGRAPH_AUTO_PATCH=1 environment variable")
print("3. Direct usage: Import classes directly from fast_langgraph")