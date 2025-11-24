# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fast LangGraph is a high-performance Rust implementation of core LangGraph components that provides 10-100x performance improvements for graph execution, state management, and checkpointing operations. The project offers a drop-in replacement for Python LangGraph components while maintaining full API compatibility.

## Architecture

The codebase is organized into several key modules:

- **`src/lib.rs`**: Main library entry point that re-exports core types (PregelExecutor, Channel, LastValueChannel, Checkpoint)
- **`src/pregel.rs`**: Core graph execution engine implementing the Pregel computation model with nodes, tasks, and superstep execution
- **`src/channels.rs`**: Channel implementations for state management including LastValueChannel and base Channel trait
- **`src/checkpoint.rs`**: Checkpoint system for persisting and restoring graph state
- **`src/errors.rs`**: Error types and handling
- **`src/python.rs`**: Python bindings using PyO3 for seamless integration with Python LangGraph

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
poetry run pytest --cov=langgraph_rs tests/

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
poetry run black langgraph_rs/ tests/ examples/
poetry run ruff check langgraph_rs/ tests/ examples/
poetry run mypy langgraph_rs/

# Run all formatting and linting
poetry run black . && poetry run ruff check . && poetry run mypy langgraph_rs/
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

The project implements a "shim" pattern where Rust implementations can be transparently substituted for Python components:

1. **Transparent Patching**: `fast_langgraph.shim.patch_langgraph()` replaces Python components with Rust equivalents
2. **Direct Usage**: Import Rust types directly from `fast_langgraph`
3. **Selective Enhancement**: Patch only specific components as needed

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