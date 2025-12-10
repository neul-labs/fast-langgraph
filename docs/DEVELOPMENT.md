# Development

## Setup

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/neul-labs/fast-langgraph
cd fast-langgraph
uv sync --all-extras

# Build Rust extension
uv run maturin develop
```

## Testing

```bash
# Rust tests
cargo test

# Python tests
uv run pytest tests/

# LangGraph compatibility
uv run python scripts/test_compatibility.py
```

## Code Quality

```bash
# Format
cargo fmt
uv run black .

# Lint
cargo clippy -- -D warnings
uv run ruff check .

# Type check
uv run mypy fast_langgraph/
```

## Benchmarks

```bash
# Generate full benchmark report (updates BENCHMARK.md)
uv run python scripts/generate_benchmark_report.py

# Rust's key strengths (checkpoint, state updates)
uv run python scripts/benchmark_rust_strengths.py

# Complex data structure benchmarks
uv run python scripts/benchmark_complex_structures.py

# All features benchmark
uv run python scripts/benchmark_all_features.py

# Rust-only benchmarks (criterion)
cargo bench
```

### Benchmark Results

See [BENCHMARK.md](../BENCHMARK.md) for detailed results. Key findings:

| Operation | Speedup | Notes |
|-----------|---------|-------|
| Checkpoint (250KB state) | **737x** | vs Python deepcopy |
| Checkpoint (35KB state) | **178x** | vs Python deepcopy |
| Sustained state updates | **13-46x** | Scales with iterations |
| E2E graph execution | **2-3x** | With checkpointing |

## Project Structure

```
fast-langgraph/
├── src/                    # Rust source
│   ├── lib.rs             # Library entry point
│   ├── python.rs          # PyO3 bindings
│   └── ...
├── fast_langgraph/        # Python package
│   ├── __init__.py
│   └── shim.py
├── tests/                 # Python tests
├── examples/              # Usage examples
└── scripts/               # Utility scripts
```

## Release

Releases are automated via GitHub Actions. To create a release:

```bash
# Update version in pyproject.toml and Cargo.toml
git tag v0.x.x
git push origin v0.x.x
```

The workflow builds wheels for Linux, macOS, and Windows across Python 3.9-3.13 and publishes to PyPI.
