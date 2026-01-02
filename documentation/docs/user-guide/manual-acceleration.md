# Manual Acceleration

For maximum performance, use Rust components directly. These require code changes but provide the largest speedups.

## Quick Reference

```python
from fast_langgraph import (
    # Checkpointing (5-6x faster)
    RustSQLiteCheckpointer,

    # Caching
    cached,           # Decorator for any function
    RustLLMCache,     # Direct cache access
    RustTTLCache,     # Cache with expiration

    # State operations
    langgraph_state_update,  # Optimized state merging
    merge_dicts,             # Fast dict merging
    deep_merge_dicts,        # Deep merge
)
```

## Performance Comparison

| Component | Speedup | Best For |
|-----------|---------|----------|
| `RustSQLiteCheckpointer` | **5-6x** | Persistent state storage |
| `@cached` decorator | **10x+** | LLM calls with repeated prompts |
| `langgraph_state_update` | **13-46x** | High-frequency state updates |
| `RustLLMCache` | **10x** | Direct cache control |
| `RustTTLCache` | **10x** | Time-based cache expiration |

## RustSQLiteCheckpointer

Drop-in replacement for LangGraph's SQLite checkpointer with 5-6x better performance.

### Basic Usage

```python
from fast_langgraph import RustSQLiteCheckpointer

# Create checkpointer
checkpointer = RustSQLiteCheckpointer("checkpoints.db")

# Use with LangGraph
graph = graph.compile(checkpointer=checkpointer)

# State is automatically persisted
result = graph.invoke(
    {"messages": [HumanMessage(content="Hello")]},
    config={"configurable": {"thread_id": "user-123"}}
)
```

### Why It's Faster

The Rust checkpointer optimizes:

1. **Serialization** - JSON encoding in Rust (serde) vs Python's json module
2. **Batching** - Groups writes to reduce SQLite transactions
3. **Prepared statements** - Reuses compiled SQL

```
Python checkpoint flow:
  dict → json.dumps → sqlite3.execute → disk

Rust checkpoint flow:
  dict → PyO3 extract → serde_json → rusqlite → disk
        └── happens once ──┘└── native speed ──┘
```

### Performance by State Size

| State Size | Rust | Python (deepcopy) | Speedup |
|------------|------|-------------------|---------|
| 3.8 KB | 0.35 ms | 15.29 ms | **43x** |
| 35 KB | 0.29 ms | 52.00 ms | **178x** |
| 235 KB | 0.28 ms | 206.21 ms | **737x** |

## The @cached Decorator

Cache any function's results with minimal overhead.

### Basic Usage

```python
from fast_langgraph import cached

@cached
def expensive_function(arg):
    return compute_something(arg)
```

### With Options

```python
@cached(max_size=1000)  # Limit cache entries
def call_llm(prompt):
    return llm.invoke(prompt)
```

### Cache Statistics

```python
@cached
def my_function(arg):
    return result

# Use the function
my_function("hello")
my_function("hello")  # Cache hit
my_function("world")  # Cache miss

# Check performance
stats = my_function.cache_stats()
print(stats)
# {'hits': 1, 'misses': 2, 'size': 2}

# Clear the cache
my_function.cache_clear()
```

### Caching LLM Calls

```python
from fast_langgraph import cached

@cached(max_size=1000)
def call_llm(prompt):
    return llm.invoke(prompt)

# First call: ~500ms (API call)
response = call_llm("What is LangGraph?")

# Second call: ~0.01ms (from cache)
response = call_llm("What is LangGraph?")
```

## RustLLMCache

Direct cache access for more control than the decorator.

```python
from fast_langgraph import RustLLMCache

cache = RustLLMCache(max_size=1000)

# Manual caching pattern
def call_with_cache(prompt):
    result = cache.get(prompt)
    if result is None:
        result = llm.invoke(prompt)
        cache.put(prompt, result)
    return result

# Check stats
print(cache.stats())  # {'hits': 0, 'misses': 0, 'size': 0}
```

## RustTTLCache

Cache with automatic time-based expiration.

```python
from fast_langgraph import RustTTLCache

# Entries expire after 60 seconds
cache = RustTTLCache(max_size=1000, ttl=60.0)

cache.put("key", "value")
result = cache.get("key")  # Returns "value"

# After 60 seconds...
result = cache.get("key")  # Returns None (expired)
```

Use cases:

- Caching API responses that may change
- Session data with timeout
- Rate limiting data

## langgraph_state_update

Optimized state merging for LangGraph patterns.

### Basic Usage

```python
from fast_langgraph import langgraph_state_update

current_state = {
    "messages": ["Hello"],
    "count": 1,
    "metadata": {"key": "value"}
}

updates = {
    "messages": ["World"],
    "count": 2
}

# Append to messages, replace other keys
new_state = langgraph_state_update(
    current_state,
    updates,
    append_keys=["messages"]
)

print(new_state)
# {
#     'messages': ['Hello', 'World'],
#     'count': 2,
#     'metadata': {'key': 'value'}
# }
```

### Performance Comparison

| Workload | Steps | Rust | Python | Speedup |
|----------|-------|------|--------|---------|
| Quick | 1000 | 1.83 ms | 83.98 ms | **45.9x** |
| Medium | 100 | 0.57 ms | 7.56 ms | **13.2x** |

## merge_dicts and deep_merge_dicts

Low-level dict merging utilities.

```python
from fast_langgraph import merge_dicts, deep_merge_dicts

# Shallow merge
result = merge_dicts({"a": 1}, {"b": 2})
# {'a': 1, 'b': 2}

# Deep merge (nested dicts)
result = deep_merge_dicts(
    {"config": {"timeout": 30, "retries": 3}},
    {"config": {"timeout": 60}}
)
# {'config': {'timeout': 60, 'retries': 3}}
```

!!! note "Python Dict Performance"
    For simple dict operations, Python's built-in `{**a, **b}` is already fast (implemented in C). Use `langgraph_state_update` for LangGraph-specific patterns with append keys.

## Combining Manual Components

All manual components work together:

```python
from fast_langgraph import (
    RustSQLiteCheckpointer,
    cached,
    langgraph_state_update,
)
from fast_langgraph.profiler import GraphProfiler

# Fast LLM caching
@cached(max_size=500)
def call_llm(prompt):
    return llm.invoke(prompt)

# Fast state persistence
checkpointer = RustSQLiteCheckpointer("state.db")

# Build and compile graph
graph = StateGraph(State)
# ... add nodes ...
app = graph.compile(checkpointer=checkpointer)

# Profile to verify speedup
profiler = GraphProfiler()
with profiler.profile_run():
    result = app.invoke(input_data)
profiler.print_report()
```

## When to Use What

| Use Case | Component |
|----------|-----------|
| Stateful conversations | `RustSQLiteCheckpointer` |
| Repeated LLM prompts | `@cached` decorator |
| RAG with document caching | `RustLLMCache` |
| Session data with timeout | `RustTTLCache` |
| Complex state updates | `langgraph_state_update` |

## Next Steps

- [Caching](caching.md) - Deep dive into caching options
- [Checkpointing](checkpointing.md) - Advanced checkpointing patterns
- [State Operations](state-operations.md) - State manipulation details
