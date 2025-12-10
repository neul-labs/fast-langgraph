# Fast-LangGraph

[![CI](https://github.com/neul-labs/fast-langgraph/actions/workflows/ci.yml/badge.svg)](https://github.com/neul-labs/fast-langgraph/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/fast-langgraph)](https://pypi.org/project/fast-langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

High-performance Rust accelerators for [LangGraph](https://github.com/langchain-ai/langgraph) applications. Drop-in components that provide **up to 700x speedups** for checkpoint operations and **10-50x speedups** for state management.

## Why Fast-LangGraph?

LangGraph is great for building AI agents, but production workloads often hit performance bottlenecks:
- **Checkpoint serialization** - Python's deepcopy is slow for complex state
- **State management at scale** - High-frequency updates accumulate overhead
- **Repeated LLM calls** - Identical prompts waste API costs

Fast-LangGraph solves these by reimplementing critical paths in Rust while maintaining full API compatibility.

## Install

```bash
pip install fast-langgraph
```

## Acceleration Modes

Fast-LangGraph offers two types of acceleration:

### Automatic Acceleration (via Shim)

Enable transparent acceleration with a single environment variable or function call. No code changes required to your existing LangGraph application.

```bash
# Option 1: Environment variable (recommended for production)
export FAST_LANGGRAPH_AUTO_PATCH=1
python your_app.py
```

```python
# Option 2: Explicit patching at startup
import fast_langgraph
fast_langgraph.shim.patch_langgraph()

# Your existing LangGraph code runs faster automatically
```

**What gets accelerated automatically:**

| Component | Speedup | Description |
|-----------|---------|-------------|
| Executor Caching | **2.3x** | Reuses ThreadPoolExecutor across invocations |
| apply_writes | **1.2x** | Rust-based channel batch updates |

**Combined automatic speedup: ~2.8x** for typical graph invocations.

Check acceleration status:
```python
import fast_langgraph
fast_langgraph.shim.print_status()
```

### Manual Acceleration (Explicit Usage)

For maximum performance, use Rust components directly. These require small code changes but provide the largest speedups.

```python
from fast_langgraph import (
    RustSQLiteCheckpointer,  # 5-6x faster checkpointing
    cached,                   # LLM response caching
    langgraph_state_update,   # Fast state merging
)
```

| Component | Speedup | When to Use |
|-----------|---------|-------------|
| `RustSQLiteCheckpointer` | **5-6x** | State persistence |
| `@cached` decorator | **10x+** | Repeated LLM calls (with 90% hit rate) |
| `langgraph_state_update` | **13-46x** | High-frequency state updates |

## Quick Start

### 1. Automatic Acceleration (Easiest)

```python
# At the top of your application
import fast_langgraph
fast_langgraph.shim.patch_langgraph()

# Rest of your code unchanged - runs 2-3x faster
from langgraph.graph import StateGraph
# ...
```

### 2. Fast Checkpointing (Biggest Impact)

Drop-in replacement for LangGraph's SQLite checkpointer:

```python
from fast_langgraph import RustSQLiteCheckpointer

# 5-6x faster than the default checkpointer
checkpointer = RustSQLiteCheckpointer("state.db")
graph = graph.compile(checkpointer=checkpointer)
```

### 3. LLM Response Caching

Cache LLM responses to avoid redundant API calls:

```python
from fast_langgraph import cached

@cached(max_size=1000)
def call_llm(prompt):
    return llm.invoke(prompt)

# First call: hits the API (~500ms)
response = call_llm("What is LangGraph?")

# Second identical call: returns from cache (~0.01ms)
response = call_llm("What is LangGraph?")

# Check cache statistics
print(call_llm.cache_stats())
# {'hits': 1, 'misses': 1, 'size': 1}
```

### 4. Optimized State Updates

Efficient state merging for high-frequency updates:

```python
from fast_langgraph import langgraph_state_update

new_state = langgraph_state_update(
    current_state,
    {"messages": [new_message]},
    append_keys=["messages"]
)
```

### 5. Performance Profiling

Find bottlenecks with minimal overhead:

```python
from fast_langgraph.profiler import GraphProfiler

profiler = GraphProfiler()

with profiler.profile_run():
    result = graph.invoke(input_data)

profiler.print_report()
```

## Performance

### Rust's Key Strengths

These are the operations where Rust provides the most dramatic improvements:

| Operation | Speedup | Best Use Case |
|-----------|---------|---------------|
| **Checkpoint Serialization** | **43-737x** | State persistence (scales with state size) |
| **Sustained State Updates** | **13-46x** | Long-running graphs with many steps |
| **E2E Graph Execution** | **2-3x** | Production workloads with checkpointing |

### All Features

| Feature | Performance | Use Case |
|---------|-------------|----------|
| Complex Checkpoint (250KB) | 737x faster than deepcopy | Large agent state |
| Complex Checkpoint (35KB) | 178x faster | Medium state |
| LLM Response Caching | 10x speedup (90% hit rate) | Repeated prompts, RAG |
| Function Caching | 1.6x speedup | Expensive computations |
| In-Memory Checkpoint | 1.4 us/op | Fast state snapshots |
| LangGraph State Update | 1.4 us/op | High-frequency updates |

> **Note**: Rust excels at complex state operations. For simple dict operations, Python's built-in dict (implemented in C) is already highly optimized. See [BENCHMARK.md](BENCHMARK.md) for detailed results.

## Requirements

- Python 3.9+
- Works with any LangGraph version

## Documentation

- [Benchmarks](BENCHMARK.md) - Detailed performance measurements
- [Usage Guide](docs/USAGE.md) - Detailed API documentation and examples
- [Architecture](docs/ARCHITECTURE.md) - How Fast-LangGraph works internally
- [Development](docs/DEVELOPMENT.md) - Building from source and contributing

## Examples

See the [examples/](examples/) directory for complete working examples:
- `function_cache_example.py` - Caching patterns
- `profiler_example.py` - Performance analysis
- `state_merge_example.py` - State manipulation

## Contributing

Contributions welcome! See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for setup instructions.

## License

MIT
