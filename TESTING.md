# Testing Fast LangGraph

This document describes the testing strategy and how to run various test suites.

## Table of Contents

- [Overview](#overview)
- [Test Types](#test-types)
- [Running Tests](#running-tests)
- [Compatibility Testing](#compatibility-testing)
- [Continuous Integration](#continuous-integration)
- [Writing Tests](#writing-tests)

## Overview

Fast LangGraph uses a comprehensive testing strategy to ensure:

1. **Correctness**: Rust implementations work as expected
2. **Compatibility**: Drop-in replacement for Python LangGraph
3. **Performance**: Improvements are measurable and consistent
4. **Regression**: Changes don't break existing functionality

## Test Types

### 1. Rust Unit Tests

Tests for core Rust functionality.

**Location**: `src/**/*.rs` (inline tests) and `tests/`

**Run with**:
```bash
# All tests
cargo test

# Specific test
cargo test test_name

# With output
cargo test -- --nocapture

# Without Python bindings
cargo test --no-default-features
```

### 2. Python Unit Tests

Tests for Python bindings and integration.

**Location**: `tests/test_*.py`

**Run with**:
```bash
# All Python tests
poetry run pytest tests/

# Specific test file
poetry run pytest tests/test_channels.py

# With coverage
poetry run pytest --cov=fast_langgraph tests/

# Verbose
poetry run pytest -v tests/

# Stop on first failure
poetry run pytest -x tests/
```

### 3. Integration Tests

Tests that verify Fast LangGraph works with actual LangGraph applications.

**Location**: `tests/test_integration*.py`

**Run with**:
```bash
# Requires langgraph to be installed
poetry install --with integration

# Run integration tests
poetry run pytest -m integration tests/
```

### 4. Compatibility Tests

**Most Important**: Tests that verify Fast LangGraph is a drop-in replacement by running LangGraph's own test suite with our shim applied.

**Location**: `scripts/test_compatibility.py`

**Run with**:
```bash
# Basic compatibility test
python scripts/test_compatibility.py

# Verbose output
python scripts/test_compatibility.py -v

# Keep test directory for inspection
python scripts/test_compatibility.py --keep

# Test against specific LangGraph branch
python scripts/test_compatibility.py --branch v0.2.0

# Pass pytest options
python scripts/test_compatibility.py -- -k test_channels -v

# Bash version (Linux/Mac)
./scripts/test_langgraph_compatibility.sh
```

### 5. Benchmark Tests

Performance comparison tests.

**Location**: `benches/`

**Run with**:
```bash
# Run all benchmarks
cargo bench

# Specific benchmark
cargo bench --bench langgraph_benchmark

# Save baseline
cargo bench -- --save-baseline main

# Compare against baseline
cargo bench -- --baseline main
```

## Running Tests

### Quick Start

```bash
# 1. Install dependencies
poetry install --with dev,test,integration,build

# 2. Build Fast LangGraph
poetry run maturin develop

# 3. Run all tests
cargo test && poetry run pytest

# 4. Run compatibility tests
python scripts/test_compatibility.py
```

### Test Matrix

| Command | What it tests | Duration |
|---------|---------------|----------|
| `cargo test` | Rust core functionality | ~10s |
| `poetry run pytest` | Python bindings | ~30s |
| `cargo bench` | Performance benchmarks | ~2min |
| `python scripts/test_compatibility.py` | LangGraph compatibility | ~5-10min |

### Pre-commit Testing

Before committing changes:

```bash
# Format code
cargo fmt
poetry run black .

# Lint
cargo clippy -- -D warnings
poetry run ruff check .

# Type check
poetry run mypy fast_langgraph/

# Run tests
cargo test
poetry run pytest
```

## Compatibility Testing

### How It Works

The compatibility test suite:

1. **Clones LangGraph** from the official repository
2. **Installs LangGraph** with all dependencies
3. **Builds Fast LangGraph** in the same environment
4. **Applies the shim** to replace Python classes with Rust
5. **Runs LangGraph's tests** to verify everything still works

This ensures Fast LangGraph is truly a drop-in replacement.

### Running Compatibility Tests

#### Basic Usage

```bash
# Default: Test against main branch
python scripts/test_compatibility.py

# Output:
# [*] Setting up test environment...
# [*] Cloning LangGraph (branch: main)...
# [*] Creating virtual environment...
# [*] Installing LangGraph and dependencies...
# [*] Building and installing Fast LangGraph...
# [*] Running LangGraph tests with Fast LangGraph shim...
# =========================================
# Applying Fast LangGraph shim...
# ✓ Successfully patched LangGraph
# ✓ Patched 5 components
# =========================================
# [✓] All tests passed! ✨
```

#### Advanced Options

```bash
# Test against specific branch
python scripts/test_compatibility.py --branch v0.2.0

# Keep test directory for debugging
python scripts/test_compatibility.py --keep
# Test dir will be at: .langgraph-test/

# Verbose output
python scripts/test_compatibility.py -v

# Run specific tests only
python scripts/test_compatibility.py -- -k test_channels

# Run with pytest options
python scripts/test_compatibility.py -- -v -x --tb=short
```

#### Custom LangGraph Repository

```bash
# Test against a fork
python scripts/test_compatibility.py \
  --repo https://github.com/your-username/langgraph.git \
  --branch your-feature-branch
```

### Interpreting Results

**Success**:
```
[✓] All tests passed! ✨
╔══════════════════════════════════════════════════════════╗
║  Fast LangGraph is fully compatible with LangGraph! 🎉  ║
╚══════════════════════════════════════════════════════════╝
```

**Failure**:
```
[✗] Some tests failed

This may indicate:
  1. Compatibility issues with LangGraph API changes
  2. Missing or incorrect implementation
  3. Edge case handling differences

Check the test output for details.
```

### Debugging Failed Tests

If compatibility tests fail:

1. **Keep the test directory**:
   ```bash
   python scripts/test_compatibility.py --keep
   ```

2. **Inspect the environment**:
   ```bash
   cd .langgraph-test
   source venv/bin/activate
   cd langgraph
   ```

3. **Run specific failing test**:
   ```bash
   python ../run_tests.py tests/test_specific.py::test_function -v
   ```

4. **Compare with unpatched**:
   ```bash
   # Disable shim and run same test
   FAST_LANGGRAPH_AUTO_PATCH=0 python -m pytest tests/test_specific.py
   ```

5. **Check what was patched**:
   ```python
   import fast_langgraph
   status = fast_langgraph.shim.get_patch_status()
   print(status)
   ```

## Continuous Integration

### GitHub Actions

Fast LangGraph uses GitHub Actions for automated testing:

#### Workflows

1. **`rust-tests.yml`**: Runs Rust tests on push/PR
   - Tests on Linux, macOS, Windows
   - Tests with stable and beta Rust
   - Checks formatting and linting
   - Generates code coverage

2. **`compatibility-tests.yml`**: Runs compatibility tests
   - Tests against LangGraph main branch
   - Tests on multiple OS and Python versions
   - Runs daily to catch breaking changes
   - Creates issues on failure

#### Manual Triggers

You can manually trigger compatibility tests:

1. Go to **Actions** → **LangGraph Compatibility Tests**
2. Click **Run workflow**
3. Choose branch to test against (default: main)
4. Click **Run workflow**

### Local CI Simulation

Simulate CI environment locally:

```bash
# Install act (GitHub Actions local runner)
# https://github.com/nektos/act

# Run compatibility test workflow
act -j compatibility-test

# Run Rust test workflow
act -j test
```

## Writing Tests

### Rust Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_channel_update() {
        let mut channel = LastValueChannel::new(String::from("test"));
        channel.update(vec!["value".to_string()]);
        assert_eq!(channel.get(), Some("value".to_string()));
    }

    #[tokio::test]
    async fn test_async_operation() {
        // Async test
    }
}
```

### Python Tests

```python
import pytest
import fast_langgraph

def test_channel_creation():
    """Test creating a channel"""
    channel = fast_langgraph.LastValue(str, "test_channel")
    assert channel is not None

def test_channel_update():
    """Test updating a channel"""
    channel = fast_langgraph.LastValue(str, "test")
    channel.update(["value"])
    assert channel.get() == "value"

@pytest.mark.integration
def test_with_langgraph():
    """Integration test requiring langgraph"""
    # This test only runs with: pytest -m integration
    pass
```

### Benchmark Tests

```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn benchmark_channel_update(c: &mut Criterion) {
    c.bench_function("channel_update", |b| {
        let mut channel = LastValueChannel::new(0);
        b.iter(|| {
            channel.update(vec![black_box(42)]);
        });
    });
}

criterion_group!(benches, benchmark_channel_update);
criterion_main!(benches);
```

## Test Coverage

### Generate Coverage Report

```bash
# Python coverage
poetry run pytest --cov=fast_langgraph --cov-report=html tests/
open htmlcov/index.html

# Rust coverage (requires tarpaulin)
cargo install cargo-tarpaulin
cargo tarpaulin --out Html
open tarpaulin-report.html
```

### Coverage Goals

- **Rust code**: >80% coverage
- **Python bindings**: >90% coverage
- **Integration tests**: All major features covered
- **Compatibility**: 100% of LangGraph tests pass

## Performance Testing

### Running Benchmarks

```bash
# Run all benchmarks
cargo bench

# Save current performance as baseline
cargo bench -- --save-baseline main

# After changes, compare
cargo bench -- --baseline main

# Generate criterion report
open target/criterion/report/index.html
```

### Performance Requirements

Fast LangGraph aims for:

- **10-100x** faster than Python for core operations
- **50-80%** memory reduction
- **Zero** performance regression between versions

### Comparing with Python

```python
# Run comparison benchmark
python examples/python_performance_comparison.py

# Output shows speedup factors
```

## Troubleshooting

### Common Issues

**1. Maturin not found**
```bash
poetry install --with build
# or
pip install maturin
```

**2. Rust compiler errors**
```bash
rustup update stable
cargo clean
cargo build
```

**3. Python import errors**
```bash
# Rebuild and reinstall
cargo clean
poetry run maturin develop --release
```

**4. Test environment conflicts**
```bash
# Clean test directory
rm -rf .langgraph-test
python scripts/test_compatibility.py
```

**5. LangGraph version mismatch**
```bash
# Update LangGraph
poetry update langgraph
# Or test against specific version
poetry add langgraph@^0.2.0 --group test
```

## Best Practices

1. **Run tests before committing**
   ```bash
   cargo test && poetry run pytest
   ```

2. **Test with Python implementation**
   ```bash
   # Verify tests pass without Rust
   FAST_LANGGRAPH_AUTO_PATCH=0 pytest
   ```

3. **Keep compatibility tests passing**
   - Run compatibility tests for major changes
   - Monitor daily CI runs for LangGraph updates

4. **Write tests for new features**
   - Add Rust tests for core functionality
   - Add Python tests for bindings
   - Add integration tests for user-facing features

5. **Document breaking changes**
   - Update CHANGELOG.md
   - Update compatibility docs
   - Add migration guide if needed

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Rust Testing](https://doc.rust-lang.org/book/ch11-00-testing.html)
- [PyO3 Testing Guide](https://pyo3.rs/latest/testing.html)
- [Criterion Benchmarking](https://bheisler.github.io/criterion.rs/book/)
