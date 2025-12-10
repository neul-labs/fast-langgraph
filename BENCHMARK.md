# Fast LangGraph Benchmark Results

Generated: 2025-12-10 00:01:45

## System Information

| Property | Value |
|----------|-------|
| Python Version | 3.12.3 |
| Platform | Linux 6.14.0-36-generic |
| Machine | x86_64 |
| Processor | x86_64 |

## Table of Contents

- [Complex Data Structures (Rust Strengths)](#complex-data-structures-rust-strengths)
- [Channel Operations](#channel-operations)
- [Checkpointing](#checkpointing)
- [LLM Caching](#llm-caching)
- [State Merge Operations](#state-merge-operations)
- [Function Caching](#function-caching)
- [Profiler Overhead](#profiler-overhead)
- [Summary](#summary)

## Complex Data Structures (Rust Strengths)

These benchmarks showcase where Rust provides the most significant performance gains.

### Checkpoint Serialization (vs Python deepcopy)

Rust's biggest advantage - avoiding Python object overhead during state persistence.

| State Size | Rust | Python | Speedup |
|------------|------|--------|---------|
| 3.8 KB | 0.35 ms | 15.29 ms | **43x** |
| 35.0 KB | 0.29 ms | 52.00 ms | **178x** |
| 235.5 KB | 0.28 ms | 206.21 ms | **737x** |

### Sustained State Updates (Graph Execution)

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

## Channel Operations

Benchmarking `RustLastValue` channel update operations.

| Metric | Value |
|--------|-------|
| Iterations | 100,000 |
| Rust Total Time | 31.73 ms |
| Python Total Time | 5.12 ms |
| Rust Per Operation | 317.29 ns |
| Python Per Operation | 51.17 ns |

## Checkpointing

### In-Memory Checkpointer

| Operation | Total Time | Per Operation |
|-----------|------------|---------------|
| PUT (1,000 ops) | 1.40 ms | 1.40 us |
| GET (1,000 ops) | 3.73 ms | 3.73 us |

### SQLite Checkpointer

| Operation | Total Time | Per Operation |
|-----------|------------|---------------|
| PUT (1,000 ops) | 2265.94 ms | 2265.94 us |
| GET (1,000 ops) | 104.14 ms | 104.14 us |

## LLM Caching

### Cache Effectiveness (Simulated LLM Calls)

| Metric | Value |
|--------|-------|
| Without Cache | 108.48 ms |
| With Cache | 11.09 ms |
| **Speedup** | **9.78x** |
| Hit Rate | 90% |
| Cache Hits | 90 |
| Cache Misses | 10 |

### Raw Cache Lookup Performance

| Metric | Value |
|--------|-------|
| Iterations | 100,000 |
| Total Time | 137.90 ms |
| Per Lookup | 1.38 us |

## State Merge Operations

### Simple Dictionary Merge

Merging dictionaries with 1000 keys.

| Implementation | Time (10000 iterations) |
|----------------|----------------------|
| Rust `merge_dicts` | 1084.81 ms |
| Python `{**a, **b}` | 209.94 ms |

### Deep Dictionary Merge

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
| Per Update | 1.43 us |

## Function Caching

### @cached Decorator Performance

| Metric | Value |
|--------|-------|
| Iterations | 10,000 |
| Uncached Time | 44.37 ms |
| Cached Time | 27.30 ms |
| **Speedup** | **1.63x** |
| Cache Overhead | 2.73 us/call |

### Raw Cache Lookup

| Metric | Value |
|--------|-------|
| Iterations | 100,000 |
| Total Time | 249.41 ms |
| Per Lookup | 2.49 us |

## Profiler Overhead

| Metric | Value |
|--------|-------|
| Iterations | 10,000 |
| Without Profiling | 28.11 ms |
| With Profiling | 44.28 ms |
| Overhead | 16.17 ms (57.5%) |
| Per Operation | 1.62 us |

## Summary

### Rust's Key Strengths

| Operation | Speedup | Best Use Case |
|-----------|---------|---------------|
| Checkpoint Serialization | **737x** | State persistence |
| Sustained State Updates | **45.9x** | Long-running graphs |
| E2E Graph Execution | **2.8x** | Production workloads |

### All Performance Characteristics

| Feature | Performance |
|---------|-------------|
| Complex Checkpoint (250KB) | 737x faster than deepcopy |
| LLM Cache (90% hit rate) | 9.8x speedup |
| Function Caching | 1.6x speedup |
| In-Memory Checkpoint PUT | 1.4 us/op |
| In-Memory Checkpoint GET | 3.7 us/op |
| LangGraph State Update | 1.4 us/op |
| Profiler Overhead | 1.6 us/op |

### Running Benchmarks

To regenerate this report:

```bash
uv run python scripts/generate_benchmark_report.py
```

To run individual benchmarks:

```bash
# Rust benchmarks (requires cargo)
cargo bench

# Python benchmarks
uv run python scripts/benchmark_rust_strengths.py      # Rust's key advantages
uv run python scripts/benchmark_complex_structures.py  # Complex data structure tests
uv run python scripts/benchmark_all_features.py
uv run python scripts/benchmark_rust_channels.py
```
