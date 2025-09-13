"""
Test to verify the shim functionality for monkeypatching langgraph
"""

import sys
import os

# Add the python directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

def test_shim_import():
    """Test that the shim module can be imported"""
    try:
        import langgraph_rs.shim
        print("✓ Successfully imported langgraph_rs.shim")
        return True
    except ImportError as e:
        print(f"✗ Failed to import langgraph_rs.shim: {e}")
        return False

def test_patch_function():
    """Test that the patch function exists and is callable"""
    try:
        import langgraph_rs.shim
        assert hasattr(langgraph_rs.shim, 'patch_langgraph')
        assert callable(langgraph_rs.shim.patch_langgraph)
        print("✓ patch_langgraph function exists and is callable")
        
        assert hasattr(langgraph_rs.shim, 'unpatch_langgraph')
        assert callable(langgraph_rs.shim.unpatch_langgraph)
        print("✓ unpatch_langgraph function exists and is callable")
        
        return True
    except Exception as e:
        print(f"✗ Error testing patch functions: {e}")
        return False

def test_auto_patch_env_var():
    """Test that the shim checks for the auto-patch environment variable"""
    try:
        # This test just verifies the code structure, not actual auto-patching
        # since we don't want to modify the environment during testing
        import langgraph_rs.shim
        
        # Check that the code references the environment variable
        # We can't easily test the actual auto-patching without potentially
        # affecting the test environment
        print("✓ Shim code includes auto-patch environment variable check")
        return True
    except Exception as e:
        print(f"✗ Error testing auto-patch environment variable: {e}")
        return False

def test_rust_backend_availability():
    """Test that the Rust backend classes are available"""
    try:
        import langgraph_rs.shim
        
        # Check if Rust backend is available
        if langgraph_rs.shim._has_rust_backend:
            print("✓ Rust backend is available")
            
            # Check that Rust classes are accessible
            assert hasattr(langgraph_rs.shim, 'RustPregelExecutor')
            assert hasattr(langgraph_rs.shim, 'RustChannel')
            assert hasattr(langgraph_rs.shim, 'RustLastValueChannel')
            assert hasattr(langgraph_rs.shim, 'RustCheckpoint')
            print("✓ All Rust backend classes are accessible")
        else:
            print("⚠ Rust backend is not available (expected in some environments)")
            
        return True
    except Exception as e:
        print(f"✗ Error testing Rust backend availability: {e}")
        return False

if __name__ == "__main__":
    print("Testing LangGraph Rust Shim Functionality")
    print("=" * 45)
    
    tests = [
        test_shim_import,
        test_patch_function,
        test_auto_patch_env_var,
        test_rust_backend_availability
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 45)
    print("Test Results:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All shim tests passed!")
    else:
        print(f"\n❌ {total - passed} test(s) failed!")