# Usage Guide

Detailed API documentation and usage patterns for Fast-LangGraph.

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
