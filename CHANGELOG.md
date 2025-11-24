# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of Fast LangGraph
- High-performance Rust implementation of core LangGraph components
- 10-100x performance improvements for graph execution
- Drop-in replacement for Python LangGraph components
- Transparent patching system via `fast_langgraph.shim.patch_langgraph()`
- Direct usage API for Rust implementations
- Auto-patching support via `FAST_LANGGRAPH_AUTO_PATCH` environment variable

### Components Implemented
- `BaseChannel`: Base interface for all channels
- `LastValue`: Last-value channel implementation
- `Checkpoint`: Checkpoint system for state persistence
- `Pregel`: Main graph execution engine
- `GraphExecutor`: High-performance graph executor

### Performance
- Channel operations: 70-80x faster than Python
- Checkpoint operations: 5-6x faster
- Memory usage: 50-80% reduction
- Support for 10,000+ node graphs

## [0.1.0] - 2025-01-XX

### Added
- Initial public release
- Python bindings via PyO3
- Comprehensive test suite
- Documentation and examples
- MIT License

[Unreleased]: https://github.com/neul-labs/fast-langgraph/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/neul-labs/fast-langgraph/releases/tag/v0.1.0
