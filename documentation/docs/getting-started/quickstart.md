# Quick Start

This guide will get you up and running with Fast-LangGraph in minutes.

## Choose Your Acceleration Mode

Fast-LangGraph offers two approaches:

| Mode | Speedup | Code Changes | Best For |
|------|---------|--------------|----------|
| **Automatic** | 2-3x | None | Existing applications |
| **Manual** | 5-700x | Minimal | Maximum performance |

## Automatic Acceleration

The easiest way to speed up your existing LangGraph application.

### Option 1: Environment Variable

```bash
export FAST_LANGGRAPH_AUTO_PATCH=1
python your_app.py
```

### Option 2: Explicit Patching

```python
import fast_langgraph
fast_langgraph.shim.patch_langgraph()

# Your existing code runs faster automatically
from langgraph.graph import StateGraph
# ... rest of your application
```

### Check What's Accelerated

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
```

## Manual Acceleration

For maximum performance, use Rust components directly.

### 1. Fast Checkpointing (5-6x speedup)

Replace LangGraph's checkpointer with the Rust version:

```python
from fast_langgraph import RustSQLiteCheckpointer
from langgraph.graph import StateGraph

# Create fast checkpointer
checkpointer = RustSQLiteCheckpointer("state.db")

# Build your graph
graph = StateGraph(YourState)
# ... add nodes and edges ...

# Compile with fast checkpointing
app = graph.compile(checkpointer=checkpointer)

# Use as normal - state persistence is now 5-6x faster
result = app.invoke(
    {"messages": [HumanMessage(content="Hello")]},
    config={"configurable": {"thread_id": "user-123"}}
)
```

### 2. LLM Response Caching (10x+ speedup)

Avoid redundant API calls:

```python
from fast_langgraph import cached

@cached(max_size=1000)
def call_llm(prompt):
    return llm.invoke(prompt)

# First call: hits the API (~500ms)
response = call_llm("What is LangGraph?")

# Second identical call: returns from cache (~0.01ms)
response = call_llm("What is LangGraph?")

# Check cache performance
print(call_llm.cache_stats())
# {'hits': 1, 'misses': 1, 'size': 1}
```

### 3. Fast State Updates (13-46x speedup)

Efficient state merging for complex operations:

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
# Result: {'messages': ['Hello', 'World'], 'count': 2}
```

## Complete Example

Here's a full example combining multiple acceleration features:

```python
import fast_langgraph
from fast_langgraph import RustSQLiteCheckpointer, cached
from langgraph.graph import StateGraph, MessagesState
from langchain_openai import ChatOpenAI

# Enable automatic acceleration
fast_langgraph.shim.patch_langgraph()

# Set up LLM with caching
llm = ChatOpenAI(model="gpt-4o-mini")

@cached(max_size=500)
def cached_llm_call(messages_tuple):
    """Cache LLM responses by message content."""
    messages = list(messages_tuple)
    return llm.invoke(messages)

def chatbot(state: MessagesState):
    # Convert to tuple for cache key
    messages_tuple = tuple(str(m) for m in state["messages"])
    response = cached_llm_call(messages_tuple)
    return {"messages": [response]}

# Build graph
graph = StateGraph(MessagesState)
graph.add_node("chatbot", chatbot)
graph.set_entry_point("chatbot")
graph.set_finish_point("chatbot")

# Compile with fast checkpointing
checkpointer = RustSQLiteCheckpointer("conversations.db")
app = graph.compile(checkpointer=checkpointer)

# Run
result = app.invoke(
    {"messages": [("user", "What is LangGraph?")]},
    config={"configurable": {"thread_id": "demo"}}
)

print(result["messages"][-1].content)
```

## Performance Tips

1. **Use automatic acceleration first** - It's free performance with zero code changes

2. **Add checkpointing for stateful apps** - `RustSQLiteCheckpointer` provides the biggest speedup for most applications

3. **Cache LLM calls** - If you have any repeated prompts, `@cached` can save significant API costs

4. **Profile before optimizing** - Use `GraphProfiler` to find actual bottlenecks:

```python
from fast_langgraph.profiler import GraphProfiler

profiler = GraphProfiler()
with profiler.profile_run():
    result = app.invoke(input_data)
profiler.print_report()
```

## Next Steps

- [User Guide](../user-guide/overview.md) - Deep dive into all features
- [Benchmarks](../development/benchmarks.md) - Detailed performance measurements
- [API Reference](../reference/api.md) - Complete API documentation
