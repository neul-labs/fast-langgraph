# Installation

## Quick Install

Install Fast-LangGraph from PyPI:

```bash
pip install fast-langgraph
```

Or with uv:

```bash
uv add fast-langgraph
```

That's it! The package includes pre-built wheels for:

- **Linux**: x86_64, aarch64
- **macOS**: x86_64 (Intel), aarch64 (Apple Silicon)
- **Windows**: x86_64

## Verify Installation

```python
import fast_langgraph

# Check version
print(fast_langgraph.__version__)

# Verify Rust extension loaded
from fast_langgraph import RustLLMCache
cache = RustLLMCache(max_size=100)
print("Rust extension working!")
```

## Optional Dependencies

### For LangGraph Integration

If you want to use automatic acceleration (shim) or checkpointing:

```bash
pip install fast-langgraph langgraph
```

### For Development

```bash
pip install fast-langgraph[dev]
```

This includes:

- pytest and testing utilities
- black, ruff, mypy for code quality
- maturin for building from source

## Building from Source

If you need to build from source (e.g., for an unsupported platform):

### Prerequisites

1. **Rust toolchain** (1.70+):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

2. **uv** (recommended) or pip:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Build Steps

```bash
# Clone repository
git clone https://github.com/neul-labs/fast-langgraph
cd fast-langgraph

# Install dependencies
uv sync --all-extras

# Build Rust extension
uv run maturin develop

# Verify
uv run python -c "import fast_langgraph; print('Success!')"
```

### Release Build

For optimized performance:

```bash
uv run maturin develop --release
```

## Troubleshooting

### Import Error: No module named 'fast_langgraph.fast_langgraph'

The Rust extension wasn't built or installed correctly. Try:

```bash
# Rebuild the extension
uv run maturin develop --release

# Or reinstall from PyPI
pip uninstall fast-langgraph
pip install fast-langgraph --force-reinstall
```

### Compilation Errors

Ensure you have:

- Rust 1.70+ (`rustc --version`)
- Python development headers (`python3-dev` on Ubuntu, comes with Python on macOS/Windows)

### Platform Not Supported

If pre-built wheels aren't available for your platform, you'll need to build from source. See the [Building from Source](#building-from-source) section above.

## Next Steps

Now that you have Fast-LangGraph installed, head to the [Quick Start](quickstart.md) guide to start accelerating your LangGraph applications.
