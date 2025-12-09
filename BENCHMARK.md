# Fast LangGraph Benchmark Results

Generated: 2025-12-09 23:34:45

## System Information

| Property | Value |
|----------|-------|
| Python Version | 3.12.3 |
| Platform | Linux 6.14.0-36-generic |
| Machine | x86_64 |
| Processor | x86_64 |

## Table of Contents

- [Channel Operations](#channel-operations)
- [Checkpointing](#checkpointing)
- [LLM Caching](#llm-caching)
- [State Merge Operations](#state-merge-operations)
- [Function Caching](#function-caching)
- [Profiler Overhead](#profiler-overhead)
- [Summary](#summary)

## Channel Operations

Benchmarking `RustLastValue` channel update operations.

| Metric | Value |
|--------|-------|
| Iterations | 100,000 |
| Rust Total Time | 20.06 ms |
| Python Total Time | 3.03 ms |
| Rust Per Operation | 200.58 ns |
| Python Per Operation | 30.27 ns |

## Checkpointing

### In-Memory Checkpointer

| Operation | Total Time | Per Operation |
|-----------|------------|---------------|
| PUT (1,000 ops) | 1.14 ms | 1.14 us |
| GET (1,000 ops) | 3.30 ms | 3.30 us |

### SQLite Checkpointer

| Operation | Total Time | Per Operation |
|-----------|------------|---------------|
| PUT (1,000 ops) | 2260.73 ms | 2260.73 us |
| GET (1,000 ops) | 73.48 ms | 73.48 us |

## LLM Caching

### Cache Effectiveness (Simulated LLM Calls)

| Metric | Value |
|--------|-------|
| Without Cache | 110.95 ms |
| With Cache | 11.26 ms |
| **Speedup** | **9.86x** |
| Hit Rate | 90% |
| Cache Hits | 90 |
| Cache Misses | 10 |

### Raw Cache Lookup Performance

| Metric | Value |
|--------|-------|
| Iterations | 100,000 |
| Total Time | 99.29 ms |
| Per Lookup | 0.99 us |

## State Merge Operations

### Simple Dictionary Merge

Merging dictionaries with 1000 keys.

| Implementation | Time (10000 iterations) |
|----------------|----------------------|
| Rust `merge_dicts` | 774.65 ms |
| Python `{**a, **b}` | 157.32 ms |

### Deep Dictionary Merge

| Implementation | Time (5000 iterations) |
|----------------|----------------------|
| Rust `deep_merge_dicts` | 45.33 ms |
| Python recursive | 37.07 ms |

### LangGraph State Update

State update with message appending (100 existing messages).

| Metric | Value |
|--------|-------|
| Iterations | 5,000 |
| Total Time | 5.16 ms |
| Per Update | 1.03 us |

## Function Caching

### @cached Decorator Performance

| Metric | Value |
|--------|-------|
| Iterations | 10,000 |
| Uncached Time | 30.25 ms |
| Cached Time | 18.68 ms |
| **Speedup** | **1.62x** |
| Cache Overhead | 1.87 us/call |

### Raw Cache Lookup

| Metric | Value |
|--------|-------|
| Iterations | 100,000 |
| Total Time | 175.82 ms |
| Per Lookup | 1.76 us |

## Profiler Overhead

| Metric | Value |
|--------|-------|
| Iterations | 10,000 |
| Without Profiling | 20.79 ms |
| With Profiling | 33.30 ms |
| Overhead | 12.52 ms (60.2%) |
| Per Operation | 1.25 us |

## Summary

### Key Performance Characteristics

| Feature | Performance |
|---------|-------------|
| LLM Cache (90% hit rate) | 9.9x speedup |
| Function Caching | 1.6x speedup |
| In-Memory Checkpoint PUT | 1.1 us/op |
| In-Memory Checkpoint GET | 3.3 us/op |
| LangGraph State Update | 1.0 us/op |
| Profiler Overhead | 1.3 us/op |

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
uv run python scripts/benchmark_all_features.py
uv run python scripts/benchmark_rust_channels.py
uv run python scripts/benchmark_new_features.py
uv run python scripts/benchmark_shimming_features.py
uv run python scripts/benchmark_optimizations.py
```
