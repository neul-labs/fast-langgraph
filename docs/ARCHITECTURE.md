# Architecture

How Fast-LangGraph achieves its performance improvements.

## Overview

Fast-LangGraph is a hybrid Rust/Python library. Performance-critical components are implemented in Rust and exposed to Python via [PyO3](https://pyo3.rs/) bindings.

```
┌─────────────────────────────────────────────┐
│              Python Application             │
│                                             │
│   from fast_langgraph import cached         │
│   @cached                                   │
│   def call_llm(prompt): ...                 │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│           fast_langgraph (Python)           │
│                                             │
│   - High-level API                          │
│   - Decorator wrappers                      │
│   - LangGraph integration                   │
└─────────────────┬───────────────────────────┘
                  │ PyO3 bindings
                  ▼
┌─────────────────────────────────────────────┐
│           fast_langgraph (Rust)             │
│                                             │
│   - LRU/TTL caches                          │
│   - SQLite checkpointer                     │
│   - State merge operations                  │
│   - Profiler                                │
└─────────────────────────────────────────────┘
```

## Why Rust?

Python's Global Interpreter Lock (GIL) and dynamic typing create overhead for:

1. **Object copying** - `deepcopy()` is expensive for nested structures
2. **Serialization** - Checkpoint encoding/decoding
3. **Memory management** - Frequent allocations in hot paths

Rust provides:
- Zero-cost abstractions
- No GIL (true parallelism possible)
- Predictable memory layout
- Compile-time optimizations

### Where Rust Excels (Benchmarks)

Based on [BENCHMARK.md](../BENCHMARK.md), Rust provides the most dramatic improvements for:

| Operation | Speedup | Why |
|-----------|---------|-----|
| **Checkpoint serialization** | 43-737x | Avoids Python `deepcopy()` overhead entirely |
| **Sustained state updates** | 13-46x | No intermediate Python object creation |
| **E2E graph execution** | 2-3x | Combined state + checkpoint benefits |

**Important**: Python's built-in `dict` is already implemented in C and highly optimized. For simple dict operations (lookups, single merges), Python is competitive. Rust's advantage comes from avoiding Python object overhead in complex, sustained operations.

## Component Design

### Caching (`src/function_cache.rs`, `src/llm_cache.rs`)

The cache uses a Rust `HashMap` with LRU eviction:

```
┌─────────────────────────────────────────┐
│              RustLLMCache               │
├─────────────────────────────────────────┤
│  HashMap<String, CacheEntry>            │
│  ┌─────────┬─────────┬─────────┐       │
│  │  key    │  value  │  access │       │
│  ├─────────┼─────────┼─────────┤       │
│  │ hash(p) │ result  │  time   │       │
│  └─────────┴─────────┴─────────┘       │
│                                         │
│  max_size: usize                        │
│  hits: AtomicU64                        │
│  misses: AtomicU64                      │
└─────────────────────────────────────────┘
```

Performance gains come from:
- Rust's efficient `HashMap` implementation
- Pre-computed string hashing
- Lock-free statistics counters
- No Python object overhead for internal operations

### Checkpointing (`src/checkpoint_sqlite.rs`)

The SQLite checkpointer optimizes:

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

### State Merge (`src/state_merge.rs`)

State updates in LangGraph involve:
1. Deep-copying state dictionaries
2. Merging updates
3. Handling append-only keys (like `messages`)

Rust implementation:
- Avoids Python dict copying overhead
- Uses efficient key lookup
- Minimizes allocations for append operations

## Python Integration

### PyO3 Bindings (`src/python.rs`)

Rust structs are exposed as Python classes:

```rust
#[pyclass]
struct RustLLMCache {
    cache: HashMap<String, String>,
    max_size: usize,
}

#[pymethods]
impl RustLLMCache {
    #[new]
    fn new(max_size: usize) -> Self { ... }

    fn get(&self, key: &str) -> Option<String> { ... }
    fn put(&mut self, key: String, value: String) { ... }
}
```

### The `@cached` Decorator

The decorator bridges Python functions with Rust caching:

```python
def cached(fn=None, *, max_size=None):
    def decorator(func):
        cache = RustLLMCache(max_size or 10000)

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = _make_key(args, kwargs)
            result = cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.put(key, result)
            return result

        wrapper.cache_stats = cache.stats
        wrapper.cache_clear = cache.clear
        return wrapper

    return decorator(fn) if fn else decorator
```

## Build System

Fast-LangGraph uses [Maturin](https://maturin.rs/) to build Python wheels with embedded Rust:

```
pyproject.toml          # Python package config
Cargo.toml              # Rust package config
src/
  lib.rs                # Rust library entry
  python.rs             # PyO3 bindings
fast_langgraph/
  __init__.py           # Python package
```

Build produces a wheel containing:
- Pure Python modules (`fast_langgraph/*.py`)
- Compiled Rust extension (`fast_langgraph.cpython-*.so`)

## Limitations & Trade-offs

1. **PyO3 boundary overhead** - Data crossing Python/Rust boundary has overhead (~1-2μs per call). This means:
   - Simple dict lookups are faster in pure Python
   - Rust wins when avoiding repeated Python operations (checkpoints, sustained updates)

2. **Best for complex operations** - Use Rust components for:
   - Large state (>10KB): Checkpoint serialization is 100x+ faster
   - Many operations (100+ steps): Sustained state updates are 10x+ faster
   - Use Python for simple, one-shot operations

3. **Not thread-safe by default** - Use `threading.Lock` for concurrent access

## Future Directions

- Async cache operations
- Distributed caching (Redis backend)
- More LangGraph component acceleration
