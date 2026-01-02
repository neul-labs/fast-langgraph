# Contributing

Guide for contributing to Fast-LangGraph.

## Development Setup

### Prerequisites

1. **Rust toolchain** (1.70+):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

2. **uv** (Python package manager):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Clone and Install

```bash
git clone https://github.com/neul-labs/fast-langgraph
cd fast-langgraph

# Install Python dependencies
uv sync --all-extras

# Build Rust extension
uv run maturin develop

# Verify setup
uv run python examples/simple_test.py
```

## Development Workflow

### Running Tests

```bash
# Rust tests
cargo test

# Python tests
uv run pytest tests/

# With coverage
uv run pytest --cov=fast_langgraph tests/

# LangGraph compatibility
uv run python scripts/test_compatibility.py
```

### Code Quality

```bash
# Format Rust
cargo fmt

# Lint Rust
cargo clippy -- -D warnings

# Format Python
uv run black .

# Lint Python
uv run ruff check .

# Type check Python
uv run mypy fast_langgraph/

# All at once
cargo fmt && cargo clippy -- -D warnings && \
uv run black . && uv run ruff check . && uv run mypy fast_langgraph/
```

### Building

```bash
# Development build (fast, unoptimized)
uv run maturin develop

# Release build (slow, optimized)
uv run maturin develop --release

# Build wheel
uv run maturin build --release
```

## Project Structure

```
fast-langgraph/
├── src/                    # Rust source
│   ├── lib.rs             # Library entry point
│   ├── python.rs          # PyO3 bindings
│   ├── function_cache.rs  # Function caching
│   ├── llm_cache.rs       # LLM cache
│   ├── checkpoint_sqlite.rs # Checkpointer
│   └── state_merge.rs     # State operations
├── fast_langgraph/        # Python package
│   ├── __init__.py        # Public API
│   ├── shim.py            # Auto-patching
│   ├── executor_cache.py  # Executor caching
│   ├── accelerator.py     # Rust wrappers
│   └── profiler.py        # Profiling
├── tests/                 # Python tests
├── benches/               # Rust benchmarks
├── examples/              # Usage examples
├── scripts/               # Utility scripts
└── documentation/         # MkDocs documentation
```

## Making Changes

### Adding a Rust Component

1. Create the Rust implementation in `src/`:

```rust
// src/my_component.rs
pub struct MyComponent {
    // ...
}

impl MyComponent {
    pub fn new() -> Self { ... }
    pub fn do_something(&self, input: &str) -> String { ... }
}
```

2. Add PyO3 bindings in `src/python.rs`:

```rust
#[pyclass]
pub struct PyMyComponent {
    inner: MyComponent,
}

#[pymethods]
impl PyMyComponent {
    #[new]
    fn new() -> Self {
        Self { inner: MyComponent::new() }
    }

    fn do_something(&self, input: &str) -> String {
        self.inner.do_something(input)
    }
}
```

3. Export in `src/lib.rs`:

```rust
mod my_component;
pub use my_component::MyComponent;
```

4. Add Python wrapper in `fast_langgraph/__init__.py`:

```python
from .fast_langgraph import PyMyComponent as MyComponent
```

5. Add tests in `tests/test_my_component.py`:

```python
def test_my_component():
    from fast_langgraph import MyComponent
    comp = MyComponent()
    result = comp.do_something("input")
    assert result == "expected"
```

### Adding a Python Feature

1. Implement in appropriate module under `fast_langgraph/`
2. Export from `fast_langgraph/__init__.py`
3. Add tests in `tests/`
4. Update documentation

### Adding Documentation

1. Create/update Markdown files in `documentation/docs/`
2. Update `documentation/mkdocs.yml` navigation if adding new pages
3. Preview locally:

```bash
cd documentation
uv run mkdocs serve
```

## Testing Guidelines

### Test Organization

```
tests/
├── test_cache.py          # Caching tests
├── test_checkpoint.py     # Checkpointer tests
├── test_state.py          # State operation tests
├── test_shim.py           # Shim/patching tests
└── conftest.py            # Shared fixtures
```

### Writing Tests

```python
import pytest
from fast_langgraph import cached, RustLLMCache

class TestCache:
    def test_basic_caching(self):
        @cached
        def fn(x):
            return x * 2

        assert fn(5) == 10
        assert fn(5) == 10  # From cache
        assert fn.cache_stats()['hits'] == 1

    def test_cache_max_size(self):
        cache = RustLLMCache(max_size=2)
        cache.put("a", "1")
        cache.put("b", "2")
        cache.put("c", "3")  # Evicts "a"

        assert cache.get("a") is None
        assert cache.get("b") == "2"
```

### Markers

```python
@pytest.mark.slow
def test_large_operation():
    # Skip with: pytest -m "not slow"
    pass

@pytest.mark.integration
def test_with_langgraph():
    # Requires langgraph installed
    pass
```

## Benchmarking

### Running Benchmarks

```bash
# Full benchmark suite
uv run python scripts/generate_benchmark_report.py

# Specific benchmarks
uv run python scripts/benchmark_rust_strengths.py
cargo bench
```

### Adding Benchmarks

Python benchmark in `scripts/`:

```python
import time
from fast_langgraph import my_function

def benchmark_my_function():
    iterations = 10000
    start = time.perf_counter()

    for _ in range(iterations):
        my_function(test_input)

    elapsed = time.perf_counter() - start
    print(f"Per operation: {elapsed/iterations*1000:.3f} ms")
```

Rust benchmark in `benches/`:

```rust
use criterion::{criterion_group, criterion_main, Criterion};
use fast_langgraph::MyComponent;

fn bench_my_component(c: &mut Criterion) {
    let comp = MyComponent::new();
    c.bench_function("my_component", |b| {
        b.iter(|| comp.do_something("input"))
    });
}

criterion_group!(benches, bench_my_component);
criterion_main!(benches);
```

## Pull Request Process

1. **Fork and branch**:
```bash
git checkout -b feature/my-feature
```

2. **Make changes** following the guidelines above

3. **Test thoroughly**:
```bash
cargo test
uv run pytest tests/
cargo clippy -- -D warnings
uv run ruff check .
```

4. **Update documentation** if needed

5. **Commit with clear message**:
```bash
git commit -m "Add feature X

- Implement Y in Rust
- Add Python bindings
- Add tests and documentation"
```

6. **Push and create PR**:
```bash
git push origin feature/my-feature
```

## Release Process

Releases are automated via GitHub Actions:

```bash
# Update version in pyproject.toml and Cargo.toml
git tag v0.x.x
git push origin v0.x.x
```

The workflow:

1. Runs tests on all platforms
2. Builds wheels for Linux, macOS, Windows
3. Publishes to PyPI

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Include reproduction steps for bugs
- Include benchmark results for performance PRs
