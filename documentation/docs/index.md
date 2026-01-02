# Fast-LangGraph

<p align="center">
  <strong>High-performance Rust accelerators for LangGraph applications</strong>
</p>

<p align="center">
  <a href="https://github.com/neul-labs/fast-langgraph/actions/workflows/ci.yml"><img src="https://github.com/neul-labs/fast-langgraph/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/fast-langgraph/"><img src="https://img.shields.io/pypi/v/fast-langgraph" alt="PyPI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

---

Fast-LangGraph provides drop-in components that deliver **up to 700x speedups** for checkpoint operations and **10-50x speedups** for state management in your LangGraph applications.

## Why Fast-LangGraph?

LangGraph is excellent for building AI agents, but production workloads often encounter performance bottlenecks:

| Problem | Impact | Fast-LangGraph Solution |
|---------|--------|------------------------|
| **Checkpoint serialization** | Python's `deepcopy` is slow for complex state | Rust-based serialization (up to 737x faster) |
| **State management at scale** | High-frequency updates accumulate overhead | Optimized state operations (13-46x faster) |
| **Repeated LLM calls** | Identical prompts waste API costs | Built-in response caching (10x+ speedup) |

Fast-LangGraph solves these by reimplementing critical paths in Rust while maintaining full API compatibility.

## Performance at a Glance

| Operation | Speedup | Use Case |
|-----------|---------|----------|
| Checkpoint Serialization (250KB) | **737x** | Large agent state |
| Sustained State Updates | **46x** | Long-running graphs |
| End-to-End Graph Execution | **2.8x** | Production workloads |
| LLM Response Caching | **10x** | Repeated prompts |

## Two Ways to Accelerate

### 1. Automatic Acceleration (Zero Code Changes)

Enable transparent acceleration with a single environment variable:

```bash
export FAST_LANGGRAPH_AUTO_PATCH=1
python your_app.py
```

Or with a single function call:

```python
import fast_langgraph
fast_langgraph.shim.patch_langgraph()

# Your existing LangGraph code runs 2-3x faster automatically
```

### 2. Manual Acceleration (Maximum Performance)

For the largest speedups, use Rust components directly:

```python
from fast_langgraph import (
    RustSQLiteCheckpointer,  # 5-6x faster checkpointing
    cached,                   # LLM response caching
    langgraph_state_update,   # Fast state merging
)
```

## Quick Example

```python
from fast_langgraph import RustSQLiteCheckpointer, cached
from langgraph.graph import StateGraph

# Cache LLM responses
@cached(max_size=1000)
def call_llm(prompt):
    return llm.invoke(prompt)

# Use fast checkpointing
checkpointer = RustSQLiteCheckpointer("state.db")
graph = graph.compile(checkpointer=checkpointer)

# Run with automatic state persistence
result = graph.invoke(
    {"messages": [HumanMessage(content="Hello")]},
    config={"configurable": {"thread_id": "user-123"}}
)
```

## Requirements

- Python 3.9+
- Works with any LangGraph version

## Next Steps

<div class="grid cards" markdown>

-   :material-clock-fast:{ .lg .middle } **Getting Started**

    ---

    Install Fast-LangGraph and run your first accelerated graph

    [:octicons-arrow-right-24: Installation](getting-started/installation.md)

-   :material-rocket-launch:{ .lg .middle } **Quick Start**

    ---

    Learn the basics with practical examples

    [:octicons-arrow-right-24: Quick Start](getting-started/quickstart.md)

-   :material-book-open-variant:{ .lg .middle } **User Guide**

    ---

    Deep dive into all features and capabilities

    [:octicons-arrow-right-24: User Guide](user-guide/overview.md)

-   :material-chart-bar:{ .lg .middle } **Benchmarks**

    ---

    Detailed performance measurements and comparisons

    [:octicons-arrow-right-24: Benchmarks](development/benchmarks.md)

</div>
