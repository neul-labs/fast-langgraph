#!/usr/bin/env python3
"""
Performance comparison script for Fast LangGraph shimming.

Runs LangGraph tests twice:
1. Baseline (no shimming) - pure Python
2. Accelerated (with shimming) - Rust-accelerated components

Compares:
- Pass/fail/error counts (should be identical)
- Execution time (accelerated should be faster)
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Paths
FAST_LANGGRAPH_ROOT = Path(__file__).parent.parent
LANGGRAPH_ROOT = FAST_LANGGRAPH_ROOT / ".langgraph-test" / "langgraph"
VENV_PYTHON = FAST_LANGGRAPH_ROOT / ".langgraph-test" / "venv" / "bin" / "python"

def run_tests_with_shim(enable_shim: bool = False) -> Dict[str, Any]:
    """
    Run LangGraph tests with or without shimming.

    Args:
        enable_shim: If True, enable Fast LangGraph shimming

    Returns:
        Dict with test results: passed, failed, errors, duration
    """
    test_type = "ACCELERATED (Rust shim)" if enable_shim else "BASELINE (Pure Python)"
    print(f"\n{'='*70}")
    print(f"Running {test_type}")
    print(f"{'='*70}\n")

    # Create test runner script
    test_script = f"""
import sys
import time
import pytest

# Add fast_langgraph to path if shimming enabled
{'sys.path.insert(0, "/home/dipankar/Code/fast-langraph")' if enable_shim else ''}

# Apply shim if enabled
{'import fast_langgraph.shim as shim' if enable_shim else ''}
{'print("Applying Fast LangGraph shim...")' if enable_shim else ''}
{'shim.patch_langgraph()' if enable_shim else ''}
{'print()' if enable_shim else ''}

# Run pytest and capture results
start_time = time.time()

# Run pytest programmatically
exit_code = pytest.main([
    '-v',
    '--tb=short',
    '--color=yes',
    '-x',  # Stop on first failure for faster iteration
    'tests/',
])

duration = time.time() - start_time

# Print summary
print()
print(f"Duration: {{duration:.2f}}s")
print(f"Exit code: {{exit_code}}")

sys.exit(exit_code)
"""

    # Run the test script
    start_time = time.time()

    try:
        result = subprocess.run(
            [str(VENV_PYTHON), "-c", test_script],
            cwd=str(LANGGRAPH_ROOT),
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        duration = time.time() - start_time

        # Parse output for test results
        output = result.stdout + result.stderr

        # Extract test counts from pytest output
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        errors = output.count(" ERROR")
        skipped = output.count(" SKIPPED")

        # Try to find the pytest summary line
        summary_markers = ["passed", "failed", "error"]
        test_summary = None
        for line in output.split('\n'):
            if any(marker in line.lower() for marker in summary_markers):
                if '==' in line:
                    test_summary = line.strip()
                    break

        results = {
            "test_type": test_type,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "duration": duration,
            "exit_code": result.returncode,
            "summary": test_summary,
        }

        # Print output
        print(output)

        return results

    except subprocess.TimeoutExpired:
        print("ERROR: Tests timed out after 300 seconds")
        return {
            "test_type": test_type,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "skipped": 0,
            "duration": 300.0,
            "exit_code": -1,
            "summary": "TIMEOUT",
        }
    except Exception as e:
        print(f"ERROR: Failed to run tests: {e}")
        import traceback
        traceback.print_exc()
        return {
            "test_type": test_type,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "skipped": 0,
            "duration": 0.0,
            "exit_code": -1,
            "summary": str(e),
        }

def compare_results(baseline: Dict[str, Any], accelerated: Dict[str, Any]) -> None:
    """
    Compare baseline vs accelerated results and print summary.

    Args:
        baseline: Results from baseline run
        accelerated: Results from accelerated run
    """
    print(f"\n{'='*70}")
    print("COMPARISON SUMMARY")
    print(f"{'='*70}\n")

    # Test counts comparison
    print("Test Counts:")
    print(f"  {'Metric':<15} {'Baseline':<12} {'Accelerated':<12} {'Match':<10}")
    print(f"  {'-'*15} {'-'*12} {'-'*12} {'-'*10}")

    for metric in ['passed', 'failed', 'errors', 'skipped']:
        b_val = baseline[metric]
        a_val = accelerated[metric]
        match = "✓ PASS" if b_val == a_val else "✗ FAIL"
        print(f"  {metric.capitalize():<15} {b_val:<12} {a_val:<12} {match:<10}")

    # Performance comparison
    print("\nPerformance:")
    b_duration = baseline['duration']
    a_duration = accelerated['duration']
    speedup = b_duration / a_duration if a_duration > 0 else 0
    improvement = ((b_duration - a_duration) / b_duration * 100) if b_duration > 0 else 0

    print(f"  Baseline duration:     {b_duration:.2f}s")
    print(f"  Accelerated duration:  {a_duration:.2f}s")
    print(f"  Speedup:              {speedup:.2f}x")
    print(f"  Improvement:          {improvement:.1f}%")

    # Overall verdict
    print("\nVerdict:")
    counts_match = all(
        baseline[m] == accelerated[m]
        for m in ['passed', 'failed', 'errors']
    )
    is_faster = a_duration < b_duration

    if counts_match and is_faster:
        print("  ✓ SUCCESS: Shim maintains compatibility and improves performance!")
    elif counts_match:
        print("  ⚠ PARTIAL: Shim maintains compatibility but no performance gain")
    else:
        print("  ✗ FAILURE: Shim changes test results - compatibility broken!")

    # Save results
    results_file = FAST_LANGGRAPH_ROOT / "scripts" / "comparison_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            'baseline': baseline,
            'accelerated': accelerated,
            'speedup': speedup,
            'improvement_percent': improvement,
            'compatible': counts_match,
        }, f, indent=2)

    print(f"\nResults saved to: {results_file}")

def main():
    """Run baseline and accelerated tests, then compare results."""
    print("Fast LangGraph Performance Comparison")
    print("=" * 70)

    # Check that LangGraph is available
    if not LANGGRAPH_ROOT.exists():
        print(f"ERROR: LangGraph not found at {LANGGRAPH_ROOT}")
        print("Please run: cd /home/dipankar/Code/fast-langraph && git clone https://github.com/langchain-ai/langgraph .langgraph-test/langgraph")
        sys.exit(1)

    if not VENV_PYTHON.exists():
        print(f"ERROR: Python venv not found at {VENV_PYTHON}")
        sys.exit(1)

    # Run baseline tests (no shim)
    baseline_results = run_tests_with_shim(enable_shim=False)

    # Run accelerated tests (with shim)
    accelerated_results = run_tests_with_shim(enable_shim=True)

    # Compare results
    compare_results(baseline_results, accelerated_results)

if __name__ == "__main__":
    main()
