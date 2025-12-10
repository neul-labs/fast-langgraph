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

## Quick Start

### LLM Response Caching

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

### Fast Checkpointing

Drop-in replacement for LangGraph's SQLite checkpointer:

```python
from fast_langgraph import RustSQLiteCheckpointer

# 5-6x faster than the default checkpointer
checkpointer = RustSQLiteCheckpointer("state.db")
graph = graph.compile(checkpointer=checkpointer)
```

### Optimized State Updates

Efficient state merging for high-frequency updates:

```python
from fast_langgraph import langgraph_state_update

new_state = langgraph_state_update(
    current_state,
    {"messages": [new_message]},
    append_keys=["messages"]
)
```

### Performance Profiling

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
