# API Reference

Complete API documentation for Fast-LangGraph.

## Package Exports

```python
from fast_langgraph import (
    # Caching
    cached,
    RustLLMCache,
    RustTTLCache,

    # Checkpointing
    RustSQLiteCheckpointer,

    # State operations
    langgraph_state_update,
    merge_dicts,
    deep_merge_dicts,
)

from fast_langgraph.shim import (
    patch_langgraph,
    unpatch_langgraph,
    print_status,
    get_patch_status,
)

from fast_langgraph.profiler import GraphProfiler
```

---

## Caching

### cached

Decorator for caching function results.

```python
@cached(max_size=None)
def function(*args, **kwargs):
    ...
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_size` | `int \| None` | `None` | Maximum cache entries. `None` = unlimited |

**Returns:** Decorated function with caching behavior.

**Attached methods:**

| Method | Description |
|--------|-------------|
| `cache_stats()` | Returns `{'hits': int, 'misses': int, 'size': int}` |
| `cache_clear()` | Clears all cached entries |

**Example:**

```python
@cached(max_size=1000)
def expensive_call(arg):
    return compute(arg)

expensive_call("a")  # Computes
expensive_call("a")  # Returns cached

print(expensive_call.cache_stats())
# {'hits': 1, 'misses': 1, 'size': 1}

expensive_call.cache_clear()
```

---

### RustLLMCache

LRU cache for string key-value pairs.

```python
class RustLLMCache:
    def __init__(self, max_size: int): ...
    def get(self, key: str) -> str | None: ...
    def put(self, key: str, value: str) -> None: ...
    def stats(self) -> dict: ...
    def clear(self) -> None: ...
```

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `max_size: int` | - | Create cache with max entries |
| `get` | `key: str` | `str \| None` | Get cached value or None |
| `put` | `key: str, value: str` | `None` | Store value |
| `stats` | - | `dict` | `{'hits': int, 'misses': int, 'size': int}` |
| `clear` | - | `None` | Remove all entries |

**Example:**

```python
cache = RustLLMCache(max_size=1000)
cache.put("prompt", "response")
result = cache.get("prompt")  # "response"
result = cache.get("unknown")  # None
```

---

### RustTTLCache

Cache with time-based expiration.

```python
class RustTTLCache:
    def __init__(self, max_size: int, ttl: float): ...
    def get(self, key: str) -> str | None: ...
    def put(self, key: str, value: str) -> None: ...
    def stats(self) -> dict: ...
    def clear(self) -> None: ...
```

**Constructor Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `max_size` | `int` | Maximum cache entries |
| `ttl` | `float` | Time-to-live in seconds |

**Methods:** Same as `RustLLMCache`.

**Example:**

```python
cache = RustTTLCache(max_size=1000, ttl=60.0)
cache.put("key", "value")
cache.get("key")  # "value"
# After 60 seconds...
cache.get("key")  # None (expired)
```

---

## Checkpointing

### RustSQLiteCheckpointer

High-performance SQLite checkpointer for LangGraph.

```python
class RustSQLiteCheckpointer:
    def __init__(self, path: str): ...
```

**Constructor Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `str` | SQLite database path. Use `:memory:` for in-memory |

**LangGraph Interface:**

Implements the standard LangGraph checkpointer interface:

| Method | Description |
|--------|-------------|
| `put(config, checkpoint, metadata)` | Save checkpoint |
| `get(config)` | Retrieve checkpoint |
| `list(config)` | List checkpoints |

**Example:**

```python
checkpointer = RustSQLiteCheckpointer("state.db")
app = graph.compile(checkpointer=checkpointer)

result = app.invoke(
    {"messages": [HumanMessage(content="Hello")]},
    config={"configurable": {"thread_id": "user-123"}}
)
```

---

## State Operations

### langgraph_state_update

Efficient state merging with append support.

