# Usage Guide

Detailed API documentation and usage patterns for Fast-LangGraph.

## Acceleration Overview

Fast-LangGraph provides two types of acceleration:

1. **Automatic Acceleration** - Transparent patching via the shim (no code changes)
2. **Manual Acceleration** - Direct usage of Rust components (maximum performance)

### Performance Summary

| Type | Component | Speedup | Code Changes |
|------|-----------|---------|--------------|
| **Automatic** | Executor caching | 2.3x | None |
| **Automatic** | apply_writes | 1.2x | None |
| **Manual** | RustSQLiteCheckpointer | 5-6x | Replace checkpointer |
| **Manual** | @cached decorator | 10x+ | Add decorator |
| **Manual** | langgraph_state_update | 13-46x | Use function |

See [BENCHMARK.md](../BENCHMARK.md) for detailed measurements.

---

## Automatic Acceleration (Shim)

The shim provides transparent acceleration without any code changes to your LangGraph application.

### Enabling Automatic Acceleration

**Option 1: Environment Variable (Recommended for Production)**

```bash
export FAST_LANGGRAPH_AUTO_PATCH=1
python your_app.py
```

**Option 2: Explicit Call at Startup**

```python
import fast_langgraph
fast_langgraph.shim.patch_langgraph()

# Your existing LangGraph code now runs faster
from langgraph.graph import StateGraph
# ...
```

### What Gets Patched

When you enable the shim, these optimizations are applied automatically:

#### 1. Thread Pool Executor Caching (2.3x speedup)

**What it does:** Reuses ThreadPoolExecutor instances across graph invocations instead of creating new ones each time.

**Technical details:**
- Patches `langchain_core.runnables.config.get_executor_for_config`
- Eliminates ~20ms overhead per graph invocation
- Executors are cached by (max_workers, thread_name_prefix)

**Impact:** This is the single biggest optimization for frequently-invoked graphs. If you call `graph.invoke()` many times, this alone provides 2-3x speedup.

#### 2. apply_writes Acceleration (1.2x speedup)

**What it does:** Uses Rust's `FastChannelUpdater` for batch channel updates during Pregel execution.

**Technical details:**
- Patches `langgraph.pregel._algo.apply_writes`
- Batch processes channel writes instead of iterating in Python
- Falls back gracefully if Rust extension unavailable

**Impact:** Noticeable on graphs with many channels or complex state.

### Checking Acceleration Status

```python
import fast_langgraph

# Print human-readable status
fast_langgraph.shim.print_status()

# Get programmatic status
status = fast_langgraph.shim.get_patch_status()
print(status)
# {
#     'automatic': {'executor_cache': True, 'apply_writes': True},
#     'manual': {'rust_checkpointer': True, 'rust_cache': True},
#     'summary': 'All automatic acceleration enabled (2 patches), 2 manual components available'
# }
```

### Disabling Acceleration

```python
import fast_langgraph

# Unpatch algorithm functions (executor cache requires restart)
fast_langgraph.shim.unpatch_langgraph()
```

> **Note:** Executor caching cannot be fully disabled without restarting the Python process.

---

## Manual Acceleration (Explicit Usage)

For maximum performance, use Rust components directly. These require code changes but provide the largest speedups.

### Quick Reference

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

## Caching

### The `@cached` Decorator

The simplest way to add caching to any function:

```python
from fast_langgraph import cached

@cached
def my_function(arg):
    return expensive_operation(arg)
```

#### Options

```python
@cached(max_size=1000)  # Limit cache size (default: unlimited)
def call_llm(prompt):
    return llm.invoke(prompt)
```

#### Cache Statistics

```python
@cached
def my_function(arg):
    return result

# After some calls
stats = my_function.cache_stats()
# {'hits': 42, 'misses': 10, 'size': 10}

# Clear the cache
my_function.cache_clear()
```

### RustLLMCache

Direct cache access for more control:

```python
from fast_langgraph import RustLLMCache

cache = RustLLMCache(max_size=1000)

# Check cache first
result = cache.get(prompt)
if result is None:
    result = llm.invoke(prompt)
    cache.put(prompt, result)
```

