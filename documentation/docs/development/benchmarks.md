# Benchmarks

Detailed performance measurements for Fast-LangGraph.

## Summary

### Rust's Key Strengths

| Operation | Speedup | Best Use Case |
|-----------|---------|---------------|
| **Checkpoint Serialization** | **737x** | State persistence |
| **Sustained State Updates** | **46x** | Long-running graphs |
| **E2E Graph Execution** | **2.8x** | Production workloads |
| **LLM Cache (90% hit rate)** | **10x** | Repeated prompts |

### All Performance Characteristics

| Feature | Performance |
|---------|-------------|
| Complex Checkpoint (250KB) | 737x faster than deepcopy |
| Complex Checkpoint (35KB) | 178x faster |
| LLM Cache (90% hit rate) | 9.8x speedup |
| Function Caching | 1.6x speedup |
| In-Memory Checkpoint PUT | 1.4 μs/op |
| In-Memory Checkpoint GET | 3.7 μs/op |
| LangGraph State Update | 1.4 μs/op |
| Profiler Overhead | 1.6 μs/op |

## Checkpoint Serialization

Rust's biggest advantage—avoiding Python object overhead during state persistence.

### vs Python deepcopy

| State Size | Rust | Python | Speedup |
|------------|------|--------|---------|
| 3.8 KB | 0.35 ms | 15.29 ms | **43x** |
| 35.0 KB | 0.29 ms | 52.00 ms | **178x** |
| 235.5 KB | 0.28 ms | 206.21 ms | **737x** |

!!! note "Scaling Behavior"
    Rust's advantage grows with state size because Python's `deepcopy` overhead scales with object complexity.

### SQLite Checkpointer Operations

| Operation | Total Time (1000 ops) | Per Operation |
|-----------|----------------------|---------------|
| PUT | 2265.94 ms | 2.27 ms |
| GET | 104.14 ms | 104 μs |

### In-Memory Checkpointer

| Operation | Total Time (1000 ops) | Per Operation |
|-----------|----------------------|---------------|
| PUT | 1.40 ms | 1.4 μs |
| GET | 3.73 ms | 3.7 μs |

## State Operations

### Sustained State Updates

Simulating real LangGraph execution with continuous state updates.

| Workload | Steps | Rust | Python | Speedup |
|----------|-------|------|--------|---------|
| Quick | 1000 | 1.83 ms | 83.98 ms | **45.9x** |
| Medium | 100 | 0.57 ms | 7.56 ms | **13.2x** |

### End-to-End Graph Simulation

Full graph execution: 20 nodes, 50 iterations with checkpointing.

| Metric | Value |
|--------|-------|
| Rust Total Time | 9.11 ms |
| Python Total Time | 25.26 ms |
| **Speedup** | **2.77x** |

### Dictionary Merge Operations

#### Simple Merge (1000 keys)

| Implementation | Time (10000 iterations) |
|----------------|----------------------|
| Rust `merge_dicts` | 1084.81 ms |
| Python `{**a, **b}` | 209.94 ms |

!!! warning "Python Wins Here"
    For simple dict merges, Python's built-in `{**a, **b}` is faster. It's implemented in C and highly optimized.

#### Deep Merge

| Implementation | Time (5000 iterations) |
|----------------|----------------------|
| Rust `deep_merge_dicts` | 62.47 ms |
| Python recursive | 50.88 ms |

### LangGraph State Update

State update with message appending (100 existing messages).

| Metric | Value |
|--------|-------|
| Iterations | 5,000 |
| Total Time | 7.15 ms |
| Per Update | 1.43 μs |

## Caching

### LLM Cache Effectiveness

Simulated LLM calls with 90% cache hit rate.

| Metric | Value |
|--------|-------|
| Without Cache | 108.48 ms |
| With Cache | 11.09 ms |
| **Speedup** | **9.78x** |
| Cache Hits | 90 |
| Cache Misses | 10 |

### Raw Cache Lookup Performance

| Metric | Value |
|--------|-------|
| Iterations | 100,000 |
| Total Time | 137.90 ms |
| Per Lookup | 1.38 μs |

### @cached Decorator Performance

| Metric | Value |
|--------|-------|
| Iterations | 10,000 |
| Uncached Time | 44.37 ms |
| Cached Time | 27.30 ms |
| **Speedup** | **1.63x** |
| Cache Overhead | 2.73 μs/call |

## Channel Operations

Benchmarking `RustLastValue` channel update operations.

| Metric | Value |
|--------|-------|
| Iterations | 100,000 |
| Rust Total Time | 31.73 ms |
| Python Total Time | 5.12 ms |
| Rust Per Operation | 317.29 ns |
| Python Per Operation | 51.17 ns |

!!! note "Channel Operations"
    Python wins for individual channel operations due to PyO3 boundary overhead. The benefit comes from batch operations and avoiding repeated crossings.

## Profiler Overhead

| Metric | Value |
|--------|-------|
| Iterations | 10,000 |
| Without Profiling | 28.11 ms |
| With Profiling | 44.28 ms |
| Overhead | 16.17 ms (57.5%) |
| Per Operation | 1.62 μs |

## Running Benchmarks

### Generate Full Report

```bash
uv run python scripts/generate_benchmark_report.py
```

This updates `BENCHMARK.md` with current results.

### Individual Benchmarks

```bash
# Rust's key advantages
uv run python scripts/benchmark_rust_strengths.py

# Complex data structure tests
uv run python scripts/benchmark_complex_structures.py

# All features
uv run python scripts/benchmark_all_features.py

# Channel operations
uv run python scripts/benchmark_rust_channels.py
```

### Rust Benchmarks (Criterion)

```bash
cargo bench
```

## Benchmark Environment

Results generated on:

| Property | Value |
|----------|-------|
| Python Version | 3.12.3 |
| Platform | Linux 6.14.0 |
| Machine | x86_64 |

Results may vary on different hardware. Run benchmarks on your target environment for accurate measurements.

## When to Use Fast-LangGraph

Based on benchmarks:

### Use Rust Components For

| Scenario | Expected Speedup |
|----------|------------------|
| Large state (>10KB) | 100x+ for checkpoints |
| Many graph steps (100+) | 10-50x for state updates |
| Repeated LLM prompts | 10x with caching |
| Production workloads | 2-3x overall |

### Stick with Python For

| Scenario | Reason |
|----------|--------|
| Simple dict merges | Python's C implementation is faster |
| Single operations | PyO3 boundary overhead dominates |
| Prototyping | Simpler debugging |

## Interpreting Results

### Variability

- Run benchmarks multiple times for reliable results
- First run may be slower (warm-up effects)
- I/O operations (SQLite) have high variance

### Real-World Impact

Synthetic benchmarks show maximum potential. Real-world improvement depends on:

1. **Workload characteristics** - State size, operation frequency
2. **Bottleneck distribution** - Where time is actually spent
3. **LLM call ratio** - I/O-bound vs compute-bound

Use [GraphProfiler](../user-guide/profiling.md) to measure actual impact in your application.
