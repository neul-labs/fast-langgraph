# Profiling

Fast-LangGraph includes a low-overhead profiler to identify performance bottlenecks.

## GraphProfiler

### Basic Usage

```python
from fast_langgraph.profiler import GraphProfiler

profiler = GraphProfiler()

# Profile a single run
with profiler.profile_run():
    result = graph.invoke(input_data)

# View results
profiler.print_report()
```

### Sample Output

```
=== Graph Execution Profile ===
Total runs: 1
Average duration: 245.3ms

Node breakdown:
  llm_call:     180.2ms (73.5%)
  retriever:     42.1ms (17.2%)
  formatter:     23.0ms  (9.3%)
```

### Multiple Runs

Profile multiple executions to get averages:

```python
profiler = GraphProfiler()

for input_data in test_inputs:
    with profiler.profile_run():
        graph.invoke(input_data)

profiler.print_report()
```

Output includes aggregated statistics:
```
=== Graph Execution Profile ===
Total runs: 10
Average duration: 243.7ms (std: 12.4ms)
Min: 228.1ms, Max: 267.3ms

Node breakdown:
  llm_call:     178.9ms (73.4%) ±8.2ms
  retriever:     41.8ms (17.1%) ±3.1ms
  formatter:     23.0ms  (9.4%) ±1.5ms
```

## Profiler Overhead

The profiler is designed for minimal impact:

| Metric | Value |
|--------|-------|
| Per-operation overhead | ~1.6 μs |
| Total overhead (10K ops) | ~16 ms |
| Memory overhead | Negligible |

Safe to use in development and testing environments.

## Common Patterns

### Comparing Before/After

```python
import fast_langgraph
from fast_langgraph.profiler import GraphProfiler

profiler = GraphProfiler()

# Before optimization
with profiler.profile_run():
    result = graph.invoke(input_data)
baseline = profiler.get_last_duration()

# Enable acceleration
fast_langgraph.shim.patch_langgraph()

# After optimization
profiler.reset()
with profiler.profile_run():
    result = graph.invoke(input_data)
optimized = profiler.get_last_duration()

print(f"Speedup: {baseline / optimized:.2f}x")
```

### Finding Bottlenecks

```python
profiler = GraphProfiler()

with profiler.profile_run():
    result = graph.invoke(input_data)

report = profiler.get_report()
for node, stats in report['nodes'].items():
    if stats['percentage'] > 50:
        print(f"Bottleneck: {node} takes {stats['percentage']:.1f}% of time")
```

### Continuous Monitoring

```python
from fast_langgraph.profiler import GraphProfiler
import logging

logger = logging.getLogger(__name__)
profiler = GraphProfiler()

def monitored_invoke(graph, input_data, config=None):
    with profiler.profile_run():
        result = graph.invoke(input_data, config)

    duration = profiler.get_last_duration()
    if duration > 1000:  # > 1 second
        logger.warning(f"Slow execution: {duration:.0f}ms")

    return result
```

### Profiling Specific Components

```python
from fast_langgraph.profiler import GraphProfiler

profiler = GraphProfiler()

# Profile just the LLM calls
with profiler.profile_section("llm_processing"):
    response = llm.invoke(prompt)
    parsed = parse_response(response)

# Profile just retrieval
with profiler.profile_section("retrieval"):
    docs = retriever.get_relevant_documents(query)

profiler.print_report()
```

## Integrating with Caching

Measure cache effectiveness:

```python
from fast_langgraph import cached
from fast_langgraph.profiler import GraphProfiler

@cached(max_size=1000)
def call_llm(prompt):
    return llm.invoke(prompt)

profiler = GraphProfiler()

# First run - cache misses
with profiler.profile_run():
    result = process_queries(queries)
cold_time = profiler.get_last_duration()

# Second run - cache hits
profiler.reset()
with profiler.profile_run():
    result = process_queries(queries)  # Same queries
warm_time = profiler.get_last_duration()

print(f"Cold: {cold_time:.0f}ms, Warm: {warm_time:.0f}ms")
print(f"Cache speedup: {cold_time / warm_time:.1f}x")
print(f"Cache stats: {call_llm.cache_stats()}")
```

## Profiling Checkpoints

```python
from fast_langgraph import RustSQLiteCheckpointer
from fast_langgraph.profiler import GraphProfiler

checkpointer = RustSQLiteCheckpointer("test.db")
app = graph.compile(checkpointer=checkpointer)

profiler = GraphProfiler()

# Profile with checkpointing
with profiler.profile_run():
    result = app.invoke(
        {"messages": [HumanMessage(content="Hello")]},
        {"configurable": {"thread_id": "test"}}
    )

profiler.print_report()
# See how much time is spent on state persistence
```

## Best Practices

1. **Profile realistic workloads** - Use production-like data

2. **Run multiple iterations** - Single runs have high variance

3. **Profile before optimizing** - Know where time is actually spent

4. **Compare apples to apples** - Same inputs, same conditions

5. **Consider warm-up** - First run may be slower (JIT, caches, etc.)

```python
# Warm-up run (discard)
graph.invoke(input_data)

# Actual profiling
profiler = GraphProfiler()
for _ in range(10):
    with profiler.profile_run():
        graph.invoke(input_data)
profiler.print_report()
```

## Exporting Results

```python
profiler = GraphProfiler()

# Run profiling...
with profiler.profile_run():
    result = graph.invoke(input_data)

# Export as dict
report = profiler.get_report()
print(report)
# {
#     'total_runs': 1,
#     'average_duration_ms': 245.3,
#     'nodes': {
#         'llm_call': {'duration_ms': 180.2, 'percentage': 73.5},
#         ...
#     }
# }

# Export as JSON
import json
with open('profile_results.json', 'w') as f:
    json.dump(report, f, indent=2)
```

## Next Steps

- [Benchmarks](../development/benchmarks.md) - Detailed performance data
- [Automatic Acceleration](automatic-acceleration.md) - Quick wins
- [Manual Acceleration](manual-acceleration.md) - Maximum performance
