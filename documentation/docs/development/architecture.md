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

### Where Rust Excels

Based on benchmarks, Rust provides the most dramatic improvements for:

| Operation | Speedup | Why |
|-----------|---------|-----|
| **Checkpoint serialization** | 43-737x | Avoids Python `deepcopy()` overhead |
| **Sustained state updates** | 13-46x | No intermediate Python object creation |
| **E2E graph execution** | 2-3x | Combined state + checkpoint benefits |

!!! note "Python Dict Performance"
    Python's built-in `dict` is already implemented in C and highly optimized. For simple dict operations (lookups, single merges), Python is competitive. Rust's advantage comes from avoiding Python object overhead in complex, sustained operations.

## Component Design

### Caching System

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

### Checkpointing System

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

### State Merge System

State updates in LangGraph involve:

1. Deep-copying state dictionaries
2. Merging updates
3. Handling append-only keys (like `messages`)

Rust implementation:

- Avoids Python dict copying overhead
- Uses efficient key lookup
- Minimizes allocations for append operations

## Python Integration

### PyO3 Bindings

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

### The @cached Decorator

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

### Shim Implementation

The shim patches LangGraph internals at runtime:

```python
# executor_cache.py
_executor_cache = {}

def get_executor_for_config_cached(config):
    key = (max_workers, thread_name_prefix)
    if key not in _executor_cache:
        _executor_cache[key] = ThreadPoolExecutor(...)
    return _executor_cache[key]

# shim.py
def patch_langgraph():
    langchain_core.runnables.config.get_executor_for_config = \
        get_executor_for_config_cached
```

## Project Structure

```
fast-langgraph/
├── src/                      # Rust source
│   ├── lib.rs               # Library entry point
│   ├── python.rs            # PyO3 bindings
│   ├── function_cache.rs    # LRU cache
│   ├── llm_cache.rs         # LLM-specific cache
│   ├── checkpoint_sqlite.rs # SQLite checkpointer
│   └── state_merge.rs       # State operations
├── fast_langgraph/          # Python package
│   ├── __init__.py          # Public API
│   ├── shim.py              # Auto-patching
│   ├── executor_cache.py    # ThreadPool caching
│   ├── accelerator.py       # Rust wrappers
│   └── profiler.py          # Performance profiling
├── tests/                   # Python tests
├── benches/                 # Rust benchmarks
└── examples/                # Usage examples
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

### PyO3 Boundary Overhead

Data crossing the Python/Rust boundary has overhead (~1-2μs per call):

```
Simple dict lookup:
  Python: 50ns
  Rust (via PyO3): 300ns + 1000ns boundary = 1300ns
```

This means:

- Simple dict lookups are faster in pure Python
- Rust wins when avoiding repeated Python operations

### Best Use Cases for Rust

| Use Case | Rust Advantage |
|----------|----------------|
| Large state (>10KB) | Checkpoint 100x+ faster |
| Many operations (100+ steps) | State updates 10x+ faster |
| Simple, one-shot operations | Use Python instead |

### Thread Safety

Rust components are not thread-safe by default. For concurrent access:

```python
import threading

lock = threading.Lock()

def thread_safe_cache_access(cache, key, value):
    with lock:
        cache.put(key, value)
```

## Future Directions

Potential improvements:

- Async cache operations
- Distributed caching (Redis backend)
- More LangGraph component acceleration
- SIMD-optimized operations
