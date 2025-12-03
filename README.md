# Fast-LangGraph

[![CI](https://github.com/neul-labs/fast-langgraph/actions/workflows/ci.yml/badge.svg)](https://github.com/neul-labs/fast-langgraph/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/fast-langgraph)](https://pypi.org/project/fast-langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

High-performance Rust accelerators for [LangGraph](https://github.com/langchain-ai/langgraph) applications. Drop-in components that provide 5-80x speedups with zero code changes.

## Why Fast-LangGraph?

LangGraph is great for building AI agents, but production workloads often hit performance bottlenecks:
- Repeated LLM calls with identical prompts
- Slow checkpoint serialization
- Inefficient state management at scale

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

| Feature | Speedup | Use Case |
|---------|---------|----------|
| LLM Caching | 10-80x | Repeated prompts, RAG systems |
| Function Caching | 2-100x | Expensive computations, embeddings |
| Checkpointing | 5-6x | Persistent conversations |
| State Updates | 10x | High-frequency state changes |

Benchmarks run on realistic workloads. Actual speedup depends on cache hit rates and I/O patterns.

## Requirements

- Python 3.9+
- Works with any LangGraph version

## Documentation

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
