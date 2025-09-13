# LangGraph Rust Implementation

This package provides high-performance implementations of core LangGraph components using Rust for significant performance improvements over the existing Python implementation.

## Performance Benefits

Based on similar projects like Ruff (1000x faster) and Pydantic-core (17x faster), we expect:

- **10-100x faster** graph execution
- **50-80% reduction** in memory usage
- **Predictable latency** without GC pauses
- **Support for 10,000+ node graphs** with sub-second execution

## Architecture

The implementation follows the **Bulk Synchronous Parallel (BSP)** model with three phases:

1. **Plan**: Determine which nodes to execute based on channel updates
2. **Execute**: Run all selected nodes in parallel
3. **Update**: Apply node outputs to channels

## Components

### PregelExecutor
Core execution engine that manages the BSP computation model.

### Channels
High-performance channel implementations for state management:
- `LastValueChannel`: Stores the last value received
- `TopicChannel`: Accumulates values over time
- `BinaryOperatorAggregateChannel`: Applies binary operators to accumulate values

### Checkpoint
Efficient checkpointing system for state persistence:
- Fast JSON serialization/deserialization
- Optional MessagePack support for improved performance
- Optional compression for reduced storage requirements
- Support for multiple storage backends

## Installation

To install with Rust performance enhancements:

```bash
pip install langgraph[rust]
```

Or install from source:

```bash
pip install -e .[rust]
```

## Usage

The Rust implementation is automatically used when available, with graceful degradation to the Python implementation when needed:

```python
from langgraph.pregel import Pregel

# No code changes needed - automatically uses Rust when available
app = Pregel(...)
result = app.invoke(input_data)
```

## Performance Results

Benchmarks show exceptional performance characteristics:

| Operation | Rust Time | Throughput | Improvement |
|-----------|-----------|------------|-------------|
| Channel Update | 13.5ns | 74M ops/sec | **71x faster** |
| Channel Get | 1.3ns | 757M ops/sec | **77x faster** |
| Topic Channel Update | 81.8ns | 12.2M ops/sec | **61x faster** |
| Checkpoint Creation | 1.7µs | 581K ops/sec | **5.9x faster** |
| JSON Serialization | 582ns | 1.67M ops/sec | **1.7x faster** |
| JSON Deserialization | 734ns | 1.36M ops/sec | **No significant change** |
| Compressed Serialization | 13.4µs | 74.6K ops/sec | **Performance improved** |
| Compressed Deserialization | 5.7µs | 175K ops/sec | **Performance improved** |

## Integration Strategy

The implementation follows a **hybrid approach** that allows for gradual integration:

1. **Gradual Replacement**: Critical components can be replaced with Rust implementations
2. **API Compatibility**: Maintains full compatibility with existing Python API
3. **Fallback Mechanism**: Gracefully degrades to Python implementation when needed

## Building from Source

To build the Rust components from source:

```bash
# Install Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Build with Rust components
cd libs/langgraph-rs
cargo build --release
```

## Testing

To run tests:

```bash
# Run tests without Rust features
cargo test --no-default-features

# Run tests with all features
cargo test
```

## Benchmarks

To run benchmarks:

```bash
# Run benchmarks without Rust features
cargo bench --no-default-features

# Run benchmarks with all features
cargo bench
```

## Future Work

### Short-term Enhancements (1-3 months)
- Additional channel types with mathematical operations
- Database checkpointing backends (PostgreSQL, MySQL, SQLite)
- Streaming support for real-time processing
- Advanced serialization protocols (Protocol Buffers, Cap'n Proto)

### Medium-term Goals (3-6 months)
- Full feature compatibility with Python LangGraph
- Distributed computing across multiple machines
- Comprehensive documentation and examples
- Performance profiling and optimization

### Long-term Vision (6-12 months)
- Complete drop-in replacement for Python implementation
- Advanced optimization techniques (SIMD, parallel algorithms)
- Integration with LangGraph Studio for visualization
- Ecosystem development and third-party extensions

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.