# State Operations

Fast-LangGraph provides optimized functions for state manipulation.

## langgraph_state_update

The primary function for efficient state updates in LangGraph patterns.

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

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `current_state` | dict | The existing state |
| `updates` | dict | Updates to apply |
| `append_keys` | list[str] | Keys where values should be appended (not replaced) |

### Append vs Replace Behavior

```python
from fast_langgraph import langgraph_state_update

state = {"messages": [1, 2], "count": 0}
updates = {"messages": [3], "count": 5}

# Without append_keys: replace all
result = langgraph_state_update(state, updates, append_keys=[])
# {'messages': [3], 'count': 5}

# With append_keys: append to specified keys
result = langgraph_state_update(state, updates, append_keys=["messages"])
# {'messages': [1, 2, 3], 'count': 5}
```

### Performance

| Workload | Steps | Rust | Python | Speedup |
|----------|-------|------|--------|---------|
| Quick | 1000 | 1.83 ms | 83.98 ms | **45.9x** |
| Medium | 100 | 0.57 ms | 7.56 ms | **13.2x** |

Rust excels at sustained state updates where Python's object overhead accumulates.

## merge_dicts

Shallow dictionary merge.

```python
from fast_langgraph import merge_dicts

a = {"x": 1, "y": 2}
b = {"y": 3, "z": 4}

result = merge_dicts(a, b)
print(result)
# {'x': 1, 'y': 3, 'z': 4}
```

!!! note "Python Alternative"
    For simple cases, Python's `{**a, **b}` is equally fast (implemented in C). Use `merge_dicts` when you need consistent behavior across the codebase.

## deep_merge_dicts

Recursive dictionary merge for nested structures.

```python
from fast_langgraph import deep_merge_dicts

base = {
    "config": {
        "timeout": 30,
        "retries": 3,
        "endpoints": ["api1"]
    },
    "name": "app"
}

override = {
    "config": {
        "timeout": 60,
        "endpoints": ["api2"]
    }
}

result = deep_merge_dicts(base, override)
print(result)
# {
#     'config': {
#         'timeout': 60,
#         'retries': 3,
#         'endpoints': ['api2']
#     },
#     'name': 'app'
# }
```

### Merge Rules

| Base Type | Override Type | Result |
|-----------|---------------|--------|
| dict | dict | Recursive merge |
| list | list | Override (replace) |
| any | any | Override (replace) |

## Common Patterns

### Building Agent State

```python
from fast_langgraph import langgraph_state_update

def agent_node(state):
    # Get LLM response
    response = llm.invoke(state["messages"])

    # Update state with new message
    return langgraph_state_update(
        state,
        {
            "messages": [response],
            "last_response": response.content
        },
        append_keys=["messages"]
    )
```

### Accumulating Results

```python
from fast_langgraph import langgraph_state_update

def search_node(state):
    results = search_engine.query(state["query"])

    return langgraph_state_update(
        state,
        {
            "search_results": results,
            "sources": [r.source for r in results]
        },
        append_keys=["sources"]  # Accumulate sources
    )
```

### Configuration Merging

```python
from fast_langgraph import deep_merge_dicts

default_config = {
    "llm": {
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 1000
    },
    "retriever": {
        "k": 5,
        "threshold": 0.8
    }
}

user_config = {
    "llm": {
        "temperature": 0.2
    }
}

config = deep_merge_dicts(default_config, user_config)
# Merges user preferences while keeping defaults
```

### Batch State Updates

```python
from fast_langgraph import langgraph_state_update

def process_batch(state, items):
    """Process multiple items efficiently."""
    results = []
    for item in items:
        result = process_item(item)
        results.append(result)

    # Single state update for all results
    return langgraph_state_update(
        state,
        {
            "processed_items": results,
            "batch_count": state.get("batch_count", 0) + 1
        },
        append_keys=["processed_items"]
    )
```

## When to Use What

| Function | Use When |
|----------|----------|
| `langgraph_state_update` | LangGraph node updates with append patterns |
| `merge_dicts` | Simple key-value merging |
| `deep_merge_dicts` | Nested configuration merging |
| `{**a, **b}` | One-off simple merges |

## Performance Considerations

### Rust Excels At

1. **Sustained updates** - Many sequential state modifications
2. **Large state** - Complex nested structures
3. **Append operations** - Building up lists over time

### Python Is Fine For

1. **Single operations** - One-off merges
2. **Simple state** - Flat dictionaries with few keys
3. **Infrequent updates** - State changes rarely

### Profiling State Operations

```python
from fast_langgraph.profiler import GraphProfiler
from fast_langgraph import langgraph_state_update

profiler = GraphProfiler()

with profiler.profile_run():
    state = {"messages": []}
    for i in range(1000):
        state = langgraph_state_update(
            state,
            {"messages": [f"msg-{i}"]},
            append_keys=["messages"]
        )

profiler.print_report()
```

## Next Steps

- [Profiling](profiling.md) - Measure performance
- [Benchmarks](../development/benchmarks.md) - Detailed comparisons