### RustTTLCache

Cache with time-based expiration:

```python
from fast_langgraph import RustTTLCache

# Entries expire after 60 seconds
cache = RustTTLCache(max_size=1000, ttl=60.0)

cache.put("key", "value")
result = cache.get("key")  # Returns "value"

# After 60 seconds...
result = cache.get("key")  # Returns None
```

## Checkpointing

### RustSQLiteCheckpointer

Drop-in replacement for LangGraph's SQLite checkpointer:

```python
from fast_langgraph import RustSQLiteCheckpointer

# Create checkpointer
checkpointer = RustSQLiteCheckpointer("checkpoints.db")

# Use with LangGraph
graph = graph.compile(checkpointer=checkpointer)

# Run with automatic state persistence
result = graph.invoke(
    {"messages": [HumanMessage(content="Hello")]},
    config={"configurable": {"thread_id": "user-123"}}
)
```

The checkpointer automatically:
- Persists state after each step
- Enables conversation resumption
- Supports time-travel debugging

## State Operations

### langgraph_state_update

Optimized state merging:

```python
from fast_langgraph import langgraph_state_update

current_state = {
    "messages": ["Hello"],
    "count": 1
}

updates = {
    "messages": ["World"],
    "count": 2
}

# Append to messages, replace count
new_state = langgraph_state_update(
    current_state,
    updates,
    append_keys=["messages"]
)
# {'messages': ['Hello', 'World'], 'count': 2}
```

## Profiling

### GraphProfiler

Low-overhead performance analysis:

```python
from fast_langgraph.profiler import GraphProfiler

profiler = GraphProfiler()

# Profile a single run
with profiler.profile_run():
    result = graph.invoke(input_data)

# Profile multiple runs
for input_data in inputs:
    with profiler.profile_run():
        graph.invoke(input_data)

# View results
profiler.print_report()
```

#### Sample Output

```
=== Graph Execution Profile ===
Total runs: 10
Average duration: 245.3ms

Node breakdown:
  llm_call:     180.2ms (73.5%)
  retriever:     42.1ms (17.2%)
  formatter:     23.0ms  (9.3%)
```

## Common Patterns

### RAG with Multi-Level Caching

```python
from fast_langgraph import cached

@cached(max_size=500)
def retrieve_documents(query):
    """Cache retrieval results."""
    return vector_store.similarity_search(query)

@cached(max_size=1000)
def generate_response(query, context):
    """Cache LLM responses."""
    prompt = f"Context: {context}\n\nQuestion: {query}"
    return llm.invoke(prompt)

def rag_query(user_query):
    docs = retrieve_documents(user_query)
    context = "\n".join(doc.page_content for doc in docs)
    return generate_response(user_query, context)
```

### Conversation with Checkpointing

```python
from fast_langgraph import RustSQLiteCheckpointer
from langgraph.graph import StateGraph

checkpointer = RustSQLiteCheckpointer("conversations.db")

graph = StateGraph(State)
# ... define nodes and edges ...
app = graph.compile(checkpointer=checkpointer)

# Each thread_id maintains separate conversation state
config = {"configurable": {"thread_id": f"user-{user_id}"}}
result = app.invoke({"messages": [user_message]}, config)
```

### Combining Features

```python
from fast_langgraph import cached, RustSQLiteCheckpointer, langgraph_state_update
from fast_langgraph.profiler import GraphProfiler

# Cache expensive operations
@cached
def call_llm(prompt):
    return llm.invoke(prompt)

# Fast state persistence
checkpointer = RustSQLiteCheckpointer("state.db")

# Profile to find bottlenecks
profiler = GraphProfiler()

with profiler.profile_run():
    result = graph.invoke(input_data)

profiler.print_report()
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FAST_LANGGRAPH_AUTO_PATCH` | Auto-patch LangGraph on import | `0` |
| `FAST_LANGGRAPH_LOG_LEVEL` | Logging verbosity | `WARNING` |