```python
def langgraph_state_update(
    current_state: dict,
    updates: dict,
    append_keys: list[str] = []
) -> dict: ...
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `current_state` | `dict` | Existing state |
| `updates` | `dict` | Updates to apply |
| `append_keys` | `list[str]` | Keys where values are appended (not replaced) |

**Returns:** New state dict with updates applied.

**Example:**

```python
state = {"messages": ["Hello"], "count": 1}
updates = {"messages": ["World"], "count": 2}

result = langgraph_state_update(state, updates, append_keys=["messages"])
# {'messages': ['Hello', 'World'], 'count': 2}
```

---

### merge_dicts

Shallow dictionary merge.

```python
def merge_dicts(a: dict, b: dict) -> dict: ...
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `a` | `dict` | Base dictionary |
| `b` | `dict` | Override dictionary |

**Returns:** New dict with `b` values overriding `a`.

**Example:**

```python
result = merge_dicts({"x": 1, "y": 2}, {"y": 3, "z": 4})
# {'x': 1, 'y': 3, 'z': 4}
```

---

### deep_merge_dicts

Recursive dictionary merge.

```python
def deep_merge_dicts(base: dict, override: dict) -> dict: ...
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `base` | `dict` | Base dictionary |
| `override` | `dict` | Override dictionary |

**Returns:** New dict with recursive merge.

**Merge Rules:**

- dict + dict → recursive merge
- list + list → override (replace)
- any + any → override (replace)

**Example:**

```python
base = {"config": {"a": 1, "b": 2}}
override = {"config": {"b": 3}}
result = deep_merge_dicts(base, override)
# {'config': {'a': 1, 'b': 3}}
```

---

## Shim (Automatic Acceleration)

### patch_langgraph

Apply automatic acceleration patches.

```python
def patch_langgraph() -> None: ...
```

Patches:
- `langchain_core.runnables.config.get_executor_for_config` (executor caching)
- `langgraph.pregel._algo.apply_writes` (Rust channel updates)

**Example:**

```python
import fast_langgraph
fast_langgraph.shim.patch_langgraph()
# LangGraph now runs faster automatically
```

---

### unpatch_langgraph

Remove algorithm patches (executor cache cannot be removed).

```python
def unpatch_langgraph() -> None: ...
```

---

### print_status

Print human-readable acceleration status.

```python
def print_status() -> None: ...
```

**Output:**

```
Fast-LangGraph Acceleration Status
==================================
Automatic Acceleration:
  ✓ Executor caching: ENABLED
  ✓ apply_writes: ENABLED
...
```

---

### get_patch_status

Get programmatic acceleration status.

```python
def get_patch_status() -> dict: ...
```

**Returns:**

```python
{
    'automatic': {'executor_cache': bool, 'apply_writes': bool},
    'manual': {'rust_checkpointer': bool, 'rust_cache': bool},
    'summary': str
}
```

---

## Profiler

### GraphProfiler

Low-overhead performance profiler.

```python
class GraphProfiler:
    def __init__(self): ...
    def profile_run(self) -> ContextManager: ...
    def profile_section(self, name: str) -> ContextManager: ...
    def print_report(self) -> None: ...
    def get_report(self) -> dict: ...
    def get_last_duration(self) -> float: ...
    def reset(self) -> None: ...
```

**Methods:**

| Method | Description |
|--------|-------------|
| `profile_run()` | Context manager for profiling an execution |
| `profile_section(name)` | Context manager for profiling a named section |
| `print_report()` | Print human-readable report |
| `get_report()` | Get report as dict |
| `get_last_duration()` | Get last run duration in ms |
| `reset()` | Clear all profiling data |

**Example:**

```python
profiler = GraphProfiler()

with profiler.profile_run():
    result = graph.invoke(input_data)

profiler.print_report()

report = profiler.get_report()
print(f"Duration: {report['average_duration_ms']}ms")
```

---

## Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `FAST_LANGGRAPH_AUTO_PATCH` | `0`, `1` | `0` | Auto-patch on import |
| `FAST_LANGGRAPH_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `WARNING` | Logging verbosity |
