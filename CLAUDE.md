# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fast LangGraph is a high-performance Rust implementation of core LangGraph components that provides 10-100x performance improvements for graph execution, state management, and checkpointing operations. The project uses a hybrid acceleration approach where performance-critical components are implemented in Rust and explicitly integrated into Python code.

**Important**: Direct class patching is disabled due to PyO3 isinstance() check incompatibility. The project uses explicit hybrid acceleration through `AcceleratedPregelLoop` and component-level Rust implementations.

## Architecture

The codebase is organized into several key modules:

### Core Rust Implementation
- **`src/lib.rs`**: Main library entry point that re-exports core types
- **`src/hybrid.rs`**: Hybrid acceleration components (ChannelManager, TaskScheduler, PregelAccelerator)
- **`src/pregel_*.rs`**: Pregel execution components (loop, node, algo)
- **`src/channel_manager.rs`**: Channel state management
- **`src/executor.rs`**: Task execution engine
- **`src/graph.rs`**: Graph structure and validation
- **`src/checkpoint.rs`**: Checkpoint system for persisting state
- **`src/python.rs`**: Python bindings using PyO3

### Python Integration Layer
- **`fast_langgraph/__init__.py`**: Package exports and imports
- **`fast_langgraph/shim.py`**: No-op shim that prints availability message
- **`fast_langgraph/accelerator.py`**: Python wrappers for Rust acceleration

### Core Architecture (rust-pregel)
The pure Rust Pregel engine has been extracted to `~/rust-pregel` with:
- **Graph computation model**: Superstep-based execution with triggers
- **Channel system**: LastValue and Topic channels with versioning
- **Checkpoint support**: Full state serialization/deserialization
- **Graph validation**: Comprehensive structure validation

The project uses a hybrid Rust/Python architecture where performance-critical components are implemented in Rust and exposed to Python through PyO3 bindings.

## Development Commands

### Building the Project
```bash
# Build Rust components
cargo build

# Build Python extension for development
poetry run maturin develop

# Build release version
cargo build --release
```

### Testing
```bash
# Run Rust tests
cargo test

# Run Rust tests without Python features
cargo test --no-default-features

# Run Python tests
poetry run pytest tests/

# Run with coverage
poetry run pytest --cov=fast_langgraph tests/

# Run LangGraph compatibility tests
python scripts/test_compatibility.py --keep

# Run integration tests only
poetry run pytest -m integration

# Skip slow tests
poetry run pytest -m "not slow"

# Run benchmarks
cargo bench
```

### Linting and Formatting
```bash
# Rust formatting and linting
cargo fmt
cargo clippy -- -D warnings

# Python formatting and linting
poetry run black fast_langgraph/ tests/ examples/
poetry run ruff check fast_langgraph/ tests/ examples/
poetry run mypy fast_langgraph/

# Run all formatting and linting
poetry run black . && poetry run ruff check . && poetry run mypy fast_langgraph/
```

### Development Setup
```bash
# Install dependencies
poetry install --with dev,docs,test

# Build the Rust extension
poetry run maturin develop

# Verify setup
poetry run python examples/simple_test.py
```

## Key Integration Points

The project uses explicit hybrid acceleration rather than transparent patching:

1. **Hybrid Acceleration**: `AcceleratedPregelLoop` wraps execution with Rust performance
2. **Direct Component Usage**: Import Rust components directly from `fast_langgraph`
3. **Selective Enhancement**: Use specific accelerated components (ChannelManager, TaskScheduler, PregelAccelerator)

**Why No Transparent Patching?**
- PyO3 classes don't support proper Python inheritance needed for CompiledStateGraph
- isinstance() checks fail when modules cache imports before patching
- Explicit integration provides better control and clearer performance boundaries

## Performance Considerations

This is a performance-focused project with specific benchmarking requirements:
- Channels operations achieve 70-80x performance improvements
- Checkpoint operations are 5-6x faster
- Memory usage is reduced by 50-80%
- Always run benchmarks when making performance-critical changes

## Testing Strategy

The project uses a dual testing approach:
- **Rust tests**: Unit tests for core functionality using `cargo test`
- **Python integration tests**: End-to-end testing of Python bindings
- **Performance tests**: Benchmarks comparing Rust vs Python implementations
- **Regression tests**: Ensure compatibility with existing LangGraph APIs