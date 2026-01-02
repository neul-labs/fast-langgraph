# Automatic Acceleration

The shim provides transparent acceleration without any code changes to your LangGraph application.

## Enabling Automatic Acceleration

### Option 1: Environment Variable (Recommended for Production)

```bash
export FAST_LANGGRAPH_AUTO_PATCH=1
python your_app.py
```

### Option 2: Explicit Call at Startup

```python
import fast_langgraph
fast_langgraph.shim.patch_langgraph()

# Your existing LangGraph code now runs faster
from langgraph.graph import StateGraph
# ...
```

!!! tip "Import Order Matters"
    Call `patch_langgraph()` before importing LangGraph components to ensure all patches are applied correctly.

## What Gets Patched

When you enable the shim, these optimizations are applied automatically:

### 1. Thread Pool Executor Caching (2.3x speedup)

**What it does:** Reuses ThreadPoolExecutor instances across graph invocations instead of creating new ones each time.

**Technical details:**

- Patches `langchain_core.runnables.config.get_executor_for_config`
- Eliminates ~20ms overhead per graph invocation
- Executors are cached by `(max_workers, thread_name_prefix)`

**Impact:** This is the single biggest optimization for frequently-invoked graphs. If you call `graph.invoke()` many times, this alone provides 2-3x speedup.

### 2. apply_writes Acceleration (1.2x speedup)

**What it does:** Uses Rust's `FastChannelUpdater` for batch channel updates during Pregel execution.

**Technical details:**

- Patches `langgraph.pregel._algo.apply_writes`
- Batch processes channel writes instead of iterating in Python
- Falls back gracefully if Rust extension unavailable

**Impact:** Noticeable on graphs with many channels or complex state.

## Checking Acceleration Status

### Human-Readable Status

```python
import fast_langgraph
fast_langgraph.shim.print_status()
```

Output:
```
Fast-LangGraph Acceleration Status
==================================
Automatic Acceleration:
  ✓ Executor caching: ENABLED (2.3x speedup)
  ✓ apply_writes: ENABLED (1.2x speedup)

Manual Components Available:
  ✓ RustSQLiteCheckpointer
  ✓ RustLLMCache
  ✓ RustTTLCache
```

### Programmatic Status

```python
import fast_langgraph

status = fast_langgraph.shim.get_patch_status()
print(status)
# {
#     'automatic': {'executor_cache': True, 'apply_writes': True},
#     'manual': {'rust_checkpointer': True, 'rust_cache': True},
#     'summary': 'All automatic acceleration enabled (2 patches), 2 manual components available'
# }
```

Use this for logging or conditional logic:

```python
status = fast_langgraph.shim.get_patch_status()
if status['automatic']['executor_cache']:
    print("Executor caching is active")
```

## Disabling Acceleration

```python
import fast_langgraph

# Unpatch algorithm functions
fast_langgraph.shim.unpatch_langgraph()
```

!!! warning "Executor Cache Cannot Be Disabled"
    Executor caching cannot be fully disabled without restarting the Python process. The cached executors remain in memory.

## When to Use Automatic Acceleration

| Scenario | Recommendation |
|----------|----------------|
| Existing production app | Enable via environment variable |
| Quick performance boost | Enable with `patch_langgraph()` |
| Maximum control | Use [Manual Acceleration](manual-acceleration.md) instead |
| Debugging performance issues | Disable temporarily to isolate issues |

## Combining with Manual Acceleration

Automatic and manual acceleration work together:

```python
import fast_langgraph
from fast_langgraph import RustSQLiteCheckpointer, cached

# Enable automatic acceleration
fast_langgraph.shim.patch_langgraph()

# Add manual acceleration for even more speed
@cached(max_size=1000)
def call_llm(prompt):
    return llm.invoke(prompt)

checkpointer = RustSQLiteCheckpointer("state.db")
app = graph.compile(checkpointer=checkpointer)
```

This gives you:

- **2.3x** from executor caching (automatic)
- **1.2x** from apply_writes (automatic)
- **5-6x** from RustSQLiteCheckpointer (manual)
- **10x+** from LLM caching (manual)

## Troubleshooting

### Patches Not Applied

If `print_status()` shows patches as disabled:

1. Ensure you call `patch_langgraph()` before importing LangGraph
2. Check that LangGraph is installed: `pip install langgraph`
3. Verify the Rust extension loaded: `import fast_langgraph.fast_langgraph`

### Performance Not Improved

1. Use [GraphProfiler](profiling.md) to identify actual bottlenecks
2. Automatic acceleration helps most with:
   - Frequent `graph.invoke()` calls (executor caching)
   - Complex state with many channels (apply_writes)
3. For I/O-bound operations (LLM calls), use `@cached` instead

### Conflicts with Other Libraries

If you encounter issues with other libraries that patch LangGraph internals:

```python
# Apply fast_langgraph patches first
import fast_langgraph
fast_langgraph.shim.patch_langgraph()

# Then import other libraries
import other_library
```

## Next Steps

- [Manual Acceleration](manual-acceleration.md) - For maximum performance
- [Profiling](profiling.md) - To measure actual improvements
