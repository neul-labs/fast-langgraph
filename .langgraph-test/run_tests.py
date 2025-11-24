#!/usr/bin/env python3
"""Test runner with Fast LangGraph shim applied"""
import sys

print("=" * 60)
print("Applying Fast LangGraph shim...")
print("=" * 60)

try:
    import fast_langgraph

    if not fast_langgraph.is_rust_available():
        print("ERROR: Rust implementation not available!")
        sys.exit(1)

    print(f"✓ Fast LangGraph loaded")
    print(f"✓ Rust available: {fast_langgraph.is_rust_available()}")

    # Apply the patch
    success = fast_langgraph.shim.patch_langgraph()

    if success:
        print("✓ Successfully patched LangGraph")

        # Show what was patched
        status = fast_langgraph.shim.get_patch_status()
        patched = [k for k, v in status.items() if v]
        if patched:
            print(f"✓ Patched {len(patched)} components")
            for component in patched:
                print(f"  - {component}")
    else:
        print("⚠ Patching failed")

    print("=" * 60)

except Exception as e:
    print(f"ERROR: Failed to apply shim: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Run pytest
import pytest
sys.exit(pytest.main(sys.argv[1:]))
