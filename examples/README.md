# Fast LangGraph Examples

This directory contains examples demonstrating various ways to use Fast LangGraph.

## Quick Start Examples

### `simple_test.py`
Comprehensive test demonstrating basic functionality without requiring LangGraph installation.
Shows:
- Shim module functionality
- Rust availability checks
- Direct usage of Rust implementations
- Basic performance testing

```bash
python examples/simple_test.py
```

### `basic_usage.py`
Simple example showing direct usage of Rust implementations.
```bash
python examples/basic_usage.py
```

## Integration Examples

### `monkeypatch_example.py`
Demonstrates the three ways to integrate Fast LangGraph:
1. Manual patching with `fast_langgraph.shim.patch_langgraph()`
2. Auto-patching with environment variable
3. Direct usage of Rust classes

```bash
python examples/monkeypatch_example.py
```

### `test_monkeypatch.py`
Advanced example comparing performance between:
- Original Python implementation
- Patched (Rust) implementation
- Direct Rust usage

Requires LangGraph to be installed. Shows real performance comparisons.

```bash
python examples/test_monkeypatch.py
```

## Performance Examples

### `performance_demo.py`
Simulates performance improvements with simplified channel implementations.

```bash
python examples/performance_demo.py
```

### `python_performance_comparison.py`
Detailed performance comparison between Python and Rust implementations.

```bash
python examples/python_performance_comparison.py
```

## Rust Examples

### `basic.rs`
Basic Rust example showing how to use the library directly from Rust.

```bash
cargo run --example basic
```

## Deprecated/Duplicate Examples

The following files are kept for backward compatibility but are redundant:
- `python_demo.py` - Similar to basic_usage.py
- `python_example.py` - Similar to basic_usage.py

## Running Examples

Make sure you have Fast LangGraph installed:

```bash
# Development installation
poetry install
poetry run maturin develop

# Or from PyPI
pip install fast-langgraph
```

Then run any example:

```bash
python examples/<example_name>.py
```
