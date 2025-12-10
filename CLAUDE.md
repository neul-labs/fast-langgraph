# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fast LangGraph is a high-performance Rust implementation of core LangGraph components that provides 10-100x performance improvements for graph execution, state management, and checkpointing operations. The project offers two acceleration modes:

1. **Automatic Acceleration (Shim)**: Transparent patching requiring no code changes
2. **Manual Acceleration**: Direct usage of Rust components for maximum performance

**Note**: Direct class patching for CompiledStateGraph is disabled due to PyO3 isinstance() check incompatibility. However, function-level patching (executor caching, apply_writes) works transparently.

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
- **`fast_langgraph/shim.py`**: Automatic acceleration via transparent patching
- **`fast_langgraph/accelerator.py`**: Python wrappers for Rust acceleration
- **`fast_langgraph/executor_cache.py`**: Thread pool caching (2.3x speedup)
- **`fast_langgraph/algo_shims.py`**: Accelerated algorithm functions
- **`fast_langgraph/optimizations.py`**: Unified optimization entry point

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
uv run maturin develop

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
uv run pytest tests/

# Run with coverage
uv run pytest --cov=fast_langgraph tests/

# Run LangGraph compatibility tests
uv run python scripts/test_compatibility.py --keep

# Run integration tests only
uv run pytest -m integration

# Skip slow tests
uv run pytest -m "not slow"

# Run benchmarks
cargo bench
```

### Linting and Formatting
```bash
# Rust formatting and linting
cargo fmt
cargo clippy -- -D warnings

# Python formatting and linting
uv run black fast_langgraph/ tests/ examples/
uv run ruff check fast_langgraph/ tests/ examples/
uv run mypy fast_langgraph/

# Run all formatting and linting
uv run black . && uv run ruff check . && uv run mypy fast_langgraph/
```

### Development Setup
```bash
# Install dependencies (creates virtual environment automatically)
uv sync --all-extras

# Build the Rust extension
uv run maturin develop

# Verify setup
uv run python examples/simple_test.py
```

## Acceleration Modes

### Automatic Acceleration (Shim)

Enable with environment variable or explicit call:
```bash
export FAST_LANGGRAPH_AUTO_PATCH=1
```
```python
import fast_langgraph
fast_langgraph.shim.patch_langgraph()
```

**What gets patched automatically:**
| Component | Speedup | Technical Detail |
|-----------|---------|------------------|
| Executor caching | 2.3x | Patches `langchain_core.runnables.config.get_executor_for_config` |
| apply_writes | 1.2x | Patches `langgraph.pregel._algo.apply_writes` |

### Manual Acceleration (Explicit Usage)

For maximum performance, use Rust components directly:
```python
from fast_langgraph import (
    RustSQLiteCheckpointer,  # 5-6x faster checkpointing
    cached,                   # LLM response caching
    langgraph_state_update,   # Fast state merging
)
```

### Why Class Patching is Disabled
- PyO3 classes don't support proper Python inheritance needed for CompiledStateGraph
- isinstance() checks fail when modules cache imports before patching
- Function-level patching works fine and provides transparent acceleration

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
